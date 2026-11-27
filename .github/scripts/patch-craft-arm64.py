#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Dudiebug
# SPDX-License-Identifier: GPL-2.0-or-later

import sys, re
helper_path = sys.argv[1]
git_path    = sys.argv[2]
perl_path   = sys.argv[3]
openssl_path = sys.argv[4]
liblzma_path = sys.argv[5]
libunistring_path = sys.argv[6]
libffi_path = sys.argv[7]
python_path = sys.argv[8]

# Patch 1: add ARM64 entries to the architectures dicts in
# CraftSetupHelper.getMSVCEnv.
with open(helper_path, 'r', encoding='utf-8') as f:
    s = f.read()
s_new = re.sub(
    r'(CraftCore\.compiler\.Architecture\.x86_64: "amd64",\r?\n)(\s*\})',
    r'\1                CraftCore.compiler.Architecture.arm64: "arm64",\n\2',
    s, count=1,
)
if s_new == s:
    print('ERROR: could not patch native architectures dict', file=sys.stderr)
    sys.exit(1)
s_new2 = re.sub(
    r'(CraftCore\.compiler\.Architecture\.x86_64: "x86_amd64",\r?\n)(\s*\})',
    r'\1                CraftCore.compiler.Architecture.arm64: "x86_arm64",\n\2',
    s_new, count=1,
)
if s_new2 == s_new:
    print('ERROR: could not patch non-native architectures dict', file=sys.stderr)
    sys.exit(1)
with open(helper_path, 'w', encoding='utf-8') as f:
    f.write(s_new2)
print(f'Patched {helper_path}: added ARM64 architecture entries')

# Patch 2: dev-utils/_windows/git/git.py locateGit() — handle the
# Git for Windows ARM64 (clangarm64) layout where git.exe lives at
# Git\clangarm64\bin\git.exe but the shared MSYS userland stays at
# Git\usr\bin. Without this fix, dev-utils/patch and dev-utils/sed
# fail post-install because they look up patch.exe / sed.exe at
# locateGit().parent / "usr/bin/X.exe", which under the new layout
# resolves to Git\clangarm64\usr\bin\X.exe (does not exist).
with open(git_path, 'r', encoding='utf-8') as f:
    s = f.read()
old_block = (
    '        # check whether git is installed by the system or us\n'
    '        if (CraftCore.standardDirs.craftRoot() / "dev-utils") in gitPath.parents:\n'
    '            return CraftCore.standardDirs.craftRoot() / "dev-utils/git/bin"\n'
    '        return gitPath.parent\n'
)
new_block = (
    '        # check whether git is installed by the system or us\n'
    '        if (CraftCore.standardDirs.craftRoot() / "dev-utils") in gitPath.parents:\n'
    '            return CraftCore.standardDirs.craftRoot() / "dev-utils/git/bin"\n'
    '        # Downstream consumers (dev-utils/patch, dev-utils/sed) expect\n'
    '        # locateGit().parent to be the MSYS root containing usr/bin/X.exe.\n'
    '        # Legacy x64 Git for Windows lays out as Git\\bin\\git.exe so\n'
    '        # gitPath.parent = Git\\bin and (Git\\bin).parent = Git, contract\n'
    '        # holds. The Git for Windows ARM64 (clangarm64) build instead\n'
    '        # uses Git\\clangarm64\\bin\\git.exe but keeps the shared MSYS\n'
    '        # userland at Git\\usr\\bin, so .parent.parent = Git\\clangarm64\n'
    '        # and the contract breaks. Detect by looking for usr\\bin and\n'
    '        # return a path one level shifted so the contract still holds.\n'
    '        binDir = gitPath.parent\n'
    '        if (binDir.parent / "usr" / "bin").exists():\n'
    '            return binDir\n'
    '        if (binDir.parent.parent / "usr" / "bin").exists():\n'
    '            return binDir.parent.parent / "bin"\n'
    '        return binDir\n'
)
if old_block not in s:
    print('ERROR: could not find locateGit() block in git.py', file=sys.stderr)
    sys.exit(1)
with open(git_path, 'w', encoding='utf-8') as f:
    f.write(s.replace(old_block, new_block))
print(f'Patched {git_path}: locateGit() handles ARM64 Git for Windows layout')

