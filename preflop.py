"""Small offline-trained linear equity model with poker-specific features."""
import json
from pathlib import Path


def features(hole):
    ranks = [c >> 2 for c in hole]
    counts = [ranks.count(r) for r in range(9)]
    suits = [[c >> 2 for c in hole if c & 3 == s] for s in range(4)]
    distinct = set(ranks)
    windows = [set(range(i, i+5)) for i in range(5)] + [{8,0,1,2,3}]
    connectivity = [len(distinct & w) for w in windows]
    pairs = [float(c >= 2) for c in counts]
    x = [1.0] + [c / 4 for c in counts] + pairs
    x += [sum(c >= 3 for c in counts), sum(c == 4 for c in counts)]
    x += [sum(len(s) == n for s in suits) for n in (2,3,4,5)]
    x += [sum(max(s)/8 for s in suits if len(s)>=2),
          sum(8 in s for s in suits if len(s)>=2)]
    x += [sum(c >= n for c in connectivity) for n in (2,3,4,5)]
    x += [sum(abs(a-b)==d for i,a in enumerate(distinct) for b in list(distinct)[i+1:]) for d in (1,2,3)]
    x += [sum(ranks)/40, sum(r*r for r in ranks)/320, max(ranks)/8,
          len(distinct)/5, sum(pairs)*sum(ranks)/40]
    return x


MODEL_PATH = Path(__file__).with_name("preflop-model.json")
MODEL = json.loads(MODEL_PATH.read_text()) if MODEL_PATH.exists() else None


def strength(hole):
    if MODEL is None:
        from fallback_strategy import preflop_strength
        return min(0.65, max(0.35, 0.5 + (preflop_strength(hole)-0.52)*0.5))
    return min(0.80, max(0.20, sum(a*b for a,b in zip(features(hole), MODEL['coefficients']))))
