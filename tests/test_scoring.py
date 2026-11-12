"""Deterministic fit-score math (shared/llm/scoring.py)."""

from shared.llm.prompts.score_listing import RUBRIC_MAX
from shared.llm.scoring import DEGREE_CAP, FUNDING_CAP, compute_fit_score

PERFECT = dict(RUBRIC_MAX)


def test_rubric_maxima_sum_to_100():
    assert sum(RUBRIC_MAX.values()) == 100


def test_perfect_rubric_scores_100():
    total, _, flags = compute_fit_score(PERFECT, {}, "")
    assert total == 100
    assert flags == []


def test_dimension_clamped_to_its_max():
    _, rubric, _ = compute_fit_score({"topic_overlap": 999}, {}, "")
    assert rubric["topic_overlap"] == RUBRIC_MAX["topic_overlap"]


def test_negative_values_clamped_to_zero():
    total, _, _ = compute_fit_score({"topic_overlap": -50}, {}, "")
    assert total == 0


def test_garbage_and_missing_values_count_as_zero():
    total, rubric, _ = compute_fit_score({"topic_overlap": "lots", "methods_match": None}, {}, "")
    assert total == 0
    assert set(rubric) == set(RUBRIC_MAX)


def test_numeric_strings_are_accepted():
    _, rubric, _ = compute_fit_score({"topic_overlap": "25"}, {}, "")
    assert rubric["topic_overlap"] == 25


def test_unfunded_capped_when_user_needs_funding():
    total, _, flags = compute_fit_score(PERFECT, {"funding_confirmed": False}, "Need a FUNDED position")
    assert total == FUNDING_CAP
    assert len(flags) == 1


def test_unfunded_not_capped_when_funding_not_required():
    total, _, _ = compute_fit_score(PERFECT, {"funding_confirmed": False}, "")
    assert total == 100


def test_unknown_funding_is_not_treated_as_unfunded():
    total, _, _ = compute_fit_score(PERFECT, {"funding_confirmed": None}, "scholarship only")
    assert total == 100


def test_cap_never_raises_a_low_score():
    total, _, _ = compute_fit_score({"topic_overlap": 10}, {"degree_match": False}, "")
    assert total == 10


def test_degree_mismatch_capped():
    total, _, _ = compute_fit_score(PERFECT, {"degree_match": False}, "")
    assert total == DEGREE_CAP


def test_both_caps_lowest_wins():
    total, _, flags = compute_fit_score(
        PERFECT, {"funding_confirmed": False, "degree_match": False}, "funding required"
    )
    assert total == min(FUNDING_CAP, DEGREE_CAP)
    assert len(flags) == 2