# Patch 3: dev-utils/perl/perl.py CRAFT_WIN64 — Perl 5.40's win32/Makefile
# already handles ARM64 (sets WIN64=define when PROCESSOR_ARCHITECTURE is
# AMD64, IA64, or ARM64), but only when WIN64 is empty so its auto-detect
# block runs. The Craft blueprint forces WIN64=undef for any non-x86_64
# target, which under arm64 produces a 64-bit ARM64 miniperl.exe compiled
# with 32-bit type assumptions; the resulting binary crashes with
# 0xc0000005 the moment perl tries to use it. Extend the 64-bit branch
# to include arm64 so the Makefile can self-configure.
with open(perl_path, 'r', encoding='utf-8') as f:
    s = f.read()
old_perl = '"CRAFT_WIN64": "" if CraftCore.compiler.architecture == CraftCompiler.Architecture.x86_64 else "undef",'
new_perl = '"CRAFT_WIN64": "" if CraftCore.compiler.architecture in (CraftCompiler.Architecture.x86_64, CraftCompiler.Architecture.arm64) else "undef",'
if old_perl not in s:
    print('ERROR: could not find CRAFT_WIN64 ternary in perl.py', file=sys.stderr)
    sys.exit(1)
s = s.replace(old_perl, new_perl)
with open(perl_path, 'w', encoding='utf-8') as f:
    f.write(s)
print(f'Patched {perl_path}: CRAFT_WIN64 empty for arm64 (lets Makefile auto-detect)')

# Patch 4: dev-utils/perl/perl.py _globEnv() — Perl 5.40's win32/Makefile
# recipe for ..\git_version.h is "cd .. && miniperl -Ilib make_patchnum.pl
# && cd win32". It uses bare "miniperl" rather than $(MINIPERL), and
# assumes cmd.exe will find miniperl.exe in the current directory after
# the cd. Modern Windows cmd.exe does not search the cwd for executables,
# so the recipe fails with "'miniperl' is not recognized" even though
# miniperl.exe is right there. Put the perl source root on PATH so the
# bare name resolves via PATH lookup.
old_globenv = (
    '    def _globEnv(self):\n'
    '        env = {}\n'
    '        if CraftCore.compiler.isMSVC():\n'
    '            env = {"PATH": f"{self.blueprintDir()};{os.environ[\'PATH\']}"}\n'
    '        return env\n'
)
new_globenv = (
    '    def _globEnv(self):\n'
    '        env = {}\n'
    '        if CraftCore.compiler.isMSVC():\n'
    '            # Perl 5.40 win32/Makefile rule for ..\\git_version.h runs\n'
    '            # "cd .. && miniperl -Ilib make_patchnum.pl" with a bare\n'
    '            # "miniperl" name. Modern cmd.exe does not search the cwd\n'
    '            # for executables, so even though miniperl.exe is right\n'
    '            # there it is not found. Put the perl source root on PATH\n'
    '            # so the bare name resolves via PATH lookup.\n'
    '            env = {"PATH": f"{self.sourceDir()};{self.blueprintDir()};{os.environ[\'PATH\']}"}\n'
    '        return env\n'
)
if old_globenv not in s:
    print('ERROR: could not find _globEnv() block in perl.py', file=sys.stderr)
    sys.exit(1)
with open(perl_path, 'w', encoding='utf-8') as f:
    f.write(s.replace(old_globenv, new_globenv))
print(f'Patched {perl_path}: _globEnv adds sourceDir to PATH for bare-miniperl recipe')

# Patch 5: libs/openssl/openssl.py — extend the Configure target
# ternary to recognise arm64. The upstream blueprint only knows
# about x86_64 (VC-WIN64A) and falls back to VC-WIN32 for any
# other architecture, so on a Windows ARM64 host OpenSSL ends up
# configured for 32-bit x86: the C sources are built with
# -DAES_ASM/-DOPENSSL_IA32_SSE2/-DSHA1_ASM/etc. and Configure
# emits nasm rules for x86 .asm files. The resulting object
# files cannot be linked into the otherwise-arm64 build. OpenSSL
# ships a proper VC-WIN64-ARM target that uses the ARM64 .S
# perlasm modules, so select it explicitly for arm64.
with open(openssl_path, 'r', encoding='utf-8') as f:
    s = f.read()
