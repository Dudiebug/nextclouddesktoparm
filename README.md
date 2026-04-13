<!--
  - SPDX-FileCopyrightText: 2026 Dudiebug
  - SPDX-FileCopyrightText: 2017 Nextcloud GmbH and Nextcloud contributors
  - SPDX-FileCopyrightText: 2011 Nextcloud GmbH and Nextcloud contributors
  - SPDX-License-Identifier: GPL-2.0-or-later
-->
# Native Windows ARM64 build of Nextcloud Desktop Client

A personal build of [`nextcloud/desktop`](https://github.com/nextcloud/desktop) with native Windows on ARM support. Runs on Snapdragon X Elite, Surface Pro X, and similar devices **without** Prism x64 emulation.

**[⬇ Download the installer](../../releases/latest)**

---

## Heads up before you install

I built this for myself. I'm not a developer — the entire port was written by [Claude Code](https://www.anthropic.com/claude-code) (Opus 4.6) under my direction, because I wanted native ARM64 sync on my Windows on ARM device and upstream doesn't ship it.

**This is not a maintained product.** I can't meaningfully review contributor PRs, I can only fix bugs that Claude can help me fix, and I cannot support thousands of users. If you need production-grade Nextcloud sync on Windows on ARM today, use the [official upstream build under Prism emulation](https://nextcloud.com/install/#install-clients).

If you want to try it anyway, great — here's what to expect.

## Install

1. Download `Nextcloud-*-arm64-setup.exe` from the [Releases page](../../releases/latest)
2. Run it. SmartScreen will flag it (unsigned, new binary) — click **More info** → **Run anyway**
3. Sign in with your Nextcloud server URL and credentials

### Verify it's actually native

Open **Task Manager** → **Details** tab → right-click any column header → **Select columns** → enable **Architecture**. The `nextcloud.exe` process should show **ARM64**, not **x64**. If it shows x64 you somehow installed the wrong build.

## Why a native build matters on Windows on ARM

File sync is the worst case for x64-on-ARM emulation:

- **Syscall-heavy workload.** Every file operation crosses the emulation boundary.
- **Always-on background process.** Emulated processes drain ARM laptop batteries noticeably faster than native ones.
- **Shell extensions are fragile.** File Explorer overlay icons and context menus run through shell extension DLLs, and emulated shell extensions have [known compatibility issues](https://learn.microsoft.com/en-us/windows/arm/arm64x-build) on Windows on ARM.

A native build fixes all three.

## Dear Nextcloud team, or any Windows / C++ developer reading this

**Please take this upstream.** The entire "port" is one Python script — [`.github/scripts/patch-craft-arm64.py`](.github/scripts/patch-craft-arm64.py) — that makes 10 small fixes to upstream KDE Craft and its dependency blueprints so `craft --install-deps nextcloud-client` succeeds on a Windows ARM64 host. **None of the patches touch a single line of Nextcloud source code.** Every fix is in upstream Craft or `craft-blueprints-kde`.

### The core problem

KDE Craft — the build system Nextcloud uses on Windows — has **zero ARM64 Windows support**. It only knows about x86 and x86_64. Every patch below is fixing a place where the code assumed *Windows = x86 or x64*.

### What the script patches

**Patch 1 — `CraftSetupHelper.py`: MSVC architecture mapping**

Adds `arm64` entries to the `architectures` dictionary that maps Craft's architecture enum to `vcvarsall.bat` arguments.

*Why:* Without this, Craft crashes immediately on ARM64 Windows with `KeyError: <Architecture.arm64: 40>` — the MSVC compiler environment can't be initialized at all.

- **Before:** only knows `x86 → "x86"` and `x86_64 → "amd64"`
- **After:** also knows `arm64 → "arm64"` (native) and `arm64 → "x86_arm64"` (cross)

---

**Patch 2 — `libs/zlib/zlib.py`: dead download URL**

Replaces `https://www.zlib.net/zlib-{ver}.tar.xz` with the GitHub release URL.

*Why:* zlib.net moves old versions to `/fossils/` when a new version ships, 404-ing the hard-coded URL. Not ARM64-specific — just broken for everyone using this pinned Craft revision.

---

**Patch 3 — `dev-utils/_windows/git/git.py`: Git for Windows ARM64 layout**

Fixes `locateGit()` to handle the ARM64 directory structure.

*Why:* x64 Git for Windows puts `git.exe` at `Git\bin\git.exe`. ARM64 Git puts it at `Git\clangarm64\bin\git.exe` but keeps the MSYS tools at `Git\usr\bin`. Craft's `dev-utils/patch` and `dev-utils/sed` locate themselves relative to `git.exe`'s parent directory, so on ARM64 they look in `Git\clangarm64\usr\bin\` — which doesn't exist. The patch detects the ARM64 layout and adjusts the path.

---

**Patch 4 — `dev-utils/perl/perl.py` (`CRAFT_WIN64` flag)**

Changes `CRAFT_WIN64` from `"undef"` to `""` (empty, meaning auto-detect) for ARM64.

*Why:* Perl 5.40's Makefile auto-detects ARM64 and sets `WIN64=define` when it sees `PROCESSOR_ARCHITECTURE=ARM64`. But Craft forces `WIN64=undef` for anything that isn't x86_64, which makes Perl compile as 32-bit. The resulting `miniperl.exe` crashes with `0xc0000005` (access violation) because it's a 64-bit ARM64 binary with 32-bit pointer assumptions.

---

**Patch 5 — `dev-utils/perl/perl.py` (PATH for miniperl)**

Adds Perl's source directory to `PATH` during the build.

*Why:* Perl's Makefile runs `cd .. && miniperl -Ilib make_patchnum.pl` using a bare `miniperl` command. Modern Windows cmd.exe doesn't search the current directory for executables, so even though `miniperl.exe` is right there, the build fails with `'miniperl' is not recognized`. Adding the source dir to `PATH` fixes it.

---

**Patch 6 — `libs/openssl/openssl.py`: ARM64 Configure target**

Adds `VC-WIN64-ARM` as the OpenSSL Configure target for ARM64.

*Why:* The blueprint only knows `VC-WIN64A` (x64) and `VC-WIN32` (x86). On ARM64 it falls through to `VC-WIN32`, which configures OpenSSL for 32-bit x86 — enabling x86 assembly (SSE2, AES-NI), generating NASM rules for `.asm` files, and setting `-DOPENSSL_IA32_SSE2`. The resulting objects can't link with the rest of the ARM64 build. OpenSSL already has a `VC-WIN64-ARM` target that uses ARM64 perlasm modules.

---

**Patch 7 — `libs/liblzma/liblzma.py`: ARM64 MSBuild platform**

Injects a `configure()` method that clones the x64 platform configurations as ARM64 in the `.sln` and `.vcxproj` files.

*Why:* xz 5.2.3 predates Windows-on-ARM. Its project files only declare `Win32` and `x64` platforms. When Craft passes `/p:Platform=arm64` to MSBuild, it fails with `MSB4126: The specified solution configuration 'Release|arm64' is invalid`. Since xz is pure C with no x86 assembly, cloning the x64 config and renaming to arm64 is sufficient — MSBuild's v143 toolset handles ARM64 codegen automatically.

---

**Patch 8 — `libs/libunistring/libunistring.py`: `windres` ARM64 wrapper**

Installs a Python wrapper script that runs `windres` and patches the output COFF machine type from AMD64 to ARM64.

*Why:* MSYS2's `windres` (GNU binutils 2.46) doesn't support `pe-arm64-little`. It can compile `.rc` resource files but stamps the output as AMD64. The wrapper intercepts the output and rewrites the 2-byte machine type field from `0x8664` (AMD64) to `0xAA64` (ARM64) so the linker accepts it.

---

**Patch 9 — `libs/libffi/libffi.py`: ARM64 platform triple and assembler**

Sets the autotools platform triple to `aarch64-w64-mingw32` and adds `-marm64` to the CCAS (C-compatible assembler) flags.

*Why:* Craft's `AutoToolsBuildSystem` hardcodes `x86_64-w64-mingw32` as the platform triple. libffi has architecture-specific assembly (closures, trampolines), so it needs the correct triple to select the ARM64 codepaths. The `-marm64` flag tells `msvcc.sh` (the MSVC compatibility wrapper) to produce ARM64 objects.

---

**Patch 10 — `libs/python/python.py`: PCbuild output directory**

Changes hardcoded `PCbuild/amd64/` paths to `PCbuild/arm64/` when building for ARM64.

*Why:* Python's MSBuild puts compiled binaries in `PCbuild/{arch}/`. The Craft blueprint hardcodes `PCbuild/amd64/` for the `install()` step that copies `python.exe`, `*.dll`, `*.lib`, and `*.pyd` files. On ARM64 the output is in `PCbuild/arm64/`, so the install step can't find anything.

### Additional patches applied at the build-workflow level

These three fixes aren't in the script itself — they're applied by the CI workflow (present on the `claude/arm-windows-build-dh7Rx` and `arm64/v33.0.2` branches) because they're either more invasive or tied to install-time packaging rather than dependency compilation:

**Patch 11 — `libs/libjpeg-turbo/libjpeg-turbo.py`: disable SIMD**

Adds `-DWITH_SIMD=OFF` for ARM64. libjpeg-turbo's SIMD code uses x86 NASM assembly that won't compile on ARM64.

**Patch 12 — `libs/pixman/pixman.py`: disable x86 SIMD**

Adds `-Dmmx=disabled -Dsse2=disabled -Dssse3=disabled -Da64-neon=disabled`. Pixman's `meson.build` unconditionally enables MMX for MSVC, which pulls in `<mmintrin.h>` — an x86-only header that doesn't exist on ARM64.

**Patch 13 — NSIS packager + installer blueprint**

Treats ARM64 as 64-bit for `PROGRAMFILES64`, adds a Start Menu shortcut, Nextcloud icon, version number, and a "Launch after install" checkbox. Not a compilation fix — an installer polish fix.

### Summary

| Category | Patches | Root cause |
|---|---|---|
| Craft doesn't know ARM64 exists | 1 | Architecture enum missing |
| Build tools assume x86/x64 layout | 3, 5 | Git paths, `PATH` search |
| Dependencies hardcode x86/x64 | 4, 6, 7, 8, 9, 10 | Platform detection, assembly, output dirs |
| SIMD / assembly is x86-only | 11, 12 | MMX / SSE / NASM intrinsics |
| Broken URL (not ARM64-related) | 2 | Dead `zlib.net` link |
| Installer polish | 13 | NSIS defaults |

**Zero patches to the Nextcloud client source code itself.** Every fix is in the build system (KDE Craft) or third-party dependency blueprints.

### How to use it

The script takes nine absolute paths — one per file it patches — and patches them in place. Run it once after Craft clones its blueprint repos and before `--install-deps`:

```bash
python .github/scripts/patch-craft-arm64.py \
  <path/to/CraftSetupHelper.py> \
  <path/to/libs/zlib/zlib.py> \
  <path/to/dev-utils/_windows/git/git.py> \
  <path/to/dev-utils/perl/perl.py> \
  <path/to/libs/openssl/openssl.py> \
  <path/to/libs/liblzma/liblzma.py> \
  <path/to/libs/libunistring/libunistring.py> \
  <path/to/libs/libffi/libffi.py> \
  <path/to/libs/python/python.py>
```

Then run Craft as usual against a `windows-msvc2022_arm64-cl` target and `craft nextcloud-client` will build end-to-end.

### You can use this on any future release

- **It's not tied to any specific Nextcloud version.** The patches target general ARM64 bugs in upstream dependency blueprints (OpenSSL, Python, Perl, zlib, libffi, libunistring, xz, Git for Windows). They apply cleanly to any future Nextcloud Desktop release because **Nextcloud's own source code is not touched at all** — this is literally a build-system config layer.
- **Total diff is tiny** — roughly 100 lines of real fix code spread across 10 patches. Most are one- or two-line ternary changes. The largest (liblzma) is ~30 lines because it has to edit some XML.
- **The better long-term home for these patches is [`KDE/craft-blueprints-kde`](https://invent.kde.org/packaging/craft-blueprints-kde)** upstream of Nextcloud's fork. Landing them there means every downstream consumer — not just Nextcloud — gets Windows ARM64 for free. This script is effectively a pre-written list of PRs waiting to be filed against that repo.
- **~12 hours of a non-developer coaxing Claude** got to the current state. A developer who actually understands C++ build systems could land these properly — patch-by-patch, upstream, with tests — in a fraction of that time.

**This repo will be archived the moment upstream ships native Windows ARM64.** That is the entire goal.

## Issues

- **ARM64-specific bugs** (crashes on ARM, shell integration broken on ARM, installer won't run) → [open an issue](../../issues). No promises on response time.
- **Everything else** (sync logic, UI bugs, features, auth, server compatibility) → [report upstream at `nextcloud/desktop`](https://github.com/nextcloud/desktop/issues). Those bugs live in the upstream code, not in these ARM64 patches.

When filing an ARM64 issue please include: Windows version and build number, device (Surface Pro X / Snapdragon X Elite laptop / VM), Nextcloud server version, and whether Task Manager shows the process as ARM64 or x64.

## Relationship to upstream

Soft fork of [`nextcloud/desktop`](https://github.com/nextcloud/desktop). Tracks upstream closely. Only adds the files in the table above. All credit for the Nextcloud Desktop Client itself belongs to the Nextcloud team and upstream contributors.

For everything else — full documentation, build instructions, contributor guide, code of conduct, community channels, professional support, test server setup — please see the [upstream repository](https://github.com/nextcloud/desktop) and the [official Nextcloud website](https://nextcloud.com).

## License

GPL-2.0-or-later, same as upstream. See [`COPYING`](COPYING).
