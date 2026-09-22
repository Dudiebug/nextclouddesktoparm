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

New upstream stable releases are detected automatically. Each version is built from the exact upstream release tag on an `arm64/vX.Y.Z` branch, and a Windows ARM64 release is published only if the full build, client tests, and native ARM64 binary validation succeed. The Releases page remains the source of truth for what is actually available.

## What is this project?

This project packages the [Nextcloud Desktop Client](https://github.com/nextcloud/desktop) for **Windows ARM64 / AArch64**. It provides a native Windows-on-ARM alternative to running an x64 client under emulation. It is not a Linux ARM build, an Android client, or a Nextcloud server package.

The ARM64 work is a compatibility layer for KDE Craft, dependency build recipes, and installer packaging. Release branches start from the corresponding upstream Nextcloud release commit; the port does not intentionally modify Nextcloud's sync-engine source.

No comparative battery-life or performance benchmark is claimed. Hardware listed here is the intended platform, not a certification that every device and feature has been tested.

## Install

1. Open [Releases](https://github.com/Dudiebug/nextclouddesktoparm/releases) and choose a published Windows ARM64 installer. Read that release's known limitations first.
2. Confirm Windows reports an **ARM-based processor**, and back up important files before changing sync clients.
3. Exit any running Nextcloud client before installing. Use the downloaded ARM64 `.exe`, then sign in with your Nextcloud server URL.

Installers are unofficial and may be unsigned. A Windows trust warning is not proof that a file is safe: check that it came from this repository and compare the published SHA-256 checksum when one is provided. Do not delete your sync folder or sync database to perform an upgrade.

For an official supported distribution, see [Nextcloud's client downloads](https://nextcloud.com/install/#install-clients).

## Build and release development

The ARM64 build runs on GitHub's native Windows ARM runner and reads the Craft URL, immutable Craft revision, and Nextcloud/KDE blueprint revisions from the selected upstream source's own `craftmaster.ini`. This avoids hardcoding a specific Nextcloud release series into the ARM64 overlay.

ARM compatibility fixes cover compiler environment selection, Git paths, Perl, OpenSSL, liblzma, libunistring, libffi, Python, libjpeg-turbo, pixman, and NSIS packaging. Build tooling is maintained on the `arm64-tooling` branch and copied onto each clean upstream source branch.

### Automatic upstream tracking

Two scheduled workflows keep the project aligned with Nextcloud:

- **Stable release watcher:** checks upstream every six hours. When Nextcloud publishes a new stable `vX.Y.Z` release, it creates `arm64/vX.Y.Z` from that exact upstream tag, overlays the ARM64 tooling, and dispatches the full Windows ARM64 build. If all validation passes, the build publishes `vX.Y.Z-arm64`.
- **Upstream-main canary:** checks upstream `master` daily. When its commit changes, the same ARM64 build is run on `canary/upstream-main`, but the release-publishing step is disabled. This provides early warning when upstream changes break the ARM64 compatibility layer.

Failed release branches are not rebuilt forever on a timer. After a build fix, the stable watcher can be manually dispatched with `rebuild_existing=true`.

Build scripts are under [`.github/scripts`](https://github.com/Dudiebug/nextclouddesktoparm/tree/arm64-tooling/.github/scripts). Their regression tests run with:

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
