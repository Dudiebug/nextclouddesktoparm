<!--
  - SPDX-FileCopyrightText: 2026 Dudiebug
  - SPDX-FileCopyrightText: 2017 Nextcloud GmbH and Nextcloud contributors
  - SPDX-FileCopyrightText: 2011 Nextcloud GmbH and Nextcloud contributors
  - SPDX-License-Identifier: GPL-2.0-or-later
-->
# Nextcloud Desktop Client for Windows ARM64

**An unofficial native ARM64 build of the Nextcloud desktop sync client for Windows on ARM.** Intended for Windows ARM64 PCs such as Snapdragon X Elite and X Plus laptops, Surface Laptop 7, Surface Pro 11, and Windows Dev Kit 2023.

[Download published ARM64 installers](https://github.com/Dudiebug/nextclouddesktoparm/releases) · [Latest published release](https://github.com/Dudiebug/nextclouddesktoparm/releases/latest) · [Build status](https://github.com/Dudiebug/nextclouddesktoparm/actions) · [Upstream Nextcloud Desktop](https://github.com/nextcloud/desktop)

## Download and release status

**The release page is the source of truth for available installers.** A source branch or a running workflow does not mean an installer is ready.

The update to **Nextcloud Desktop 34.0.4** is being built on [`arm64/v34.0.4`](https://github.com/Dudiebug/nextclouddesktoparm/tree/arm64/v34.0.4). Do not treat it as a published or tested Windows ARM64 release until its installer appears in Releases. The previous published build is `v33.0.2-arm64`.

## What is this project?

This project packages the [Nextcloud Desktop Client](https://github.com/nextcloud/desktop) for **Windows ARM64 / AArch64**. It provides a native Windows-on-ARM alternative to running an x64 client under emulation. It is not a Linux ARM build, an Android client, or a Nextcloud server package.

The ARM64 work is a compatibility layer for KDE Craft, dependency build recipes, and installer packaging. The 34.0.4 source branch starts from upstream release commit `ece94a644d472542f841124067f75cf284899c67`; the port does not modify Nextcloud's sync-engine source.

No comparative battery-life or performance benchmark is claimed. Hardware listed here is the intended platform, not a certification that every device and feature has been tested.

## Install

1. Open [Releases](https://github.com/Dudiebug/nextclouddesktoparm/releases) and choose a published Windows ARM64 installer. Read that release's known limitations first.
2. Confirm Windows reports an **ARM-based processor**, and back up important files before changing sync clients.
3. Exit any running Nextcloud client before installing. Use the downloaded ARM64 `.exe`, then sign in with your Nextcloud server URL.

Installers are unofficial and may be unsigned. A Windows trust warning is not proof that a file is safe: check that it came from this repository and compare the published SHA-256 checksum when one is provided. Do not delete your sync folder or sync database to perform an upgrade.

For an official supported distribution, see [Nextcloud's client downloads](https://nextcloud.com/install/#install-clients).

## Build and release development

The 34.0.4 build targets Windows 11 ARM64 using MSVC 2022, Qt 6.10.2, and GitHub's `windows-11-arm` runner. Build tooling for this update lives on the [release branch](https://github.com/Dudiebug/nextclouddesktoparm/tree/arm64/v34.0.4), rather than the older source snapshot on `master`.

The build reads the Craft URL and revision from the selected upstream source's `craftmaster.ini`. ARM compatibility fixes cover compiler environment selection, Git paths, Perl, OpenSSL, liblzma, libunistring, libffi, Python, libjpeg-turbo, pixman, and NSIS packaging. The old zlib download-URL workaround is omitted for 34.0.4 because its pinned Craft revision already contains that fix.

Build scripts are under [`.github/scripts`](https://github.com/Dudiebug/nextclouddesktoparm/tree/arm64/v34.0.4/.github/scripts). Their regression tests run with:

```text
python -m unittest discover -s .github/scripts/tests -v
```

Passing script tests is not the same as passing a full Windows build or hardware smoke test. Release notes should state exactly what was tested.

## Project status and contributions

This is a personal, community project, not a maintained or officially endorsed Nextcloud GmbH product. The original port was developed with Claude Code under my direction, and subsequent build work has also been AI-assisted. There is no support or update-cadence guarantee.

The long-term goal is upstream Windows ARM64 support and fewer downstream patches. Changes that already exist upstream should be removed from this compatibility layer after verification. An official native Windows ARM64 release would make this project unnecessary.

For ARM64-specific installation or build failures, [open an issue here](https://github.com/Dudiebug/nextclouddesktoparm/issues) with the release tag, Windows build, device, relevant logs, and whether the client process is ARM64. Redact server addresses, usernames, tokens, and file names from logs before posting. General client issues belong in [nextcloud/desktop](https://github.com/nextcloud/desktop/issues).

## License

GPL-2.0-or-later, matching the upstream Nextcloud Desktop Client. See [COPYING](COPYING). All upstream authorship and license notices remain applicable.
