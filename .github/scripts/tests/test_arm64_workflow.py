# SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: GPL-2.0-or-later
from pathlib import Path
import re
import unittest


WORKFLOW = Path(__file__).resolve().parents[2] / "workflows" / "arm64-release.yml"
CACHE_SHA = "55cc8345863c7cc4c66a329aec7e433d2d1c52a9"


class Arm64WorkflowTests(unittest.TestCase):
    def test_pip_legacy_certs_is_inherited_by_all_craft_subprocesses(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        job = re.search(r"(?ms)^  build-release:\n(?P<body>.*?)(?=^  \S|\Z)", text)
        self.assertIsNotNone(job)
        env = re.search(r"(?ms)^    env:\n(?P<body>(?:^      .*\n)+)", job.group("body"))
        self.assertIsNotNone(env)
        self.assertRegex(
            env.group("body"),
            r"(?m)^      PIP_USE_DEPRECATED:\s*legacy-certs\s*$",
        )

    def test_failed_client_tests_are_diagnosed_and_still_fail_the_job(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        step = re.search(r"(?ms)^      - name: Compile client and run its tests\n(?P<body>.*?)(?=^      - name: )", text)
        self.assertIsNotNone(step)
        body = step.group("body")
        self.assertIn("--no-tests=error", body)
        self.assertIn("$ctestCode = $LASTEXITCODE", body)
        self.assertIn("LastTestsFailed.log", body)
        self.assertIn("Get-WinEvent", body)
        self.assertIn("craft-test-$name.log", body)
        # The diagnostics must never turn a failing CTest run into a pass.
        self.assertRegex(body, r"(?m)^\s*if \(\$ctestCode -ne 0\) \{ exit \$ctestCode \}\s*$")
        # Tests run in upstream's Windows CI environment (UTC clock, windowsvista
        # style) and the runner's own time zone is restored afterwards.
        self.assertLess(body.index("Set-TimeZone -Id 'UTC'"), body.index("& ctest"))
        self.assertLess(body.index("$env:QT_STYLE_OVERRIDE = 'windowsvista'"), body.index("& ctest"))
        self.assertIn("Set-TimeZone -Id $runnerTimeZone", body)
        self.assertLess(body.index("Set-TimeZone -Id $runnerTimeZone"), body.index("{ exit $ctestCode }"))
        self.assertNotIn("continue-on-error", body)

    def test_dependency_build_is_resumable_across_six_hour_runner_windows(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(f"actions/cache/restore@{CACHE_SHA}", text)
        self.assertGreaterEqual(text.count(f"actions/cache/save@{CACHE_SHA}"), 5)
        self.assertIn("arm64-deps-${{ env.ARM64_CACHE_FINGERPRINT }}-phase-", text)
        self.assertIn(".arm64-dependency-checkpoints", text)
        for package in (
            "dev-utils/cmake",
            "libs/qt6/qtbase",
            "libs/qt6/qtdeclarative",
            "libs/qt6/qtwebsockets",
            "libs/qt/qtsvg",
            "libs/qt6/qt5compat",
            "libs/libp11",
            "libs/kdsingleapplication",
            "qt-libs/qtkeychain",
            "kde/frameworks/tier1/karchive",
            "libs/openssl",
        ):
            self.assertIn(package, text)

    def test_zlib_is_bootstrapped_before_virtual_base_resolves_python(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        step = re.search(
            r"(?ms)^      - name: Build dependency checkpoint 01 - foundation\n(?P<body>.*?)(?=^      - name: )",
            text,
        )
        self.assertIsNotNone(step)
        body = step.group("body")
        bootstrap = body.index("virtual/base.ignored=True")
        tools = re.search(r"foreach \(\$package in @\((?P<list>[^)]*)\)\) \{\s*\n\s*Write-Host \"Bootstrapping", body)
        self.assertIsNotNone(tools)
        packages = re.findall(r"'([^']+)'", tools.group("list"))
        self.assertEqual(packages[-1], "libs/zlib")
        for tool in ("dev-utils/cmake", "dev-utils/ninja", "dev-utils/patch"):
            self.assertIn(tool, packages)
        verify = body.index("Join-Path $root 'lib/zlib.lib'")
        resume = body.index("foreach ($package in @('libs/zlib', 'libs/openssl'))")
        self.assertLess(bootstrap, verify)
        self.assertLess(verify, resume)
        self.assertIn("@bootstrap $package", body)
        # The normal resolution must not carry the virtual/base override.
        self.assertNotIn("bootstrap", body[resume:])

    def test_blueprint_fixes_reach_restored_workspaces(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        reuse = text.index('Write-Host "Reusing restored ARM64 Craft dependency workspace."')
        patch = text.index("patch-kde-blueprints-arm64.py")
        self.assertLess(reuse, patch)
        self.assertIn('"$nextcloud/libs/libp11/libp11.py"', text)
        self.assertIn('"$kde/libs/qt6/qttools/qttools.py"', text)
        self.assertIn('"$nextcloud/nextcloud-client/nextcloud-client.py"', text)

    def test_nsis_is_installed_before_the_installer_is_packaged(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        nsis = text.index("-c 'dev-utils/nsis'")
        package = text.index("--package nextcloud-client")
        self.assertLess(text.index("- name: Validate native binaries and package installer"), nsis)
        self.assertLess(nsis, package)
        self.assertIn('throw "NSIS installation failed: $LASTEXITCODE"', text)

    def test_cross_commit_checkpoint_fallback_is_limited_to_stable_branches(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        restore = re.search(r"(?ms)restore-keys: \|\n(?P<keys>(?:^            .*\n)+)", text)
        self.assertIsNotNone(restore)
        keys = restore.group("keys").splitlines()
        self.assertEqual(keys[0].strip(), "arm64-deps-${{ env.ARM64_CACHE_FINGERPRINT }}-phase-")
        self.assertIn("startsWith(github.ref, 'refs/heads/arm64/stable-') && 'arm64-deps-'", keys[1])
        self.assertIn("format('arm64-deps-{0}-phase-', env.ARM64_CACHE_FINGERPRINT)", keys[1])


if __name__ == "__main__":
    unittest.main()
