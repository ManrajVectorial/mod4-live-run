"""The rollback helper picks the deployment that was live before the current one."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from railway_rollback import pick_previous


def d(id_, status, created):
    return {
        "id": id_,
        "status": status,
        "createdAt": created,
        "meta": {"commitHash": id_ * 7},
    }


def test_picks_the_last_good_deployment_before_the_live_one():
    deployments = [
        d("c", "SUCCESS", "2026-10-25T10:00:00Z"),  # the release, live now
        d("b", "REMOVED", "2026-10-24T10:00:00Z"),  # was live before it
        d("a", "REMOVED", "2026-10-23T10:00:00Z"),
    ]
    assert pick_previous(deployments)["id"] == "b"


def test_failed_deployments_are_never_picked():
    deployments = [
        d("d", "SUCCESS", "2026-10-25T10:00:00Z"),
        d("c", "FAILED", "2026-10-24T12:00:00Z"),
        d("b", "CRASHED", "2026-10-24T11:00:00Z"),
        d("a", "REMOVED", "2026-10-24T10:00:00Z"),
    ]
    assert pick_previous(deployments)["id"] == "a"


def test_order_comes_from_the_dates_not_the_list():
    deployments = [
        d("a", "REMOVED", "2026-10-23T10:00:00Z"),
        d("c", "SUCCESS", "2026-10-25T10:00:00Z"),
        d("b", "REMOVED", "2026-10-24T10:00:00Z"),
    ]
    assert pick_previous(deployments)["id"] == "b"


def test_nothing_to_go_back_to_on_the_first_release():
    # The first release: before it, only failed builds of the empty main.
    deployments = [
        d("r", "SUCCESS", "2026-10-25T10:00:00Z"),
        d("x", "FAILED", "2026-10-23T03:03:25Z"),
    ]
    assert pick_previous(deployments) is None


def test_no_live_deployment_means_nothing_to_roll_back():
    deployments = [d("x", "FAILED", "2026-10-23T03:03:25Z")]
    assert pick_previous(deployments) is None
