import subprocess
import tempfile
from dataclasses import dataclass
import logging

from ofrak import Identifier, Analyzer
from ofrak.component.packer import Packer
from ofrak.component.unpacker import Unpacker
from ofrak.resource import Resource
from ofrak.core.filesystem import File, Folder, FilesystemRoot, SpecialFileType
from ofrak.core.binary import GenericBinary

from ofrak.model.component_model import ComponentExternalTool
from ofrak_type.range import Range

from ubireader.ubifs.defines import UBIFS_NODE_MAGIC

from ubireader import ubi_io
from ubireader.ubifs import ubifs as ubireader_ubifs
from ubireader.ubifs.defines import PRINT_UBIFS_KEY_HASH, PRINT_UBIFS_COMPR
from ubireader.utils import guess_leb_size

LOGGER = logging.getLogger(__name__)

MKFS_UBIFS_TOOL = ComponentExternalTool(
    "mkfs.ubifs",
    "http://www.linux-mtd.infradead.org/faq/ubifs.html",
    install_check_arg="--help",
    apt_package="mtd-utils",
    brew_package="",  # This isn't compatible with macos, but there may be an alternative tool to do the bidding.
)


@dataclass
class SuperblockNode:
    """
    Each UBIFS image has a superblock which describe a large number of parameters regarding the filesystem. The
    minimal set of parameters necessary to re-pack an UBIFS filesystem are stored here.
    (see also: https://elixir.bootlin.com/linux/v6.1.7/source/fs/ubifs/ubifs.h#L1017).


    :cvar max_leb_count: Maximum number / limit of Logical Erase Blocks
    :cvar default_compr: Default compression algorithm
    :cvar fanout: Fanout of the index tree (number of links per indexing node)
    :cvar key_hash: Type of hash function used for keying direntries (typically 'r5' of reiserfs)
    :cvar orph_lebs: Number of LEBs used for orphan area (orphans are inodes with no links; see https://elixir.bootlin.com/linux/v6.1.7/source/fs/ubifs/orphan.c#L13)
    :cvar log_lebs: LEBs reserved for the journal (see the 'Journal' section in https://www.kernel.org/doc/Documentation/filesystems/ubifs-authentication.rst)
    """

    max_leb_count: int
    default_compr: str  # PRINT_UBIFS_COMPR
    fanout: int
    key_hash: str  # PRINT_UBIFS_KEY_HASH
    orph_lebs: int
    log_lebs: int


@dataclass
class Ubifs(GenericBinary, FilesystemRoot):
    """
    UBIFS is a filesystem specially made to run on top of an UBI translation layer. UBIFS specifically provides
    indexing, compression, encryption / authentication and some other filesystem-related features.

    As part of an UBI image, re-packing an UBIFS image requires the 'min_io_size' and 'leb_size' properties that
    are stored as part of the UBI header (https://elixir.bootlin.com/linux/v6.1.7/source/drivers/mtd/ubi/ubi.h#L441).

    Each UBIFS image has a superblock which is encoded in OFRAK as a SuperblockNode.

    Some documentation about UBIFS layout can also be found here:
    https://www.kernel.org/doc/Documentation/filesystems/ubifs-authentication.rst
    http://www.linux-mtd.infradead.org/doc/ubifs.html

    :cvar min_io_size: Minimum number of bytes per I/O transaction (see http://www.linux-mtd.infradead.org/doc/ubi.html#L_min_io_unit)
    :cvar leb_size: Size of Logical Erase Blocks
    :cvar superblock: A SuberblockNode

    """

    min_io_size: int
    leb_size: int
    superblock: SuperblockNode


class UbifsAnalyzer(Analyzer[None, Ubifs]):
    """
    Extract UBIFS parameters required for packing a resource.
    """

    targets = (Ubifs,)
    outputs = (Ubifs,)

    async def analyze(self, resource: Resource, config=None) -> Ubifs:
        with tempfile.NamedTemporaryFile() as temp_file:
            resource_data = await resource.get_data()
            temp_file.write(resource_data)
            temp_file.flush()

            ubifs_obj = ubireader_ubifs(
                ubi_io.ubi_file(
                    temp_file.name,
                    block_size=guess_leb_size(temp_file.name),
                    start_offset=0,
                    end_offset=None,
                )
            )
            return Ubifs(
                ubifs_obj._get_min_io_size(),
                ubifs_obj._get_leb_size(),
                SuperblockNode(
                    ubifs_obj.superblock_node.max_leb_cnt,
                    PRINT_UBIFS_COMPR[ubifs_obj.superblock_node.default_compr],
                    ubifs_obj.superblock_node.fanout,
                    PRINT_UBIFS_KEY_HASH[ubifs_obj.superblock_node.key_hash],
                    ubifs_obj.superblock_node.orph_lebs,
                    ubifs_obj.superblock_node.log_lebs,
                ),
            )


class UbifsUnpacker(Unpacker[None]):
    """
    Unpack the UBIFS image into a filesystem representation.
    """

    targets = (Ubifs,)
    children = (File, Folder, SpecialFileType)
    external_dependencies = ()

    async def unpack(self, resource: Resource, config=None):
        with tempfile.NamedTemporaryFile() as temp_file:
            resource_data = await resource.get_data()
            temp_file.write(resource_data)
            temp_file.flush()

            with tempfile.TemporaryDirectory() as temp_flush_dir:
                command = [
                    "ubireader_extract_files",
                    "-k",
                    "-o",
                    temp_flush_dir,
                    temp_file.name,
                ]
                subprocess.run(command, check=True, capture_output=True)

                ubifs_view = await resource.view_as(Ubifs)
                await ubifs_view.initialize_from_disk(temp_flush_dir)


class UbifsPacker(Packer[None]):
    """
    Generate an UBIFS image from a filesystem representation in OFRAK.
    """

    targets = (Ubifs,)
    external_dependencies = (MKFS_UBIFS_TOOL,)

    async def pack(self, resource: Resource, config=None) -> None:
        ubifs_view = await resource.view_as(Ubifs)
        flush_dir = await ubifs_view.flush_to_disk()

        with tempfile.NamedTemporaryFile(mode="rb") as temp:
            command = [
                "mkfs.ubifs",
                "-m",
                f"{ubifs_view.min_io_size}",
                "-e",
                f"{ubifs_view.leb_size}",
                "-c",
                f"{ubifs_view.superblock.max_leb_count}",
                "-x",
                f"{ubifs_view.superblock.default_compr}",
                "-f",
                f"{ubifs_view.superblock.fanout}",
                "-k",
                f"{ubifs_view.superblock.key_hash}",
                "-p",
                f"{ubifs_view.superblock.orph_lebs}",
                "-l",
                f"{ubifs_view.superblock.log_lebs}",
                "-F",
                "-r",
                flush_dir,
                temp.name,
            ]
            subprocess.run(command, check=True, capture_output=True)
            new_data = temp.read()

            resource.queue_patch(Range(0, await resource.get_data_length()), new_data)


class UbifsIdentifier(Identifier):
    """
    Check the first four bytes of a resource and tag the resource as Ubifs if it matches the file magic.
    """

    targets = (File, GenericBinary)

    async def identify(self, resource: Resource, config=None) -> None:
        datalength = await resource.get_data_length()
        if datalength >= 4:
            data = await resource.get_data(Range(0, 4))
            if data == UBIFS_NODE_MAGIC:
                resource.add_tag(Ubifs)
