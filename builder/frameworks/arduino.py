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

"""
Arduino

Arduino Wiring-based Framework allows writing cross-platform software to
control devices attached to a wide range of Arduino boards to create all
kinds of creative coding, interactive objects, spaces or physical experiences.

http://arduino.cc/en/Reference/HomePage
"""

from os.path import isdir, join

from SCons.Script import DefaultEnvironment

env = DefaultEnvironment()
platform = env.PioPlatform()
board = env.BoardConfig()
build_core = board.get("build.core", "")

FRAMEWORK_DIR = platform.get_package_dir("framework-arduino-cmsis5")
assert isdir(FRAMEWORK_DIR)

CPPDEFINES = [
    ("F_CPU", "$BOARD_F_CPU"),
    ("ARDUINO", 10808)
]

env.Append(
    ARFLAGS=["rc"],
    ASFLAGS=["-x", "assembler-with-cpp"],

    CFLAGS=[
        "-std=gnu11",
        "-fno-fat-lto-objects",
        "-D__nop=__NOP" #fix bug? in cmsis driver, uses __nop instead of __NOP
    ],

    CCFLAGS=[
        "-O0",  # optimize for size
        "-Wall",  # show warnings
        "-ffunction-sections",  # place each function in its own section
        "-fdata-sections",
        "-fsingle-precision-constant",
        "-flto",
        "-mthumb",
        "--specs=nano.specs",
        "--specs=nosys.specs",
    ],

    CXXFLAGS=[
        "-std=gnu++17",
        "-fno-rtti",
        "-fno-exceptions",
        "-fno-use-cxa-atexit",
        "-fno-common",
        "-fno-threadsafe-statics"
    ],

    LINKFLAGS=[
        "-O0",
        "-Wl,--gc-sections,--relax",
        "-u_printf_float",
        "-flto",
        "-Wall",  # show warnings
        "-ffunction-sections",  # place each function in its own section
        "-fdata-sections",
        "-fsingle-precision-constant",
        "-flto",
        "-mthumb",
        "--specs=nano.specs",
        "--specs=nosys.specs",
    ],

    CPPDEFINES=CPPDEFINES,

    LIBS=["c", "gcc", "m"],

    LIBSOURCE_DIRS=[
        join(FRAMEWORK_DIR, "libraries")
    ],

    CPPPATH=[
        join(FRAMEWORK_DIR, "cores", build_core),
        join(FRAMEWORK_DIR, "cores", build_core, "api", "deprecated"),
        join(FRAMEWORK_DIR, "cores", build_core, "api", "deprecated-avr-comp"),
    ]
)

# copy CCFLAGS to ASFLAGS (-x assembler-with-cpp mode)
env.Append(ASFLAGS=env.get("CCFLAGS", [])[:])

#
# Target: Build Core Library
#

libs = []

if "build.variant" in board:
    variants_dir = join(
        "$PROJECT_DIR", board.get("build.variants_dir")) if board.get(
            "build.variants_dir", "") else join(FRAMEWORK_DIR, "variants")

    env.Append(
        CPPPATH=[
            join(variants_dir, board.get("build.variant"))
        ]
    )
    libs.append(env.BuildLibrary(
        join("$BUILD_DIR", "FrameworkArduinoVariant"),
        join(variants_dir, board.get("build.variant"))
    ))

libs.append(env.BuildLibrary(
    join("$BUILD_DIR", "FrameworkArduino"),
    join(FRAMEWORK_DIR, "cores", build_core)
))

env.Prepend(LIBS=libs)
