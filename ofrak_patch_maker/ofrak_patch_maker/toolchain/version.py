from enum import Enum


class ToolchainVersion(Enum):
    LLVM_12_0_1 = "LLVM_12_0_1"
    GNU_ARM_NONE_EABI_10_2_1 = "GNU_ARM_NONE_EABI_10_2_1"
    GNU_X86_64_LINUX_EABI_10_3_0 = "GNU_X86_64_LINUX_EABI_10_3_0"
    GNU_M68K_LINUX_10 = "GNU_M68K_LINUX_10"
    VBCC_M68K_0_9 = "VBCC_M68K_0_9"
    GNU_AARCH64_LINUX_10 = "GNU_AARCH64_LINUX_10"
    GNU_AVR_5 = "GNU_AVR_5"
