# SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: GPL-2.0-or-later
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from arm64_lzma import (  # noqa: E402
    liblzma_build_system,
    liblzma_import_library,
    patch_liblzma_blueprint,
    patch_python_lzma_link,
)

MSBUILD_LIBLZMA = (
    "class PackageMSBuild(MSBuildPackageBase):\n"
    "    def __init__(self, **kwargs):\n"
    "        super().__init__(**kwargs)\n"
    '        self.subinfo.options.configure.projectFile = self.sourceDir() / "windows/xz_win.sln"\n'
    '        self.msbuildTargets = ["liblzma_dll"]\n'
    "\n"
    "    def install(self):\n"
    "        return True\n"
)

# Shape of blueprints/libs/liblzma/liblzma.py at Nextcloud Craft 6e684481 (xz 5.8.4).
CMAKE_LIBLZMA = (
    "import info\n"
    "from Package.CMakePackageBase import CMakePackageBase\n"
    "\n\n"
    "class Package(CMakePackageBase):\n"
    "    def __init__(self, **kwargs):\n"
    "        super().__init__(**kwargs)\n"
    "        self.subinfo.options.configure.args += [\n"
    '            f"-DXZ_TOOL_XZ={self.subinfo.options.dynamic.buildTools.asOnOff}",\n'
    "        ]\n"
)

PYTHON = (
    '            addLib("FFI", "ffi")\n'
    '            addLib("LZMA", "liblzma")\n'
    '            addLib("SQLITE", "sqlite3")\n'
)


class Arm64LzmaTests(unittest.TestCase):
    def test_detects_msbuild_recipe(self):
        self.assertEqual(liblzma_build_system(MSBUILD_LIBLZMA), "msbuild")
        self.assertEqual(liblzma_import_library(MSBUILD_LIBLZMA), "liblzma")

    def test_detects_cmake_recipe(self):
        self.assertEqual(liblzma_build_system(CMAKE_LIBLZMA), "cmake")
        self.assertEqual(liblzma_import_library(CMAKE_LIBLZMA), "lzma")

    def test_unknown_recipe_is_an_error(self):
        with self.assertRaises(ValueError):
            liblzma_build_system("class Package(AutoToolsPackageBase):\n")

    def test_cmake_liblzma_makes_python_link_lzma(self):
        patched, changed = patch_python_lzma_link(PYTHON, CMAKE_LIBLZMA)
        self.assertTrue(changed)
        self.assertIn('addLib("LZMA", "lzma")', patched)
        self.assertNotIn('"liblzma"', patched)
        self.assertIn('addLib("SQLITE", "sqlite3")', patched)

    def test_msbuild_liblzma_leaves_python_alone(self):
        patched, changed = patch_python_lzma_link(PYTHON, MSBUILD_LIBLZMA)
        self.assertFalse(changed)
        self.assertEqual(patched, PYTHON)

    def test_already_fixed_python_is_unchanged(self):
        source = PYTHON.replace('"liblzma"', '"lzma"')
        patched, changed = patch_python_lzma_link(source, CMAKE_LIBLZMA)
        self.assertFalse(changed)
        self.assertEqual(patched, source)

    def test_missing_lzma_lib_is_an_error(self):
        with self.assertRaises(ValueError):
            patch_python_lzma_link('addLib("FFI", "ffi")\n', CMAKE_LIBLZMA)


class PatchLiblzmaBlueprintTests(unittest.TestCase):
    def test_cmake_recipe_is_left_unchanged(self):
        self.assertEqual(patch_liblzma_blueprint(CMAKE_LIBLZMA), (CMAKE_LIBLZMA, False))

    def test_msbuild_recipe_gets_arm64_platform_configs(self):
        patched, changed = patch_liblzma_blueprint(MSBUILD_LIBLZMA)
        self.assertTrue(changed)
        self.assertIn("_addArm64PlatformConfigs", patched)
        self.assertIn("    def install(self):\n        return True\n", patched)
        compile(patched.replace("MSBuildPackageBase", "object"), "liblzma.py", "exec")

    def test_msbuild_recipe_patch_is_idempotent(self):
        patched, _ = patch_liblzma_blueprint(MSBUILD_LIBLZMA)
        self.assertEqual(patch_liblzma_blueprint(patched), (patched, False))

    def test_changed_msbuild_recipe_is_an_error(self):
        with self.assertRaises(ValueError):
            patch_liblzma_blueprint("class PackageMSBuild(MSBuildPackageBase):\n    pass\n")


if __name__ == "__main__":
    unittest.main()
