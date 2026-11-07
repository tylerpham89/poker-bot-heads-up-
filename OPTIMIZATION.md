# PocketEdge v2 optimization results

## Outcome

The revised bot won all ten official HTTP matches (20,000 hands): eight against the supplied baselines and two against the frozen original PocketEdge policy.
It recorded zero errors, forfeits, skipped decisions, or exhausted time banks.
The highest charged thinking time was 2.46 seconds out of eight per half. These are local Windows measurements, not a guarantee on every host.

| Opponent | Seed | v2 bb/deal | 95% confidence interval | v2 thinking seconds: half 1 / half 2 |
|---|---:|---:|---|---|
| always_half | 42 | +10.799 | [+9.403, +12.195] | 0.91 / 0.79 |
| always_half | 7 | +10.667 | [+9.259, +12.075] | 1.41 / 2.04 |
| always_pot | 42 | +7.184 | [+5.582, +8.786] | 0.87 / 1.00 |
| always_pot | 7 | +6.881 | [+5.288, +8.474] | 1.21 / 1.07 |
| calling_station | 42 | +12.425 | [+11.401, +13.449] | 2.46 / 1.39 |
| calling_station | 7 | +11.134 | [+10.136, +12.132] | 1.81 / 1.23 |
| random | 42 | +6.859 | [+5.526, +8.191] | 1.04 / 1.46 |
| random | 7 | +6.393 | [+5.093, +7.693] | 1.26 / 0.98 |
| v1 | 1009 | +1.880 | [+1.242, +2.518] | 1.51 / 1.59 |
| v1 | 2027 | +1.279 | [+0.712, +1.846] | 0.83 / 0.82 |

Both players also stayed within the bank in the direct v2-versus-v1 HTTP matches; the win was not caused by the old bot forfeiting or running out of time.
The old policy and the official rules, evaluator, judge, tests, and server plumbing were verified unchanged.

## Strategy changes

- Native C simulation uses the official five-card score table. It evaluates Omaha with exactly two private and three shared cards.
- Sampling increases from v1's 40/56/128 to 320/448/1,024 flop/turn/river samples, with caching and a conservative computation budget.
- Preflop equities are calibrated from 8,000 hands with 2,048 simulations each. A 1,600-hand holdout had RMSE 0.0143 and correlation 0.9758; coefficients were then refit on all labels.
- Action-range inference conditions on observed bets, betting frequency, and showdown bluffs. Calls use pot odds, and raises account for selection by the opponent's calling range.

## Additional checks

- All 19 tests pass: the 12 official interface tests, four prior strategy tests, and three new native-engine checks.
- 3,000 random native scores were compared with independent reference scores across flop, turn and river.
- A river Monte Carlo estimate was checked against exact enumeration of all 65,780 legal opponent hands.
- The official standalone HTTP smoke test passed (`optimization-results/smoke-test.txt`).
- Eight in-process matches on new seeds also beat the original policy and three synthetic equity/tight/pressure opponents. Every confidence interval was above zero; see `optimization-results/heldout-arena.json`.

## Reproduce

```text
python -m pip install -r requirements-dev.txt
python -m pytest -q
python verify_solution.py --seeds 7 42 --output-dir my-baselines
python verify_solution.py --opponents v1 --seeds 1009 2027 --output-dir my-v1-comparison
python arena.py --deals 1000 --seeds 1009 2027 --output my-arena.json
```

Timing may affect the adaptive sample budget, so repeated runs can produce slightly different decisions and scores even with the same deal seeds.

## Scope and limitations

No direct comparison with your friend's private bot was possible because its code and head-to-head report were unavailable. These results establish an improvement over our previous bot and the listed opponents, not a guaranteed win against your friend.
The screenshot contains baseline hand counts; the tournament comparison uses chip profit in bb/deal and confidence intervals. Winning more hands does not necessarily mean winning more chips.
Windows x64 was tested directly. Linux x64/ARM64 and macOS Intel/Apple Silicon libraries were cross-compiled, but not executed on those OSes. The Linux libraries have no undefined global symbols; no external C runtime is required.
Docker was unavailable, so the resource-restricted Linux container build/smoke check remains outstanding. Run `bash tools/check_build.sh` before tournament submission.
Older v1 results are retained separately in `VALIDATION.md` and `comparison-results/`. The frozen old submission is in `archive-v1/` locally and is excluded from the new ZIP.
