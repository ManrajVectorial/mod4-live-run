"""Fail if any installed dependency carries a copyleft licence (AGENTS.md rule 7).

Checks every Python package in the current environment (via pip-licenses) and every
package under frontend/node_modules. Refused: GPL, AGPL, LGPL, SSPL and EUPL, in any
version. A package whose licence can't be read also fails, so nothing slips through
unchecked.

    python ci/check_licences.py
    python ci/check_licences.py --node-modules frontend/node_modules
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

COPYLEFT = re.compile(
    r"\b(A?GPL|LGPL|SSPL|EUPL)\b|GNU (Affero |Lesser |Library )?General Public",
    re.IGNORECASE,
)
UNKNOWN = {"", "unknown", "none", "unlicensed"}
OWN_PACKAGES = {"policy-assistant-api", "policy-assistant-web"}


def classify(licence: str) -> str:
    """'copyleft', 'unknown' or 'ok' for one licence string."""
    text = licence.strip()
    if text.lower() in UNKNOWN:
        return "unknown"
    if COPYLEFT.search(text):
        return "copyleft"
    return "ok"


def python_packages() -> list[tuple[str, str]]:
    result = subprocess.run(
        [sys.executable, "-m", "piplicenses", "--format=json", "--from=mixed"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pip-licenses failed: {result.stderr.strip()}")
    return [(p["Name"], p["License"]) for p in json.loads(result.stdout)]


def node_packages(node_modules: Path) -> list[tuple[str, str]]:
    found = []
    for manifest in node_modules.rglob("package.json"):
        # Only a package's own manifest: node_modules/<pkg>/package.json or
        # node_modules/@scope/<pkg>/package.json, at any nesting depth.
        parent = manifest.parent
        owner = (
            parent.parent.parent
            if parent.parent.name.startswith("@")
            else parent.parent
        )
        if owner.name != "node_modules" and parent.parent.name != "node_modules":
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"cannot read {manifest}: {type(exc).__name__}") from exc
        if "name" not in data or "version" not in data:
            continue  # a nested config file, not a package manifest
        licence = data.get("license")
        if isinstance(licence, dict):
            licence = licence.get("type", "")
        if licence is None and isinstance(data.get("licenses"), list):
            licence = " OR ".join(str(x.get("type", "")) for x in data["licenses"])
        found.append((f"{data['name']}@{data['version']}", str(licence or "")))
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refuse copyleft dependencies.")
    parser.add_argument(
        "--node-modules", type=Path, default=Path("frontend/node_modules")
    )
    parser.add_argument("--skip-python", action="store_true")
    args = parser.parse_args(argv)

    try:
        packages = [] if args.skip_python else python_packages()
        if args.node_modules.is_dir():
            packages += node_packages(args.node_modules)
        else:
            print(
                f"Note: {args.node_modules} not found; frontend packages not checked."
            )
    except RuntimeError as exc:
        print(f"Licence check could not run: {exc}", file=sys.stderr)
        return 2

    problems = []
    for name, licence in sorted(set(packages)):
        if name.split("@")[0] in OWN_PACKAGES:
            continue
        verdict = classify(licence)
        if verdict != "ok":
            problems.append(f"  {verdict:9} {name}: {licence or '(none declared)'}")

    print(f"Checked {len(packages)} packages.")
    if problems:
        print("LICENCE CHECK FAILED:")
        print("\n".join(problems))
        return 1
    print("Licence check passed: no copyleft or unknown licences.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
