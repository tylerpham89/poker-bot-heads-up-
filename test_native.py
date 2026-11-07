"""Cross-check accelerated scoring and sampling against independent references."""
from itertools import combinations
import random
import numpy as np
import pytest

from evaluator import get_table
from fallback_strategy import BITS, board_masks, score_masks
from native_engine import LIB, evaluate, samples

pytestmark=pytest.mark.skipif(LIB is None,reason='Native binary unavailable for this platform')


def test_native_matches_reference_for_every_board_length():
    rng=random.Random(12939)
    for _ in range(1000):
        cards=rng.sample(range(36),10)
        pairs=tuple(BITS[a]|BITS[b] for a,b in combinations(cards[:5],2))
        for n in (3,4,5):
            assert evaluate(cards[:5],cards[5:5+n])==score_masks(pairs,board_masks(cards[5:5+n]),get_table())


def test_river_simulation_matches_exact_opponent_enumeration():
    hole=(1,8,15,22,29)
    board=(3,12,17,25,34)
    deck=[c for c in range(36) if c not in hole+board]
    hero=evaluate(hole,board)
    win,total=0.0,0
    for opponent in combinations(deck,5):
        other=evaluate(opponent,board)
        win+=1 if hero>other else 0.5 if hero==other else 0
        total+=1
    empirical=np.ctypeslib.as_array(samples(hole,board,16384,98211)).reshape(-1,4)[:,0].mean()
    assert abs(empirical-win/total)<0.015


def test_native_sampler_is_reproducible():
    args=((0,5,10,15,20),(25,30,35),512,73933)
    a=np.ctypeslib.as_array(samples(*args)).copy()
    b=np.ctypeslib.as_array(samples(*args)).copy()
    assert np.array_equal(a,b)
    assert np.all(np.isin(a.reshape(-1,4)[:,0],[0,0.5,1]))
