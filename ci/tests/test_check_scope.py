"""Proves ci/check_scope.py in a throwaway git repository. Never touches our real files."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "check_scope.py"
REFUSED = "SCOPE CHECK REFUSED THE BUILD"

GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "scope-test",
    "GIT_AUTHOR_EMAIL": "scope-test@example.invalid",
    "GIT_COMMITTER_NAME": "scope-test",
    "GIT_COMMITTER_EMAIL": "scope-test@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}


def git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=repo, env=GIT_ENV, check=True, capture_output=True
    )


def write(repo: Path, path: str, text: str) -> None:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def check(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), "--base", "main"],
        env=GIT_ENV,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repo whose main branch holds one file in each protected place, plus app code."""
    git(tmp_path, "init", "-q", "-b", "main")
    files = {
        "backend/corpus/policy.md": "policy v1\n",
        "docs/project-brief.md": "brief\n",
        "docs/PRD.md": "prd\n",
        "docs/features.md": "features\n",
        "AGENTS.md": "rules\n",
        "CLAUDE.md": "@AGENTS.md\n",
        ".claude/settings.json": "{}\n",
        "ci/check_scope.py": "# check\n",
        ".github/workflows/ci.yml": "name: CI\n",
        "backend/app/main.py": "print('app')\n",
    }
    for path, text in files.items():
        write(tmp_path, path, text)
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "base")
    git(tmp_path, "checkout", "-q", "-b", "work")
    return tmp_path


def assert_refused(result: subprocess.CompletedProcess, path: str) -> None:
    assert result.returncode == 1, result.stdout + result.stderr
    assert REFUSED in result.stdout
    assert path in result.stdout


def test_clean_branch_passes(repo):
    result = check(repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert REFUSED not in result.stdout


@pytest.mark.parametrize(
    "path",
    [
        "backend/corpus/policy.md",
        "docs/project-brief.md",
        "docs/PRD.md",
        "docs/features.md",
        "AGENTS.md",
        "CLAUDE.md",
        ".claude/settings.json",
        "ci/check_scope.py",
        ".github/workflows/ci.yml",
    ],
)
def test_committed_change_to_protected_file_is_refused(repo, path):
    write(repo, path, "tampered\n")
    git(repo, "commit", "-q", "-am", "change")
    assert_refused(check(repo), path)


def test_uncommitted_change_is_refused(repo):
    write(repo, "backend/corpus/policy.md", "policy v2, not committed\n")
    assert_refused(check(repo), "backend/corpus/policy.md")


def test_staged_change_is_refused(repo):
    write(repo, "docs/PRD.md", "staged edit\n")
    git(repo, "add", "docs/PRD.md")
    assert_refused(check(repo), "docs/PRD.md")


def test_deleted_protected_file_is_refused(repo):
    git(repo, "rm", "-q", "AGENTS.md")
    git(repo, "commit", "-q", "-m", "delete")
    assert_refused(check(repo), "AGENTS.md")


def test_renamed_protected_file_is_refused(repo):
    git(repo, "mv", "backend/corpus/policy.md", "backend/corpus/renamed.md")
    git(repo, "commit", "-q", "-m", "rename")
    assert_refused(check(repo), "backend/corpus/policy.md")


def test_new_files_are_allowed_even_in_protected_dirs(repo):
    write(repo, "backend/corpus/new-policy.md", "new\n")
    write(repo, "ci/new_check.py", "# new\n")
    write(repo, ".github/workflows/extra.yml", "name: extra\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "add files")
    write(repo, "ci/uncommitted_new.py", "# untracked\n")
    result = check(repo)
    assert result.returncode == 0, result.stdout + result.stderr


def test_changes_outside_protected_paths_are_allowed(repo):
    write(repo, "backend/app/main.py", "print('changed')\n")
    write(repo, "README.md", "new readme\n")
    result = check(repo)
    assert result.returncode == 0, result.stdout + result.stderr


def test_missing_tag_falls_back_to_base_branch(repo):
    write(repo, "AGENTS.md", "changed, and no plan-approved tag exists\n")
    git(repo, "commit", "-q", "-am", "change")
    result = check(repo)
    assert "tag plan-approved not found; falling back to main" in result.stdout
    assert_refused(result, "AGENTS.md")


def test_tag_is_the_baseline_when_present(repo):
    # Approved change made before the plan was approved, then the tag is set.
    write(repo, "AGENTS.md", "rules v2, approved\n")
    git(repo, "commit", "-q", "-am", "approved change")
    git(repo, "tag", "plan-approved")

    result = check(repo)  # differs from main, but not from the tag
    assert result.returncode == 0, result.stdout + result.stderr
    assert "refs/tags/plan-approved" in result.stdout

    write(repo, "AGENTS.md", "rules v3, after approval\n")
    assert_refused(check(repo), "AGENTS.md")


def test_file_absent_at_tag_is_new_and_allowed(repo):
    git(repo, "tag", "plan-approved")
    write(repo, "ci/check_licences.py", "# added after the tag\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "add")
    write(repo, "ci/check_licences.py", "# edited, still absent at the tag\n")
    result = check(repo)
    assert result.returncode == 0, result.stdout + result.stderr


def test_protected_file_at_tag_refused_even_if_main_moves(repo):
    git(repo, "tag", "plan-approved")
    write(repo, "docs/PRD.md", "prd changed after approval\n")
    git(repo, "commit", "-q", "-am", "change")
    git(repo, "branch", "-f", "main", "HEAD")  # main catches up; the tag still governs
    assert_refused(check(repo), "docs/PRD.md")


def test_unknown_base_cannot_run(repo):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), "--base", "no-such-branch"],
        env=GIT_ENV,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert REFUSED not in result.stdout
