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


def test_cases_run_through_the_api_as_two_turn_conversations():
    from app.followup_eval import run_cases

    sent = []

    def fake_ask(base_url, question, timeout, conversation_id=None):
        sent.append((question, conversation_id))
        if conversation_id is None:
            return {"status": "answered", "conversation_id": "conv", "meta": {"top_score": 0.7}}
        refuse = "partner" in question
        return {
            "status": "refused" if refuse else "answered",
            "conversation_id": conversation_id,
            "meta": {"top_score": 0.3 if refuse else 0.6},
        }

    cases = [
        FollowupCase(cid="C1", expect="answer", first="Threshold?", followup="And £75?"),
        FollowupCase(
            cid="C4", expect="refuse", first="Threshold?", followup="My partner's flight?"
        ),
        FollowupCase(cid="C9", expect="refuse", first="Threshold?", followup="And Singapore?"),
    ]
    rows = run_cases(cases, "http://api.test", 1.0, ask=fake_ask)
    assert sent == [
        ("Threshold?", None),
        ("And £75?", "conv"),
        ("Threshold?", None),
        ("My partner's flight?", "conv"),
        ("Threshold?", None),
        ("And Singapore?", "conv"),
    ]
    assert [(r.cid, r.status, r.outcome) for r in rows] == [
        ("C1", "answered", "PASS"),
        ("C4", "refused", "PASS"),
        ("C9", "answered", "FAIL"),
    ]


def test_no_floor_when_the_scores_overlap():
    scores = {"C1": 0.40, "C4": 0.45}
    assert choose_floor([case("C1", "answer"), case("C4", "refuse")], scores) is None
