# Copyright 2014-present PlatformIO <contact@platformio.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from platform import system
from os import makedirs
from os.path import isdir, join
from pathlib import Path

from platformio.package.download import FileDownloader
from zipfile import ZipFile
import tempfile

from SCons.Script import (
    ARGUMENTS,
    COMMAND_LINE_TARGETS,
    AlwaysBuild,
    Builder,
    Default,
    DefaultEnvironment,
)

env = DefaultEnvironment()
platform = env.PioPlatform()

platform_version  = str(int(''.join(['{0:0=3d}'.format(int(x)) for x in platform.version.split('.')]))) + 'UL'
framework_version = str(int(''.join(['{0:0=3d}'.format(int(x)) for x in platform.get_package_version('framework-arduino-cmsis5').split('.')]))) + 'UL'

if "BOARD" not in env:
    raise(Exception("No board in configuration"))

board = env.BoardConfig()
target_mcu = board.get("build.mcu").upper()

env.Replace(
    AR="arm-none-eabi-ar",
    AS="arm-none-eabi-as",
    CC="arm-none-eabi-gcc",
    CXX="arm-none-eabi-g++",
    GDB="arm-none-eabi-gdb",
    OBJCOPY="arm-none-eabi-objcopy",
    RANLIB="arm-none-eabi-ranlib",
    SIZETOOL="arm-none-eabi-size",

    ARFLAGS=[],

    ASFLAGS=[],
    CCFLAGS=[],
    CXXFLAGS=[],
    CPPDEFINES=[],
    LINKFLAGS=[],
    LIBS=[],

    SIZEPROGREGEXP=r"^(?:\.text|\.ramcode|\.data|\.rodata|\.text.align|\.ARM.exidx)\s+(\d+).*",
    SIZEDATAREGEXP=r"^(?:\.ram_isr_vector|\.ramcode|\.data|\.bss|\.noinit)\s+(\d+).*",
    SIZECHECKCMD="$SIZETOOL -A -d $SOURCES",
    SIZEPRINTCMD='$SIZETOOL -B -d $SOURCES',

    PROGSUFFIX=".elf"
)

# Allow user to override via pre:script
if env.get("PROGNAME", "program") == "program":
    env.Replace(PROGNAME="firmware")

env.Append(
    CCFLAGS=[
        "-mcpu=%s" % board.get("build.cpu")
    ],
    LINKFLAGS=[
        "-mcpu=%s" % board.get("build.cpu")
    ]
)

env.Append(
    ASFLAGS=env.get("CCFLAGS", [])[:],

    BUILDERS=dict(
        ElfToBin=Builder(
            action=env.VerboseAction(" ".join([
                "$OBJCOPY",
                "-O",
                "binary",
                "$SOURCES",
                "$TARGET"
            ]), "Building $TARGET"),
            suffix=".bin"
        ),
        ElfToHex=Builder(
            action=env.VerboseAction(" ".join([
                "$OBJCOPY",
                "-O",
                "ihex",
                "-R",
                ".eeprom",
                "$SOURCES",
                "$TARGET"
            ]), "Building $TARGET"),
            suffix=".hex"
        )
    )
)

cmsis_platform_path = Path(platform.manifest_path).parents[0]

cmsis5_pack = board.get("pack.cmsis")
cmsis5_extract_loc = join(cmsis_platform_path, ".pack", Path(cmsis5_pack).stem)
if (not Path(cmsis5_extract_loc).exists()):
    print("Downloading {}".format(cmsis5_pack))
    keil_pack = FileDownloader(cmsis5_pack, tempfile.gettempdir())
    keil_pack.start()
    print("Unpacking to {}".format(cmsis5_extract_loc))
    with ZipFile(keil_pack.get_filepath(), 'r') as zip_ref:
        zip_ref.extractall(cmsis5_extract_loc)

# https://developer.arm.com/tools-and-software/embedded/cmsis/cmsis-search
required_keil_pack = board.get("pack.mcu_driver")
keil_pack_extract_loc = join(cmsis_platform_path, ".pack", Path(required_keil_pack).stem)
if (not Path(keil_pack_extract_loc).exists()):
    print("Downloading {}".format(required_keil_pack))
    keil_pack = FileDownloader(required_keil_pack, tempfile.gettempdir())
    keil_pack.start()
    print("Unpacking to {}".format(keil_pack_extract_loc))
    with ZipFile(keil_pack.get_filepath(), 'r') as zip_ref:
        zip_ref.extractall(keil_pack_extract_loc)


#TODO: parse pdcs file for build information

# Experiment to parse the pdsc file for data about the build
# import xml.etree.ElementTree as ET
# available_devices = {}
# tree = ET.parse(join(keil_pack_extract_loc, "Keil.LPC4000_DFP.pdsc"))
# root = tree.getroot()
# devices = root.find("devices")
# family = devices.find("family")
# for fam in family.findall("subFamily"):
#     for device in fam.findall("device"):
#         available_devices[device.get("Dname")] = { "FPU" : device.find("processor").get("Dfpu"), "CLOCK" : device.find("processor").get("Dclock") }
# for d,dev in available_devices.items():
#     print("{} : {}".format(d, dev))


arch = {
    "cortex-m3": "ARMCM3",
    "cortex-m4": "ARMCM4"
}[board.get("build.cpu")]

env.Append(
    CPPDEFINES={
        "ARMCM3" : ["CORE_M3", "ARMCM3"],
        "ARMCM4" : ["CORE_M4", "ARMCM4_FP"],
    }[arch]
)

env.Append(
    CPPDEFINES={
        "lpc1768" : ["LPC175x_6x"],
        "lpc1769" : ["LPC175x_6x"],
    }[board.get("build.mcu")]
)

