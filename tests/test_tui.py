from unittest.mock import patch

from rakkib.tui import progress_wait


def test_progress_wait_returns_true_when_poll_succeeds():
    with patch("rakkib.tui.Progress"), patch("rakkib.tui.time.sleep"):
        assert progress_wait("Waiting...", 5, lambda: True)


def test_progress_wait_returns_false_after_timeout():
    now = iter([0, 0, 1, 1, 2, 2])

    with patch("rakkib.tui.Progress"), patch("rakkib.tui.time.sleep"), patch(
        "rakkib.tui.time.monotonic", side_effect=lambda: next(now, 2)
    ):
        assert not progress_wait("Waiting...", 2, lambda: False)
