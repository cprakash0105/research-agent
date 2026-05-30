import pytest
from app.token_tracker import TokenTracker


class TestTokenTracker:
    """Test per-session token budget tracking."""

    def test_initial_state(self):
        tracker = TokenTracker(budget=100_000)
        assert tracker.total_tokens == 0
        assert tracker.budget_remaining == 100_000
        assert tracker.budget_used_pct == 0.0
        assert tracker.is_over_budget() is False

    def test_record_usage(self):
        tracker = TokenTracker(budget=100_000)
        tracker.record_usage("planner", input_tokens=200, output_tokens=100)
        assert tracker.total_input_tokens == 200
        assert tracker.total_output_tokens == 100
        assert tracker.total_tokens == 300

    def test_multiple_calls_accumulate(self):
        tracker = TokenTracker(budget=100_000)
        tracker.record_usage("planner", 200, 100)
        tracker.record_usage("analyst", 500, 300)
        tracker.record_usage("writer", 1000, 800)
        assert tracker.total_input_tokens == 1700
        assert tracker.total_output_tokens == 1200
        assert tracker.total_tokens == 2900

    def test_budget_exceeded(self):
        tracker = TokenTracker(budget=500)
        tracker.record_usage("planner", 300, 250)
        assert tracker.is_over_budget() is True

    def test_budget_not_exceeded(self):
        tracker = TokenTracker(budget=10_000)
        tracker.record_usage("planner", 200, 100)
        assert tracker.is_over_budget() is False

    def test_budget_used_percentage(self):
        tracker = TokenTracker(budget=1000)
        tracker.record_usage("planner", 400, 100)
        assert tracker.budget_used_pct == 50.0

    def test_budget_remaining(self):
        tracker = TokenTracker(budget=1000)
        tracker.record_usage("planner", 300, 200)
        assert tracker.budget_remaining == 500

    def test_get_summary(self):
        tracker = TokenTracker(budget=10_000)
        tracker.record_usage("planner", 200, 100)
        tracker.record_usage("writer", 500, 300)
        summary = tracker.get_summary()
        assert summary["total_input_tokens"] == 700
        assert summary["total_output_tokens"] == 400
        assert summary["total_tokens"] == 1100
        assert summary["budget"] == 10_000
        assert summary["num_calls"] == 2
        assert len(summary["calls"]) == 2
        assert summary["calls"][0]["node"] == "planner"
        assert summary["calls"][1]["node"] == "writer"