driver_filter = {
    "lpc1768" : "*_LPC17xx*",
    "lpc1769" : "*_LPC17xx*",
    "lpc4078" : "*_LPC40xx*",
}[board.get("build.mcu")]

cmsis_core_include = join(cmsis5_extract_loc, "CMSIS/Core/Include")
cmsis_driver_include = join(cmsis5_extract_loc, "CMSIS/Driver/Include")

cmsis_device_include = join(cmsis5_extract_loc, "Device/ARM/{}/Include".format(arch))
cmsis_device_asm = join(cmsis5_extract_loc, "Device/ARM/{}/Source/GCC".format(arch))
cmsis_device_link_script = join(cmsis_platform_path, "system/{}/gcc_arm.ld".format(board.get("build.mcu")))

if env.get("LDSCRIPT_PATH") == None:
    env.Replace(LDSCRIPT_PATH=cmsis_device_link_script)

env.Append(
    CPPPATH=[
        cmsis_core_include,
        cmsis_driver_include,
        cmsis_device_include,
        join(keil_pack_extract_loc, "Device", "Include"),
        join(keil_pack_extract_loc, "RTE_Driver"),
        join(cmsis_platform_path, board.get("RTE_config_path"))
    ]
)

# TODO: these source files can only be build if the feature is enabled, plus other conflicts
env.BuildSources(join("$BUILD_DIR", "FrameworkCMSIS", "driver"), keil_pack_extract_loc, "-<*> +<RTE_Driver/{}.c> -<RTE_Driver/CAN*.c> -<RTE_Driver/USBH*.c> -<RTE_Driver/EMAC*.c> -<RTE_Driver/SPI*.c>".format(driver_filter))
env.BuildSources(join("$BUILD_DIR", "FrameworkCMSIS", "core"), join(cmsis_platform_path, ""), "-<*> +<system/{}/src/*.c>".format(board.get("build.mcu")))

#
# Target: Build executable and linkable firmware
#

target_elf = None
if "nobuild" in COMMAND_LINE_TARGETS:
    target_firm = join("$BUILD_DIR", "${PROGNAME}.bin")
else:
    target_elf = env.BuildProgram()
    target_firm = env.ElfToBin(join("$BUILD_DIR", "${PROGNAME}"), target_elf)

AlwaysBuild(env.Alias("nobuild", target_firm))
target_buildprog = env.Alias("buildprog", target_firm, target_firm)

#
# Target: Print binary size
#

target_size = env.Alias(
    "size", target_elf,
    env.VerboseAction("$SIZEPRINTCMD", "Calculating size $SOURCE"))
AlwaysBuild(target_size)

#
# Target: Upload by default .bin file
#

upload_protocol = env.subst("$UPLOAD_PROTOCOL")
debug_server = board.get("debug.tools", {}).get(
    upload_protocol, {}).get("server")
upload_actions = []

if upload_protocol == "mbed":
    upload_actions = [
        env.VerboseAction(env.AutodetectUploadPort, "Looking for upload disk..."),
        env.VerboseAction(env.UploadToDisk, "Uploading $SOURCE")
    ]

elif upload_protocol.startswith("jlink"):
    def _jlink_cmd_script(env, source):
        build_dir = env.subst("$BUILD_DIR")
        if not isdir(build_dir):
            makedirs(build_dir)
        script_path = join(build_dir, "upload.jlink")
        commands = ["h", "loadbin %s, %s" % (source, board.get("upload.offset_address", "0x0")), "r", "q"]
        with open(script_path, "w") as fp:
            fp.write("\n".join(commands))
        return script_path

    env.Replace(
        __jlink_cmd_script=_jlink_cmd_script,
        UPLOADER="JLink.exe" if system() == "Windows" else "JLinkExe",
        UPLOADERFLAGS=[
            "-device", board.get("debug", {}).get("jlink_device"),
            "-speed", "4000",
            "-if", ("jtag" if upload_protocol == "jlink-jtag" else "swd"),
            "-autoconnect", "1"
        ],
        UPLOADCMD="$UPLOADER $UPLOADERFLAGS -CommanderScript ${__jlink_cmd_script(__env__, SOURCE)}"
    )
    upload_actions = [env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")]

elif upload_protocol.startswith("blackmagic"):
    env.Replace(
        UPLOADER="$GDB",
        UPLOADERFLAGS=[
            "-nx",
            "--batch",
            "-ex", "target extended-remote $UPLOAD_PORT",
            "-ex", "monitor %s_scan" %
            ("jtag" if upload_protocol == "blackmagic-jtag" else "swdp"),
            "-ex", "attach 1",
            "-ex", "load",
            "-ex", "compare-sections",
            "-ex", "kill"
        ],
        UPLOADCMD="$UPLOADER $UPLOADERFLAGS $BUILD_DIR/${PROGNAME}.elf"
    )
    upload_actions = [
        env.VerboseAction(env.AutodetectUploadPort, "Looking for BlackMagic port..."),
        env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")
    ]

elif debug_server and debug_server.get("package") == "tool-pyocd":
    env.Replace(
        UPLOADER=join(platform.get_package_dir("tool-pyocd") or "",
                      "pyocd-flashtool.py"),
        UPLOADERFLAGS=debug_server.get("arguments", [])[1:],
        UPLOADCMD='"$PYTHONEXE" "$UPLOADER" $UPLOADERFLAGS $SOURCE'
    )
    upload_actions = [
        env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")
    ]

# custom upload tool
elif "UPLOADCMD" in env:
    upload_actions = [env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")]

else:
    sys.stderr.write("Warning! Unknown upload protocol %s\n" % upload_protocol)

AlwaysBuild(env.Alias("upload", target_firm, upload_actions))

#
# Default targets
#

Default([target_buildprog, target_size])
