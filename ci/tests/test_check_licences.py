import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from check_licences import classify, node_packages


@pytest.mark.parametrize(
    "licence",
    [
        "GPL-3.0",
        "GPL-2.0-or-later",
        "AGPL-3.0-only",
        "LGPL-2.1",
        "GNU Lesser General Public License v3 (LGPLv3)",
        "GNU General Public License v2 (GPLv2)",
        "SSPL-1.0",
        "EUPL-1.2",
        "MIT OR GPL-3.0",
    ],
)
def test_copyleft_is_refused(licence):
    assert classify(licence) == "copyleft"


@pytest.mark.parametrize(
    "licence",
    ["MIT", "BSD-3-Clause", "Apache-2.0", "ISC", "MPL-2.0", "PostgreSQL", "0BSD"],
)
def test_permissive_is_allowed(licence):
    assert classify(licence) == "ok"


@pytest.mark.parametrize("licence", ["", "UNKNOWN", "UNLICENSED"])
def test_unreadable_licence_fails(licence):
    assert classify(licence) == "unknown"


def test_reads_plain_and_scoped_node_packages(tmp_path: Path):
    def package(path: str, data: dict) -> None:
        target = tmp_path / "node_modules" / path / "package.json"
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps(data), encoding="utf-8")

    package("left-pad", {"name": "left-pad", "version": "1.0.0", "license": "MIT"})
    package(
        "@scope/thing",
        {"name": "@scope/thing", "version": "2.0.0", "license": "GPL-3.0"},
    )
    package("left-pad/dist", {"type": "module"})  # nested config, not a package
    found = dict(node_packages(tmp_path / "node_modules"))
    assert found == {"left-pad@1.0.0": "MIT", "@scope/thing@2.0.0": "GPL-3.0"}
