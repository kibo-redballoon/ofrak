import setuptools
from setuptools.command.egg_info import egg_info


class egg_info_ex(egg_info):
    """Includes license file into `.egg-info` folder."""

    def run(self):
        # don't duplicate license into `.egg-info` when building a distribution
        if not self.distribution.have_run.get("install", True):
            # `install` command is in progress, copy license
            self.mkpath(self.egg_info)
            self.copy_file("LICENSE", self.egg_info)

        egg_info.run(self)


with open("README.md") as f:
    long_description = f.read()


entropy_so = setuptools.Extension(
    "ofrak.core.entropy.entropy_c",
    sources=["ofrak/core/entropy/entropy.c"],
    libraries=["m"],  # math library
    optional=True,  # If this fails the build, OFRAK will fall back to Python implementation
    extra_compile_args=["-O3"],
)


setuptools.setup(
    name="ofrak",
    version="2.0.0",
    description="A binary analysis and modification platform",
    packages=setuptools.find_packages(exclude=["test_ofrak", "test_ofrak.*"]),
    package_data={
        "ofrak": ["py.typed"],
    },
    install_requires=[
        "aiohttp~=3.8.1",
        "beartype~=0.10.2",
        "fdt==0.3.2",
        "importlib-metadata>=1.4",
        "intervaltree==3.1.0",
        "keystone-engine==0.9.2",
        "lief==0.12.2",
        "ofrak_io~=1.0",
        "ofrak_type~=2.0",
        "ofrak_patch_maker~=2.0",
        "orjson~=3.6.7",
        "pefile==2022.5.30",
        "pycdlib==1.12.0",
        "python-lzo==1.14",
        "python-magic",
        "reedsolo==1.5.4",
        "sortedcontainers==2.2.2",
        "synthol~=0.1.1",
        "typeguard~=2.13.3",
        "ubi-reader==0.8.5",
        "xattr==0.9.7",
    ],
    extras_require={
        "docs": [
            "mkdocs==1.2.3",
            "mkdocs-autorefs==0.3.0",
            "mkdocstrings==0.16.2",
            "mkdocs-literate-nav==0.4.0",
            "mkdocs-material==7.3.3",
            "mkdocs_gen_files==0.3.3",
            "jinja2==3.0.0",
            "pytkdocs>=0.12.0",
            "PyYAML~=6.0,>=5.4",
        ],
        "test": [
            "autoflake==1.4",
            "black==22.3.0",
            "pytest",
            "hypothesis~=6.39.3",
            "hypothesis-trio",
            "trio-asyncio",
            "mypy==0.942",
            "psutil~=5.9",
            "pyelftools==0.29",
            "pytest-aiohttp",
            "pytest-asyncio==0.19.0",
            "pytest-lazy-fixture",
            "pytest-cov",
            "pytest-xdist",
            "beartype~=0.10.2",
            "requests",
            "fun-coverage==0.2.0",
        ],
    },
    author="Red Balloon Security",
    author_email="ofrak@redballoonsecurity.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://ofrak.com/",
    download_url="https://github.com/redballoonsecurity/ofrak",
    project_urls={
        "Documentation": "https://ofrak.com/docs/",
        "Community License": "https://github.com/redballoonsecurity/ofrak/blob/master/LICENSE",
        "Commercial Licensing Information": "https://ofrak.com/license/",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "License :: Other/Proprietary License",
        "License :: Free To Use But Restricted",
        "License :: Free For Home Use",
        "Topic :: Security",
        "Typing :: Typed",
    ],
    python_requires=">=3.7",
    license="Proprietary",
    license_files=["LICENSE"],
    cmdclass={"egg_info": egg_info_ex},
    entry_points={
        "ofrak.packages": ["ofrak_pkg = ofrak"],
        "console_scripts": ["ofrak = ofrak.__main__:main"],
    },
    ext_modules=[entropy_so],
    include_package_data=True,
)
