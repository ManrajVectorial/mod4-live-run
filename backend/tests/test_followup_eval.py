"""The follow-up evaluation set and the floor it sets (D9 amendment)."""

from app.followup_eval import FOLLOWUPS_FILE, FollowupCase, choose_floor, load_cases


def test_six_cases_three_to_answer_three_to_refuse():
    cases = load_cases(FOLLOWUPS_FILE)
    assert [c.cid for c in cases] == ["C1", "C2", "C3", "C4", "C5", "C6"]
    assert [c.expect for c in cases] == ["answer"] * 3 + ["refuse"] * 3
    assert cases[0].first == "What is the approval threshold for a travel expense claim?"
    assert cases[1].followup == "And for Singapore?"
    assert cases[3].followup == "Can I expense my partner's flight?"


def case(cid, expect):
    return FollowupCase(cid=cid, expect=expect, first="f", followup="u")


def test_floor_is_the_midpoint_of_the_gap_in_scores_alone():
    scores = {"C1": 0.50, "C2": 0.48, "C3": 0.55, "C4": 0.42, "C5": 0.30, "C6": 0.44}
    cases = [
        case("C1", "answer"),
        case("C2", "answer"),
        case("C3", "answer"),
        case("C4", "refuse"),
        case("C5", "refuse"),
        case("C6", "refuse"),
    ]
    floor = choose_floor(cases, scores)
    assert floor is not None
    assert round(floor, 4) == 0.46  # midpoint of 0.44 (highest refuse) and 0.48 (lowest answer)


def test_no_floor_when_the_scores_overlap():
    scores = {"C1": 0.40, "C4": 0.45}
    assert choose_floor([case("C1", "answer"), case("C4", "refuse")], scores) is None
