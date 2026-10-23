"""Refuse any change to a protected file that already existed at the approved baseline.

The baseline is the `plan-approved` tag: the commit where the plan was approved. If that
tag is missing, the base branch is used instead.

Protected: the corpus, the brief, the PRD, the features list, AGENTS.md, CLAUDE.md,
.claude/, ci/ and .github/. Modifying, deleting, renaming or retyping a protected file that
existed at the baseline is refused, including uncommitted changes in the working tree.
Adding a new file is allowed, even inside a protected directory.

    python ci/check_scope.py                    # baseline: tag plan-approved, else origin/main
    python ci/check_scope.py --base main        # fallback base branch if the tag is missing
    python ci/check_scope.py --tag other-tag    # a different baseline tag
    python ci/check_scope.py --repo PATH        # run against another repository

Exit 0 when allowed, 1 when refused, 2 when the check itself cannot run.
Standard library only.
"""

import argparse
import subprocess
import sys
from pathlib import Path

REFUSED = "SCOPE CHECK REFUSED THE BUILD"

PROTECTED_FILES = (
    "docs/project-brief.md",
    "docs/PRD.md",
    "docs/features.md",
    "AGENTS.md",
    "CLAUDE.md",
)
PROTECTED_DIRS = (
    "backend/corpus/",
    ".claude/",
    "ci/",
    ".github/",
)


def is_protected(path: str) -> bool:
    return path in PROTECTED_FILES or path.startswith(PROTECTED_DIRS)


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def exists_on_base(repo: Path, base: str, path: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{base}:{path}"],
        cwd=repo,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def violations(repo: Path, base: str) -> list[str]:
    """Every protected file on `base` that the working tree changes, as 'STATUS path'."""
    # Working tree (staged and unstaged) against the base commit. Renames are reported as
    # a deletion plus an addition, so a renamed protected file is caught as deleted.
    diff = git(repo, "diff", "--no-renames", "--name-status", base, "--")
    found = []
    for line in diff.splitlines():
        status, _, path = line.partition("\t")
        if status.startswith("A"):
            continue  # new files are allowed
        if is_protected(path) and exists_on_base(repo, base, path):
            found.append(f"{status[0]} {path}")
    return found


def ref_exists(repo: Path, ref: str) -> bool:
    try:
        git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    except RuntimeError:
        return False
    return True


def resolve_baseline(repo: Path, tag: str, base: str) -> str:
    """The approved tag if it exists, otherwise the base branch."""
    tag_ref = f"refs/tags/{tag}"
    if ref_exists(repo, tag_ref):
        return tag_ref
    print(f"Note: tag {tag} not found; falling back to {base}.")
    if ref_exists(repo, base):
        return base
    raise RuntimeError(f"neither tag {tag} nor base {base} exists")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refuse changes to protected files.")
    parser.add_argument(
        "--tag", default="plan-approved", help="baseline tag (default: plan-approved)"
    )
    parser.add_argument(
        "--base",
        default="origin/main",
        help="fallback if the tag is missing (default: origin/main)",
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="repository root")
    args = parser.parse_args(argv)

    try:
        baseline = resolve_baseline(args.repo, args.tag, args.base)
        found = violations(args.repo, baseline)
    except RuntimeError as exc:
        print(f"Scope check could not run: {exc}", file=sys.stderr)
        return 2

    if found:
        print(REFUSED)
        print(f"These protected files have changed since {baseline}:")
        for item in found:
            print(f"  {item}")
        print(
            "Protected files change only with the product owner's approval (AGENTS.md rule 1)."
        )
        return 1

    print(f"Scope check passed: no protected file has changed since {baseline}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
