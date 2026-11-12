"""Application status lifecycle (shared/services/state_machine.py)."""

import pytest

from shared.services import state_machine as sm


def test_happy_path_is_legal():
    path = [sm.SAVED, sm.IN_PROGRESS, sm.DOCS_READY, sm.APPLIED, sm.INTERVIEW, sm.OFFER]
    for src, dst in zip(path, path[1:]):
        assert sm.is_legal(src, dst), f"{src} -> {dst}"


def test_cannot_skip_to_applied():
    with pytest.raises(sm.IllegalTransition):
        sm.check_transition(sm.SAVED, sm.APPLIED)


def test_terminal_states_have_no_exit():
    assert sm.allowed_transitions(sm.REJECTED) == []
    assert sm.allowed_transitions(sm.WITHDRAWN) == []


def test_unknown_status_rejected():
    with pytest.raises(sm.IllegalTransition):
        sm.check_transition(sm.SAVED, "ARCHIVED")


def test_same_status_is_a_no_op():
    sm.check_transition(sm.APPLIED, sm.APPLIED)


def test_docs_ready_requires_checklist():
    with pytest.raises(sm.GuardFailed):
        sm.check_transition(sm.IN_PROGRESS, sm.DOCS_READY, docs_checklist=[])


def test_docs_ready_requires_every_item_ready():
    checklist = [{"name": "CV", "ready": True}, {"name": "SOP", "ready": False}]
    with pytest.raises(sm.GuardFailed):
        sm.check_transition(sm.IN_PROGRESS, sm.DOCS_READY, docs_checklist=checklist)


def test_docs_ready_passes_when_all_ready():
    sm.check_transition(sm.IN_PROGRESS, sm.DOCS_READY, docs_checklist=[{"name": "CV", "ready": True}])
