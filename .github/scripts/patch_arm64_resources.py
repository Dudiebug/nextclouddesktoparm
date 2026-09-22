#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Replace the legacy libunistring windres shim with explicit SDK compilation."""
import ast
from pathlib import Path
import shutil
import sys

PACKAGE = '''class Package(AutoToolsPackageBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.shell.useMSVCCompatEnv = True
        from CraftCompiler import CraftCompiler
        from CraftCore import CraftCore
        if CraftCore.compiler.isWindows and CraftCore.compiler.architecture == CraftCompiler.Architecture.arm64:
            import sys
            python = self.shell.toNativePath(sys.executable)
            wrapper = self.shell.toNativePath(self.blueprintDir() / "arm64_windres.py")
            compiler = f'"{python}" "{wrapper}"'
            # Configure libtool consistently, and propagate to recursive make.
            for settings in (self.subinfo.options.configure, self.subinfo.options.make):
                settings.args += [f"RC={compiler}", f"WINDRES={compiler}"]
'''


def patch(source: str) -> str:
    tree = ast.parse(source)
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Package"]
    if len(classes) != 1 or [ast.unparse(base) for base in classes[0].bases] != ["AutoToolsPackageBase"]:
        raise ValueError("libunistring Package structure changed; review the patch")
    node = classes[0]
    lines = source.splitlines(keepends=True)
    result = "".join(lines[:node.lineno - 1]) + PACKAGE + "".join(lines[node.end_lineno:])
    ast.parse(result)
    return result


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: patch_arm64_resources.py <craft-clone>")
    directory = Path(sys.argv[1]) / "blueprints/libs/libunistring"
    blueprint = directory / "libunistring.py"
    result = patch(blueprint.read_text(encoding="utf-8"))
    shutil.copyfile(Path(__file__).with_name("arm64_windres.py"), directory / "arm64_windres.py")
    blueprint.write_text(result, encoding="utf-8", newline="\n")
    print("Patched libunistring: explicit RC/WINDRES using rc.exe and ARM64 cvtres.exe")


if __name__ == "__main__":
    main()