old_openssl = '                "VC-WIN64A" if CraftCore.compiler.architecture == CraftCompiler.Architecture.x86_64 else "VC-WIN32",\n'
new_openssl = (
    '                # Pick the OpenSSL Configure target that matches the host arch.\n'
    '                # The upstream blueprint only knows about x86_64 (VC-WIN64A) and\n'
    '                # falls back to VC-WIN32 for everything else, which on a Windows\n'
    '                # ARM64 host produces a build configured for 32-bit x86 (the C\n'
    '                # sources get compiled with -DAES_ASM/-DOPENSSL_IA32_SSE2/etc.\n'
    '                # and Configure emits nasm rules for x86 .asm files). OpenSSL\n'
    '                # ships a proper VC-WIN64-ARM target that uses the ARM64 .S\n'
    '                # perlasm modules, so select it for arm64.\n'
    '                ("VC-WIN64A" if CraftCore.compiler.architecture == CraftCompiler.Architecture.x86_64\n'
    '                 else "VC-WIN64-ARM" if CraftCore.compiler.architecture == CraftCompiler.Architecture.arm64\n'
    '                 else "VC-WIN32"),\n'
)
if old_openssl not in s:
    print('ERROR: could not find VC-WIN64A/VC-WIN32 ternary in openssl.py', file=sys.stderr)
    sys.exit(1)
with open(openssl_path, 'w', encoding='utf-8') as f:
    f.write(s.replace(old_openssl, new_openssl))
print(f'Patched {openssl_path}: openssl Configure target VC-WIN64-ARM for arm64')

# Patch 6: libs/liblzma/liblzma.py. Older Craft revisions build xz 5.2.3
# from windows/xz_win.sln, whose project files only declare Win32 and x64:
# MSBuild rejects /p:Platform=arm64 with MSB4126. arm64_lzma clones the x64
# configurations as arm64 siblings. From Craft 6e684481 liblzma is a CMake
# package for xz 5.8.4, which supports MSVC ARM64 natively and needs no patch.
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parent))
import arm64_lzma

with open(liblzma_path, 'r', encoding='utf-8') as f:
    s = f.read()
try:
    s_new, liblzma_changed = arm64_lzma.patch_liblzma_blueprint(s)
except ValueError as error:
    print(f'ERROR: {liblzma_path}: {error}', file=sys.stderr)
    sys.exit(1)
if liblzma_changed:
    with open(liblzma_path, 'w', encoding='utf-8') as f:
        f.write(s_new)
    print(f'Patched {liblzma_path}: PackageMSBuild.configure() clones x64 platform configs as arm64')
else:
    print(f'Left {liblzma_path} unchanged: CMake xz build supports MSVC ARM64')

# Patch 7: libs/libunistring/libunistring.py
import stat, textwrap
with open(libunistring_path, 'r', encoding='utf-8') as f:
    s = f.read()
