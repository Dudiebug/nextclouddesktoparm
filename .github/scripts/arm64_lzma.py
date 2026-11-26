#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Decide how the pinned Craft liblzma and Python recipes need ARM64 fixes.

Older Craft revisions built xz 5.2.3 from its windows/xz_win.sln project with
MSBuild. That solution only declares Win32 and x64, so the ARM64 layer clones
the x64 configurations (see patch 6 in patch-craft-arm64.py).

From Nextcloud Craft 6e684481 (stable-35.0-qt-6.11.2, used by 35.0.4) liblzma
is a plain CMake package for xz 5.8.4. xz's CMake build supports MSVC ARM64
natively, so no MSBuild patch is needed. Since xz 5.6.3 its MSVC build names
the DLL liblzma.dll but the import library lzma.lib (so that pkgconf works).
KDE Craft changed its Python recipe to link "lzma" together with that liblzma
update; Nextcloud's backport kept addLib("LZMA", "liblzma"), so a from-source
MSVC Python build would fail to link lib/liblzma.lib. Upstream's x64 CI does
not notice because it restores Python from a binary cache; the ARM64 build
compiles Python from source.
"""

import re

MSBUILD_MARKER = "class PackageMSBuild(MSBuildPackageBase):"

MSBUILD_ANCHOR = (
    'class PackageMSBuild(MSBuildPackageBase):\n'
    '    def __init__(self, **kwargs):\n'
    '        super().__init__(**kwargs)\n'
    '        self.subinfo.options.configure.projectFile = self.sourceDir() / "windows/xz_win.sln"\n'
    '        self.msbuildTargets = ["liblzma_dll"]\n'
    '\n'
    '    def install(self):\n'
)
MSBUILD_REPLACEMENT = (
    'class PackageMSBuild(MSBuildPackageBase):\n'
    '    def __init__(self, **kwargs):\n'
    '        super().__init__(**kwargs)\n'
    '        self.subinfo.options.configure.projectFile = self.sourceDir() / "windows/xz_win.sln"\n'
    '        self.msbuildTargets = ["liblzma_dll"]\n'
    '\n'
    '    def configure(self):\n'
    '        # The xz 5.2.3 windows/ project files only declare Win32, x64, and\n'
    '        # ReleaseMT|x64 platform configurations. On a Windows ARM64 host\n'
    '        # MSBuild rejects /p:Platform=arm64 (the platform Craft passes for\n'
    '        # an arm64 target) with MSB4126 "The specified solution\n'
    '        # configuration \'Release|arm64\' is invalid". xz itself is pure C\n'
    '        # with no x86-specific inline assembly, so cloning the x64 sections\n'
    '        # of xz_win.sln, liblzma.vcxproj, and liblzma_dll.vcxproj as arm64\n'
    '        # siblings is sufficient: MSBuild\'s v143 toolset handles arm64\n'
    '        # codegen automatically once an arm64 platform is declared.\n'
    '        from CraftCompiler import CraftCompiler\n'
    '        if CraftCore.compiler.architecture == CraftCompiler.Architecture.arm64:\n'
    '            self._addArm64PlatformConfigs()\n'
    '        return super().configure()\n'
    '\n'
    '    def _addArm64PlatformConfigs(self):\n'
    '        import re\n'
    '        windowsDir = self.sourceDir() / "windows"\n'
    '        slnPath = windowsDir / "xz_win.sln"\n'
    '        with open(slnPath, "r", encoding="utf-8", newline="") as f:\n'
    '            slnLines = f.readlines()\n'
    '        if not any("|arm64" in ln for ln in slnLines):\n'
    '            outLines = []\n'
    '            for ln in slnLines:\n'
    '                outLines.append(ln)\n'
    '                if "|x64" in ln:\n'
    '                    outLines.append(ln.replace("|x64", "|arm64"))\n'
    '            with open(slnPath, "w", encoding="utf-8", newline="") as f:\n'
    '                f.writelines(outLines)\n'
    '        # Non-greedy block regex: capture each top-level XML element whose\n'
    '        # opening tag mentions "|x64" (in either an Include= or Condition=\n'
    '        # attribute) and clone it as an arm64 sibling. The .vcxproj files\n'
    '        # have no nested elements of the same name at the relevant depths,\n'
    '        # so a non-greedy match is unambiguous.\n'
    '        blockPattern = re.compile(r"(  <(\\w+)[^>]*\\|x64[^>]*>[\\s\\S]*?</\\2>)")\n'
    '        for vcxproj in ("liblzma.vcxproj", "liblzma_dll.vcxproj"):\n'
    '            path = windowsDir / vcxproj\n'
    '            with open(path, "r", encoding="utf-8", newline="") as f:\n'
    '                content = f.read()\n'
    '            if "|arm64" in content:\n'
    '                continue\n'
    '            def cloneBlock(m):\n'
    '                orig = m.group(1)\n'
    '                cloned = (\n'
    '                    orig.replace("|x64", "|arm64")\n'
    '                        .replace("<Platform>x64</Platform>", "<Platform>arm64</Platform>")\n'
    '                )\n'
    '                return orig + "\\n" + cloned\n'
    '            with open(path, "w", encoding="utf-8", newline="") as f:\n'
    '                f.write(blockPattern.sub(cloneBlock, content))\n'
    '\n'
    '    def install(self):\n'
)

CMAKE_PACKAGE = re.compile(r"^class Package\(CMakePackageBase\):", re.MULTILINE)
PYTHON_LZMA = re.compile(r'addLib\(\s*"LZMA"\s*,\s*"(?P<name>[A-Za-z0-9_.-]+)"\s*\)')


def liblzma_build_system(liblzma_blueprint: str) -> str:
    """Return "msbuild" or "cmake" for the pinned liblzma recipe."""
    if MSBUILD_MARKER in liblzma_blueprint:
        return "msbuild"
    if CMAKE_PACKAGE.search(liblzma_blueprint):
        return "cmake"
    raise ValueError("liblzma.py is neither the MSBuild xz_win.sln recipe nor a CMakePackageBase recipe")


def liblzma_import_library(liblzma_blueprint: str) -> str:
    """Name of the import library the pinned liblzma recipe installs with MSVC."""
    return "liblzma" if liblzma_build_system(liblzma_blueprint) == "msbuild" else "lzma"


def patch_python_lzma_link(python_blueprint: str, liblzma_blueprint: str) -> tuple[str, bool]:
    """Make Craft's MSVC Python recipe link the import library liblzma installs.

    Returns the (possibly unchanged) Python recipe and whether it changed.
    """
    names = [match.group("name") for match in PYTHON_LZMA.finditer(python_blueprint)]
    if len(names) != 1:
        raise ValueError(f'Expected one addLib("LZMA", ...) in the Python blueprint, found {names}')
    wanted = liblzma_import_library(liblzma_blueprint)
    if names[0] == wanted:
        return python_blueprint, False
    patched = PYTHON_LZMA.sub(f'addLib("LZMA", "{wanted}")', python_blueprint, count=1)
    return patched, True


def patch_liblzma_blueprint(liblzma_blueprint: str) -> tuple[str, bool]:
    """Apply the ARM64 MSBuild fix to the xz_win.sln recipe; leave CMake recipes alone."""
    if liblzma_build_system(liblzma_blueprint) == "cmake":
        return liblzma_blueprint, False
    if MSBUILD_REPLACEMENT in liblzma_blueprint:
        return liblzma_blueprint, False
    if MSBUILD_ANCHOR not in liblzma_blueprint:
        raise ValueError("could not find PackageMSBuild __init__/install block in liblzma.py")
    return liblzma_blueprint.replace(MSBUILD_ANCHOR, MSBUILD_REPLACEMENT, 1), True
