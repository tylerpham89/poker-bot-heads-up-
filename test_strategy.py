"""Independent checks of the simulation's hand scoring and lifecycle."""
from itertools import combinations
import random

import pytest

from evaluator import cards_from_str, omaha_score, score_five, warmup
from game import AgentConfig, Game, make_deal
from strategy import BITS, board_masks, estimate, new_half, score_masks


def test_partial_and_complete_scores_match_exhaustive_reference():
    warmup()
    from evaluator import get_table
    rng = random.Random(2026)
    for _ in range(30):
        cards = rng.sample(range(36), 10)
        hole, board = cards[:5], cards[5:]
        pairs = tuple(BITS[a] | BITS[b] for a, b in combinations(hole, 2))
        for size in (3, 4, 5):
            actual = score_masks(pairs, board_masks(board[:size]), get_table())
            expected = max(score_five(p + b) for p in combinations(hole, 2)
                           for b in combinations(board[:size], 3))
            assert actual == expected
        assert actual == omaha_score(hole, board)


@pytest.mark.parametrize("text, board", [
    ("Ah Kh 6c 7d 8s", "Qh Jh Th 9c 6d"),
    ("Ac Ad 6c 7d 8s", "Ah As Kh Qc Jd"),
])
def test_unbeatable_river_has_full_equity(text, board):
    from dataclasses import replace
    game = Game(make_deal("nuts", 0), button_seat=0, hand_index=0)
    obs = replace(game.observation(0), hole_cards=tuple(cards_from_str(text)),
                  board=tuple(cards_from_str(board)))
    memory = {}
    new_half(AgentConfig(), memory)
    uniform, tight = estimate(obs, memory)
    assert uniform == 1.0
    assert tight == pytest.approx(1.0)


def test_half_reset_reproduces_sample_and_clears_learning():
    from dataclasses import replace
    obs = Game(make_deal("repeat", 0), button_seat=0, hand_index=0).observation(0)
    used = set(obs.hole_cards)
    obs = replace(obs, board=tuple(c for c in range(36) if c not in used)[:3])
    memory = {}
    new_half(AgentConfig(), memory)
    first = estimate(obs, memory)
    assert estimate(obs, memory) == first
    memory.clear()  # the server's actual new-half lifecycle
    new_half(AgentConfig(), memory)
    assert estimate(obs, memory) == first
    assert memory["opp_raises"] == 0