old_libunistring = (
    'class Package(AutoToolsPackageBase):\n'
    '    def __init__(self, **kwargs):\n'
    '        super().__init__(**kwargs)\n'
    '        self.shell.useMSVCCompatEnv = True\n'
)
new_libunistring = (
    'import stat\n'
    'import textwrap\n'
    'from CraftCore import CraftCore\n'
    '\n\n'
    'class Package(AutoToolsPackageBase):\n'
    '    def __init__(self, **kwargs):\n'
    '        super().__init__(**kwargs)\n'
    '        self.shell.useMSVCCompatEnv = True\n'
    '\n'
    '    def configure(self):\n'
    '        from CraftCompiler import CraftCompiler\n'
    '        if CraftCore.compiler.isWindows and CraftCore.compiler.architecture == CraftCompiler.Architecture.arm64:\n'
    '            self._installWindresArm64Wrapper()\n'
    '        return super().configure()\n'
    '\n'
    '    def _installWindresArm64Wrapper(self):\n'
    '        localBin = CraftCore.standardDirs.msysDir() / "usr" / "local" / "bin"\n'
    '        localBin.mkdir(parents=True, exist_ok=True)\n'
    '        wrapperPath = localBin / "windres"\n'
    '        if wrapperPath.exists():\n'
    '            return\n'
    '        realWindres = str(CraftCore.standardDirs.msysDir() / "usr" / "bin" / "windres.exe")\n'
    '        wrapperContent = textwrap.dedent(f"""\\\n'
    '            #!/usr/bin/env python\n'
    '            import subprocess, sys, os\n'
    '            REAL_WINDRES = r\'{realWindres}\'\n'
    '            output = None\n'
    '            i = 1\n'
    '            while i < len(sys.argv):\n'
    '                a = sys.argv[i]\n'
    '                if a in (\'-o\', \'--output\') and i + 1 < len(sys.argv):\n'
    '                    output = sys.argv[i + 1]\n'
    '                elif a.startswith(\'-o\') and len(a) > 2:\n'
    '                    output = a[2:]\n'
    '                i += 1\n'
    '            result = subprocess.run([REAL_WINDRES] + sys.argv[1:])\n'
    '            if result.returncode != 0:\n'
    '                sys.exit(result.returncode)\n'
    '            if output and os.path.exists(output):\n'
    '                with open(output, \'r+b\') as f:\n'
    '                    if f.read(2) == b\'\\\\x64\\\\x86\':\n'
    '                        f.seek(0); f.write(b\'\\\\x64\\\\xaa\')\n'
    '            sys.exit(0)\n'
    '        """)\n'
    '        wrapperPath.write_text(wrapperContent, encoding=\'utf-8\')\n'
    '        wrapperPath.chmod(wrapperPath.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)\n'
)
if old_libunistring not in s:
    print('ERROR: could not find Package class in libunistring.py', file=sys.stderr)
    sys.exit(1)
with open(libunistring_path, 'w', encoding='utf-8') as f:
    f.write(s.replace(old_libunistring, new_libunistring))
print(f'Patched {libunistring_path}: Package.configure() installs windres ARM64 wrapper')

# Patch 8: libs/libffi/libffi.py
with open(libffi_path, 'r', encoding='utf-8') as f:
    s = f.read()
old_libffi_import = 'from Package.AutoToolsPackageBase import AutoToolsPackageBase\nfrom Utils import CraftHash\n'
new_libffi_import = 'from Package.AutoToolsPackageBase import AutoToolsPackageBase\nfrom Utils import CraftHash\nfrom Utils.Arguments import Arguments\n'
if old_libffi_import not in s:
    print('ERROR: could not find AutoToolsPackageBase import in libffi.py', file=sys.stderr)
    sys.exit(1)
s = s.replace(old_libffi_import, new_libffi_import)
old_libffi_arch = (
    '            if CraftCore.compiler.architecture == CraftCompiler.Architecture.x86_64:\n'
    '                arch = " -m64"\n'
    '            self.subinfo.options.configure.args += [f"CCAS={wrapper}{arch}"]\n'
)
new_libffi_arch = (
    '            if CraftCore.compiler.architecture == CraftCompiler.Architecture.x86_64:\n'
    '                arch = " -m64"\n'
    '            elif CraftCore.compiler.architecture == CraftCompiler.Architecture.arm64:\n'
    '                arch = " -marm64"\n'
    '            self.subinfo.options.configure.args += [f"CCAS={wrapper}{arch}"]\n'
)
if old_libffi_arch not in s:
    print('ERROR: could not find CCAS arch block in libffi.py', file=sys.stderr)
    sys.exit(1)
s = s.replace(old_libffi_arch, new_libffi_arch)
old_libffi_tail = (
    '            self.subinfo.options.configure.cflags += " -DFFI_BUILDING_DLL"\n'
    '        self.subinfo.options.configure.args += [\n'
)
new_libffi_tail = (
    '            self.subinfo.options.configure.cflags += " -DFFI_BUILDING_DLL"\n'
    '\n'
    '        if CraftCore.compiler.isWindows and CraftCore.compiler.architecture == CraftCompiler.Architecture.arm64:\n'
    '            self.platform = Arguments([\n'
    '                "--host=aarch64-w64-mingw32",\n'
    '                "--build=aarch64-w64-mingw32",\n'
    '                "--target=aarch64-w64-mingw32",\n'
    '            ])\n'
    '\n'
    '        self.subinfo.options.configure.args += [\n'
)
if old_libffi_tail not in s:
    print('ERROR: could not find FFI_BUILDING_DLL tail block in libffi.py', file=sys.stderr)
    sys.exit(1)
