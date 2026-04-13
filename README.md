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

### What the script fixes

1. **`CraftSetupHelper.getMSVCEnv`** — adds `arm64` / `x86_arm64` entries to the MSVC architecture dicts so Craft knows how to set up an ARM64 compile environment
2. **`libs/zlib/zlib.py`** — rewrites the dead `zlib.net` download URL to the equivalent GitHub release asset (unrelated to ARM64, but blocks the whole build)
3. **`dev-utils/_windows/git/git.py::locateGit()`** — handles the Git for Windows ARM64 layout (`Git\clangarm64\bin\git.exe`) so `dev-utils/patch` and `dev-utils/sed` still resolve
4. **`dev-utils/perl/perl.py` (`CRAFT_WIN64`)** — leaves `CRAFT_WIN64` empty for arm64 so Perl 5.40's `win32/Makefile` can self-configure (without this, miniperl.exe crashes with `0xc0000005`)
5. **`dev-utils/perl/perl.py` (`_globEnv`)** — adds the perl source root to `PATH` so the Makefile's bare `miniperl` invocation resolves (modern cmd.exe doesn't search the cwd)
6. **`libs/openssl/openssl.py`** — selects OpenSSL's `VC-WIN64-ARM` Configure target for arm64 (upstream falls back to `VC-WIN32`, producing a broken 32-bit x86 OpenSSL on ARM64)
7. **`libs/liblzma/liblzma.py`** — clones the x64 sections of xz 5.2.3's `xz_win.sln`, `liblzma.vcxproj`, and `liblzma_dll.vcxproj` as arm64 siblings so MSBuild accepts `/p:Platform=arm64`
8. **`libs/libunistring/libunistring.py`** — installs a `windres` wrapper that fixes the COFF machine header bytes from `0x8664` (x86) to `0xaa64` (arm64) on resource object files
9. **`libs/libffi/libffi.py`** — sets the `aarch64-w64-mingw32` platform triple and `-marm64` CCAS flag
10. **`libs/python/python.py`** — swaps `PCbuild/amd64` for `PCbuild/arm64` in `install()` (Python's build system uses arch-suffixed output dirs)

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
