"""Budgeted short-deck PLO5 equity and opponent-aware betting policy.

Only public observations are used. All learning and simulation caches belong
to the half's memory, and no files or network are needed during play.
"""
from itertools import combinations
import random
import time

from evaluator import get_table
from game import Action, Street

BITS = tuple(1 << c for c in range(36))
PAIRS = tuple(combinations(range(5), 2))


def preflop_strength(hole):
    """Cheap starting-hand prior; pairs, nut suits and connectedness matter."""
    ranks = [c >> 2 for c in hole]
    counts = [ranks.count(r) for r in range(9)]
    value = 0.45 + (sum(ranks) - 20) * 0.004
    for r, n in enumerate(counts):
        if n >= 2:
            value += 0.035 + r * 0.006
        if n >= 3:  # extra copies block our own two-card combinations
            value -= 0.055 * (n - 2)
    for s in range(4):
        suited = [c >> 2 for c in hole if c & 3 == s]
        if len(suited) >= 2:
            value += 0.025 + max(suited) * 0.003
            value -= max(0, len(suited) - 2) * 0.018
    distinct = set(ranks)
    windows = [set(range(i, i + 5)) for i in range(5)]
    windows.append({8, 0, 1, 2, 3})
    connected = max(len(distinct & w) for w in windows)
    value += (connected - 3) * 0.018
    return min(0.77, max(0.30, value))


def board_masks(board):
    return tuple(BITS[a] | BITS[b] | BITS[c]
                 for a, b, c in combinations(board, 3))


def score_masks(hole_masks, triples, table):
    best = 0
    for hm in hole_masks:
        for bm in triples:
            v = table[hm | bm]
            if v > best:
                best = v
    return best


