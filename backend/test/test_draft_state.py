import pytest
from unittest.mock import patch
from fantasyVCT.draft_state import DraftState


@pytest.fixture
def draft():
    return DraftState()


def start_no_shuffle(draft, users, num_rounds=2):
    """Start draft with shuffle disabled for deterministic ordering."""
    draft.set_num_rounds(num_rounds)
    with patch("fantasyVCT.draft_state.random.shuffle"):
        return draft.start_draft(list(users))


# --- Initial state ---

def test_initial_state(draft):
    assert not draft.is_draft_started()
    assert not draft.is_draft_complete()
    assert draft.current_drafter is None


def test_can_draft_before_start_returns_false(draft):
    assert not draft.can_draft("A")


# --- start_draft ---

def test_start_draft_marks_started(draft):
    start_no_shuffle(draft, ["A", "B"])
    assert draft.is_draft_started()
    assert not draft.is_draft_complete()


def test_start_draft_returns_first_drafter(draft):
    # No-op shuffle; users=["A","B"]
    # i=0: reverse→["B","A"]; queue: B,A
    # i=1: reverse→["A","B"]; queue: B,A,A,B
    # current = queue.get() = B
    first = start_no_shuffle(draft, ["A", "B"])
    assert first == "B"
    assert draft.current_drafter == "B"


# --- Snake rotation ---

def test_snake_rotation_two_users_two_rounds(draft):
    """With users [A,B] and 2 rounds (no shuffle), order must be B,A,A,B."""
    start_no_shuffle(draft, ["A", "B"], num_rounds=2)

    order = [draft.current_drafter]
    nxt = draft.next()
    while nxt is not None:
        order.append(nxt)
        nxt = draft.next()

    assert order == ["B", "A", "A", "B"]


def test_draft_complete_after_all_picks(draft):
    start_no_shuffle(draft, ["A", "B"], num_rounds=2)
    while draft.next() is not None:
        pass
    assert draft.is_draft_complete()


# --- can_draft ---

def test_can_draft_current_user(draft):
    start_no_shuffle(draft, ["A", "B"])
    assert draft.can_draft(draft.current_drafter)


def test_can_draft_wrong_user(draft):
    start_no_shuffle(draft, ["A", "B"])
    other = "A" if draft.current_drafter == "B" else "B"
    assert not draft.can_draft(other)


def test_can_draft_true_when_complete(draft):
    """Once draft is complete, any user passes can_draft."""
    draft.skip_draft()
    assert draft.can_draft("anyone")


def test_can_draft_string_int_coercion(draft):
    """can_draft() uses str() comparison; int IDs must match."""
    start_no_shuffle(draft, [123, 456])
    current = draft.current_drafter
    assert draft.can_draft(str(current))
    assert draft.can_draft(current)


# --- next ---

def test_next_advances_current_drafter(draft):
    start_no_shuffle(draft, ["A", "B"])
    first = draft.current_drafter
    second = draft.next()
    assert draft.current_drafter == second
    assert second != first


def test_next_returns_none_on_empty_queue(draft):
    start_no_shuffle(draft, ["A"], num_rounds=1)
    # 1 user, 1 round: queue=[A], current=A after start → queue empty
    result = draft.next()
    assert result is None
    assert draft.is_draft_complete()


# --- skip_draft ---

def test_skip_draft(draft):
    draft.skip_draft()
    assert draft.is_draft_started()
    assert draft.is_draft_complete()


# --- set_num_rounds ---

def test_set_num_rounds(draft):
    draft.set_num_rounds(3)
    assert draft.num_rounds == 3


def test_num_rounds_affects_total_picks(draft):
    """3 users × 3 rounds = 9 total picks."""
    start_no_shuffle(draft, ["A", "B", "C"], num_rounds=3)
    picks = 1  # current_drafter counts as first pick
    while draft.next() is not None:
        picks += 1
    assert picks == 9