with open(libffi_path, 'w', encoding='utf-8') as f:
    f.write(s.replace(old_libffi_tail, new_libffi_tail))
print(f'Patched {libffi_path}: ARM64 platform triple override and -marm64 CCAS flag')

# Patch 9: libs/python/python.py
with open(python_path, 'r', encoding='utf-8') as f:
    s = f.read()
old_python_install = (
    '        def install(self):\n'
    '            self.cleanImage()\n'
    '            verMinor = self.subinfo.buildTarget.split(".")[1]\n'
    '            debugSuffix = "_d" if self.buildType() == "Debug" else ""\n'
    '            for p in ["python", "pythonw", "venvlauncher", "venvwlauncher"]:\n'
    '                if not utils.copyFile(self.sourceDir() / f"PCbuild/amd64/{p}{debugSuffix}.exe", self.imageDir() / f"bin/{p}{debugSuffix}.exe"):\n'
)
new_python_install = (
    '        def install(self):\n'
    '            self.cleanImage()\n'
    '            verMinor = self.subinfo.buildTarget.split(".")[1]\n'
    '            debugSuffix = "_d" if self.buildType() == "Debug" else ""\n'
    '            from CraftCompiler import CraftCompiler\n'
    '            pcbuildArch = "arm64" if CraftCore.compiler.architecture == CraftCompiler.Architecture.arm64 else "amd64"\n'
    '            for p in ["python", "pythonw", "venvlauncher", "venvwlauncher"]:\n'
    '                if not utils.copyFile(self.sourceDir() / f"PCbuild/{pcbuildArch}/{p}{debugSuffix}.exe", self.imageDir() / f"bin/{p}{debugSuffix}.exe"):\n'
)
if old_python_install not in s:
    print('ERROR: could not find install() PCbuild/amd64 block in python.py', file=sys.stderr)
    sys.exit(1)
s = s.replace(old_python_install, new_python_install)
for old_ref, new_ref in [
    ('self.sourceDir() / "PCbuild/amd64/", self.imageDir() / "bin", ["*.dll"]',
     'self.sourceDir() / f"PCbuild/{pcbuildArch}/", self.imageDir() / "bin", ["*.dll"]'),
    ('self.sourceDir() / f"PCbuild/amd64/{p}{debugSuffix}.lib"',
     'self.sourceDir() / f"PCbuild/{pcbuildArch}/{p}{debugSuffix}.lib"'),
    ('self.sourceDir() / "PCbuild/amd64/", self.imageDir() / "bin/DLLs", ["*.pyd"]',
     'self.sourceDir() / f"PCbuild/{pcbuildArch}/", self.imageDir() / "bin/DLLs", ["*.pyd"]'),
]:
    if old_ref not in s:
        print(f'ERROR: PCbuild/amd64 reference not found: {old_ref!r}', file=sys.stderr)
        sys.exit(1)
    s = s.replace(old_ref, new_ref)
with open(python_path, 'w', encoding='utf-8') as f:
    f.write(s)
print(f'Patched {python_path}: PCbuild/amd64 -> PCbuild/{{pcbuildArch}} in install()')

# Patch 10: libs/python/python.py links the import library liblzma installs.
# xz >= 5.6.3 built with CMake and MSVC installs lib/lzma.lib (DLL still
# liblzma.dll); Nextcloud's Craft 6e684481 kept addLib("LZMA", "liblzma").
with open(python_path, 'r', encoding='utf-8') as f:
    s = f.read()
with open(liblzma_path, 'r', encoding='utf-8') as f:
    liblzma_source = f.read()
try:
    s_new, python_changed = arm64_lzma.patch_python_lzma_link(s, liblzma_source)
except ValueError as error:
    print(f'ERROR: {python_path}: {error}', file=sys.stderr)
    sys.exit(1)
if python_changed:
    with open(python_path, 'w', encoding='utf-8') as f:
        f.write(s_new)
    print(f'Patched {python_path}: MSVC Python links lib/{arm64_lzma.liblzma_import_library(liblzma_source)}.lib')
else:
    print(f'Left {python_path} LZMA link unchanged: lib/{arm64_lzma.liblzma_import_library(liblzma_source)}.lib')
