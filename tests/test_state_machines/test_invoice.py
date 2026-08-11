import pytest

from app.state_machines.invoice import validate_transition, VALID_TRANSITIONS
from app.core.exceptions import InvalidStateTransitionError


class TestInvoiceStateMachine:
    def test_draft_can_issue(self):
        validate_transition("draft", "issued")  # Should not raise

    def test_draft_can_cancel(self):
        validate_transition("draft", "cancelled")

    def test_draft_cannot_jump_to_paid(self):
        with pytest.raises(InvalidStateTransitionError):
            validate_transition("draft", "fully_paid")

    def test_issued_can_request_upfront(self):
        validate_transition("issued", "upfront_requested")

    def test_upfront_paid_can_begin_transit(self):
        validate_transition("upfront_paid", "in_transit")

    def test_pod_captured_can_verify(self):
        validate_transition("pod_captured", "pod_verified")

    def test_pod_verified_can_release_balance(self):
        validate_transition("pod_verified", "balance_released")

    def test_balance_released_can_mark_paid(self):
        validate_transition("balance_released", "fully_paid")

    def test_fully_paid_no_transitions(self):
        assert VALID_TRANSITIONS["fully_paid"] == []

    def test_cancelled_no_transitions(self):
        assert VALID_TRANSITIONS["cancelled"] == []
