#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Dudiebug
# SPDX-License-Identifier: GPL-2.0-or-later

"""Apply Windows ARM64 fixes to stable Nextcloud/KDE Craft blueprints."""

import sys


def _read_normalized(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        source = f.read()
    line_ending = "\r\n" if "\r\n" in source else "\n"
    return source.replace("\r\n", "\n"), line_ending


def _write_preserving_line_endings(path, source, line_ending):
    if line_ending == "\r\n":
        source = source.replace("\n", "\r\n")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(source)


def patch_libjpeg(path):
    s, line_ending = _read_normalized(path)

    if "-DWITH_SIMD=OFF" in s:
        print(f"SKIP {path}: ARM64 SIMD patch already present")
        return

    old_imports = "import info\nfrom Package.CMakePackageBase import CMakePackageBase\nfrom Utils import CraftHash\n"
    new_imports = "import info\nfrom CraftCompiler import CraftCompiler\nfrom CraftCore import CraftCore\nfrom Package.CMakePackageBase import CMakePackageBase\nfrom Utils import CraftHash\n"
    if old_imports not in s:
        raise RuntimeError("libjpeg-turbo import block changed upstream")
    s = s.replace(old_imports, new_imports)

    needle = (
        '        else:\n'
        '            self.subinfo.options.configure.args += ["-DENABLE_SHARED=ON", "-DENABLE_STATIC=OFF"]\n'
    )
    replacement = needle + (
        '        if CraftCore.compiler.isWindows and CraftCore.compiler.architecture == CraftCompiler.Architecture.arm64:\n'
        '            self.subinfo.options.configure.args += ["-DWITH_SIMD=OFF"]\n'
    )
    if needle not in s:
        raise RuntimeError("libjpeg-turbo Package block changed upstream")
    s = s.replace(needle, replacement, 1)

    _write_preserving_line_endings(path, s, line_ending)
    print(f"Patched {path}: disabled x86 SIMD for Windows ARM64")


def patch_pixman(path):
    s, line_ending = _read_normalized(path)

    if "-Dmmx=disabled" in s and "-Dsse2=disabled" in s and "-Dssse3=disabled" in s:
        print(f"SKIP {path}: Windows ARM64 SIMD patch already present")
        return

    needle = (
        'class Package(MesonPackageBase):\n'
        '    def __init__(self, **kwargs):\n'
        '        super().__init__(**kwargs)\n'
    )
    replacement = needle + (
        '        from CraftCompiler import CraftCompiler\n'
        '        if CraftCore.compiler.isWindows and CraftCore.compiler.architecture == CraftCompiler.Architecture.arm64:\n'
        '            self.subinfo.options.configure.args += [\n'
        '                "-Da64-neon=disabled",\n'
        '                "-Dmmx=disabled",\n'
        '                "-Dsse2=disabled",\n'
        '                "-Dssse3=disabled",\n'
        '            ]\n'
    )
    if needle not in s:
        raise RuntimeError("pixman Package block changed upstream")
    s = s.replace(needle, replacement, 1)

    _write_preserving_line_endings(path, s, line_ending)
    print(f"Patched {path}: disabled unsupported SIMD paths for Windows ARM64")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: patch-kde-blueprints-arm64.py <libjpeg-turbo.py> <pixman.py>")
        sys.exit(2)
    patch_libjpeg(sys.argv[1])
    patch_pixman(sys.argv[2])