def estimate(obs, memory):
    """Common samples across repeat decisions avoid action-to-action noise.

    Opponent samples are ranked by their strength on the *visible* board.
    The weighted estimate approximates a value-heavy betting range; future
    cards are never used to decide which opponent samples get more weight.
    """
    key = (obs.hand_index, obs.hole_cards, obs.board)
    if memory.get("equity_key") == key:
        return memory["equity"]
    known = set(obs.hole_cards + obs.board)
    deck = [c for c in range(36) if c not in known]
    seed = sum(BITS[c] for c in known) ^ (obs.hand_index * 1000003)
    rng = random.Random(seed)
    table = get_table()
    hm = tuple(BITS[a] | BITS[b] for a, b in combinations(obs.hole_cards, 2))
    visible = board_masks(obs.board)
    missing = 5 - len(obs.board)
    n = (40, 56, 128)[len(obs.board) - 3]
    # Preserve a safety margin even on a slow CPU. This is a computation
    # budget, not an assumption that HTTP overhead is free.
    hands = max(1, memory.get("num_hands", 1000))
    allowance = memory.get("compute_budget", 3.0) * (obs.hand_index + 20) / hands
    if memory.get("compute_used", 0) > allowance:
        n = max(16, n // 2)
    samples = []
    river_cache = {}
    hero_river = score_masks(hm, visible, table) if not missing else None
    for _ in range(n):
        draw = rng.sample(deck, 5 + missing)
        opponent = draw[:5]
        om = tuple(BITS[opponent[i]] | BITS[opponent[j]] for i, j in PAIRS)
        if missing:
            full = board_masks(obs.board + tuple(draw[5:]))
            hero = score_masks(hm, full, table)
            villain = score_masks(om, full, table)
            current = score_masks(om, visible, table)
        else:
            hero = hero_river
            villain = 0
            for mask in om:
                v = river_cache.get(mask)
                if v is None:
                    v = max(table[mask | b] for b in visible)
                    river_cache[mask] = v
                if v > villain:
                    villain = v
            current = villain
        samples.append((current, 1.0 if hero > villain else 0.5 if hero == villain else 0.0))
    samples.sort(key=lambda x: x[0])
    uniform = sum(s[1] for s in samples) / n
    # Smooth weighting avoids unstable rejection sampling on tiny ranges.
    weighted = sum(s[1] * (0.1 + (i / (n - 1)) ** 3)
                   for i, s in enumerate(samples))
    weights = sum(0.1 + (i / (n - 1)) ** 3 for i in range(n))
    answer = (uniform, weighted / weights)
    memory["equity_key"], memory["equity"] = key, answer
    return answer


def new_half(config, memory):
    memory.update(hands_played=0, opp_actions=0, opp_raises=0,
                  opp_folds=0, seen_history=0, hand=-1, compute_used=0.0,
                  num_hands=config.num_hands,
                  compute_budget=min(3.0, config.time_bank_seconds * 0.4))


def choose_action(obs, memory):
    started = time.perf_counter()
    try:
        return _choose(obs, memory)
    finally:
        memory["compute_used"] = memory.get("compute_used", 0.0) + time.perf_counter() - started


def _choose(obs, memory):
    if memory.get("hand") != obs.hand_index:
        memory["hand"], memory["seen_history"] = obs.hand_index, 0
    for event in obs.action_history[memory.get("seen_history", 0):]:
        if not event.is_me:
            memory["opp_actions"] = memory.get("opp_actions", 0) + 1
            if event.action in (Action.RAISE_HALF, Action.RAISE_POT):
                memory["opp_raises"] = memory.get("opp_raises", 0) + 1
    memory["seen_history"] = len(obs.action_history)
    aggression = (memory.get("opp_raises", 0) + 4) / (memory.get("opp_actions", 0) + 12)
    raises = [e for e in obs.action_history if not e.is_me
              and e.street == obs.street and e.action in (Action.RAISE_HALF, Action.RAISE_POT)]
    pressure = len(raises)
    legal = obs.legal_actions
    call = Action.CHECK_CALL if Action.CHECK_CALL in legal else legal[0]
    fold = Action.FOLD if Action.FOLD in legal else call
    pot_odds = min(obs.to_call, obs.my_stack) / max(1, obs.pot + min(obs.to_call, obs.my_stack))
    if obs.street == Street.PREFLOP:
        equity = preflop_strength(obs.hole_cards)
        # Defend blinds widely, tighten against repeated expensive raises.
        if obs.to_call > obs.big_blind and equity < 0.44 + 0.035 * pressure + 0.05 * (aggression < 0.2):
            return fold
        threshold = 0.57 if pressure == 0 else 0.65 + 0.025 * pressure
        if equity > threshold and Action.RAISE_POT in legal:
            return Action.RAISE_POT
        return call
    uniform, tight = estimate(obs, memory)
    # Frequent raisers have a wider range; passive players' bets deserve credit.
    range_weight = 0.0
    if pressure:
        range_weight = min(0.9, max(0.05, 0.85 - aggression * 1.5) + 0.12 * (pressure - 1))
    elif obs.pot > 12 * obs.big_blind:
        range_weight = 0.20
    equity = uniform * (1 - range_weight) + tight * range_weight
    if obs.to_call:
        margin = 0.035 if obs.street == Street.RIVER else 0.065
        if obs.opp_stack == 0:
            margin = 0.02
        if equity < pot_odds + margin:
            return fold
    # A bet needs enough equity to survive selection by the calling range.
    threshold = (0.60, 0.63, 0.67)[int(obs.street) - 1] + 0.04 * pressure
    if equity > threshold:
        action = Action.RAISE_POT if equity > 0.78 or obs.street == Street.FLOP else Action.RAISE_HALF
        if action in legal:
            return action
    # Small, infrequent steals against opponents who demonstrably overfold.
    folds = (memory.get("opp_folds", 0) + 2) / (memory.get("hands_played", 0) + 10)
    if not obs.to_call and obs.is_button and not pressure and folds > 0.6:
        if uniform > 0.25 and (obs.hand_index * 17 + int(obs.street)) % 7 == 0:
            if Action.RAISE_HALF in legal:
                return Action.RAISE_HALF
    return call


def on_hand_end(result, memory):
    memory["hands_played"] = memory.get("hands_played", 0) + 1
    if not result.went_to_showdown and result.winner == "me":
        memory["opp_folds"] = memory.get("opp_folds", 0) + 1
