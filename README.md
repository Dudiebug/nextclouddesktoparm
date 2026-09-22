<!--
  - SPDX-FileCopyrightText: 2026 Dudiebug
  - SPDX-FileCopyrightText: 2017 Nextcloud GmbH and Nextcloud contributors
  - SPDX-FileCopyrightText: 2011 Nextcloud GmbH and Nextcloud contributors
  - SPDX-License-Identifier: GPL-2.0-or-later
-->
# Nextcloud Desktop Client ARM64 for Windows

**Native Nextcloud client for Windows on ARM / Windows ARM64.** This repository builds the official Nextcloud Desktop Client as a native ARM64 application for Snapdragon X, Surface Pro 11, Surface Laptop 7, and other Windows-on-ARM PCs.

**Current ARM64 release: Nextcloud Desktop 34.0.4**

[Download the latest Windows ARM64 installer](../../releases/latest)

## What this is

This is an unofficial Windows ARM64 build of the upstream [Nextcloud Desktop Client](https://github.com/nextcloud/desktop). The application source is kept aligned with the official Nextcloud release; the ARM64-specific changes are build-system patches for KDE Craft, dependency blueprints, and the Windows installer.

Search terms this project is intended to cover naturally include **Nextcloud ARM64**, **Nextcloud Windows ARM**, **Nextcloud client ARM**, **Nextcloud Desktop ARM64**, and **Windows on ARM Nextcloud client**.

### Why use a native ARM64 build?

The normal Windows x64 client can run through Windows emulation on ARM hardware. A native ARM64 build avoids x64 emulation for the always-running sync client and gives the Explorer integration a native Windows-on-ARM binary.

## Supported hardware

This build is intended for Windows 11 ARM64 systems, including:

- Qualcomm Snapdragon X Elite and Snapdragon X Plus PCs
- Surface Pro 11
- Surface Laptop 7
- Windows Dev Kit 2023
- Other Windows-on-ARM devices capable of running Windows 11 ARM64

## Install

1. Open the [latest release](../../releases/latest).
2. Download the `Nextcloud-*-arm64-setup.exe` installer.
3. Run the installer.
4. Sign in to your Nextcloud server normally.

The installer is not an official Nextcloud GmbH binary and may not carry the same code-signing trust as the official x64 distribution.

## Current release

| Component | Version |
|---|---|
| Nextcloud Desktop | **34.0.4** |
| Platform | **Windows ARM64** |
| Compiler | MSVC 2022 ARM64 |
| Qt | 6.10.2 |
| Packaging | KDE Craft + NSIS |

The `arm64/v34.0.4` branch starts directly from the official upstream `v34.0.4` release commit. ARM-specific files are layered on top; the Nextcloud application source itself is not modified for the port.

## ARM64 build layer

The Windows ARM64 port currently carries build-system compatibility fixes for:

- KDE Craft MSVC ARM64 environment selection
- Git for Windows ARM64 layout detection
- Perl ARM64 configuration and `miniperl` lookup
- OpenSSL `VC-WIN64-ARM`
- liblzma/xz ARM64 MSBuild platform definitions
- libunistring resource compilation
- libffi AArch64 autotools/assembler configuration
- Python `PCbuild/arm64` installation paths
- libjpeg-turbo SIMD selection
- pixman x86 SIMD disabling on Windows ARM64
- NSIS 64-bit Program Files handling and installer metadata

The old zlib URL workaround from the 33.0.2 build is no longer carried because Nextcloud's 34.0.4-pinned Craft revision already contains that fix.

## Building

The release workflow runs on GitHub's native `windows-11-arm` runner with the target:

```text
windows-msvc2022_arm64-cl
```

It reads the Craft URL and pinned Craft revision from the upstream release's own `craftmaster.ini`, applies the ARM64 compatibility layer, builds dependencies, compiles the client, packages the installer, and verifies that the resulting `nextcloud.exe` has the ARM64 PE machine type (`0xAA64`) before publishing.

The reusable patch scripts live under `.github/scripts/`.

## Project status

This is a community/personal build, not an official Nextcloud GmbH release. ARM64-specific issues are appropriate here. General sync, UI, authentication, or server-compatibility bugs should be reported to [nextcloud/desktop](https://github.com/nextcloud/desktop/issues).

The goal is to remove downstream patches whenever equivalent Windows ARM64 support lands in Craft or its blueprints. If upstream eventually ships an official native Windows ARM64 client, this repository should no longer be necessary.

## Upstream

- Nextcloud Desktop source: [nextcloud/desktop](https://github.com/nextcloud/desktop)
- Official client downloads: [nextcloud.com/install](https://nextcloud.com/install/#install-clients)

## License

GPL-2.0-or-later, matching the upstream Nextcloud Desktop Client. See `COPYING`.
