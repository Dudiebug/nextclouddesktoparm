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

**Please take these patches upstream.** They're small, cleanly scoped, and the entire reason this repo is public. Everything added to the upstream tree:

| File | Change |
|---|---|
| `craftmaster.ini` | New `[windows-msvc2022_arm64-cl]` KDE Craft target |
| `admin/win/msi/CMakeLists.txt` | Detect ARM64 via `CMAKE_SYSTEM_PROCESSOR` — the existing pointer-size check was broken (x64 and ARM64 are both 8 bytes) |
| `admin/win/msi/Platform.wxi` | New `arm64` WiX platform branch using `ProgramFiles64Folder` |
| `src/libsync/vfs/cfapi/shellext/CMakeLists.txt` | ARM64 Windows SDK tools path resolution |
| `.github/workflows/windows-arm64-release.yml` | New workflow on `windows-11-arm` runners; builds via Craft and publishes a GitHub Release on `v*-arm64*` tag push |

The remaining work — which needs someone who can actually code — is in [`nextcloud/craft-blueprints-kde`](https://github.com/nextcloud/craft-blueprints-kde) and [`nextcloud/desktop-client-blueprints`](https://github.com/nextcloud/desktop-client-blueprints): making sure every transitive build dependency has an ARM64 build rule. I have no way to evaluate the size of that effort. A developer with access to a Windows on ARM device and the existing Craft toolchain could probably find out in an afternoon.

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
