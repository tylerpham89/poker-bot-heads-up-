# Validation results

Tested locally on Windows with Python 3.11 on November 7, 2026.

- 16 tests passed: all 12 official interface tests plus four strategy checks.
- Official standalone HTTP smoke test passed (`validation/smoke-test.txt`).
- Eight full duplicate matches: 1,000 deals in each seat order, 16,000 total hands.
- Zero bot errors, forfeits, time-bank exhaustion, or skipped decisions.
- Official rules, evaluator, judge, interface tests, requirements and server plumbing are unchanged.

| Opponent | Seed | bb/deal | 95% confidence interval | Thinking seconds, halves 1 / 2 | Result |
|---|---:|---:|---|---|---|
| always_half | 42 | +12.134 | [+10.737, +13.531] | 2.06 / 1.99 | Win |
| always_half | 7 | +11.484 | [+10.070, +12.898] | 2.06 / 3.04 | Win |
| always_pot | 42 | +7.453 | [+5.843, +9.063] | 2.34 / 2.22 | Win |
| always_pot | 7 | +7.043 | [+5.416, +8.670] | 2.33 / 2.34 | Win |
| calling_station | 42 | +9.501 | [+8.635, +10.367] | 3.33 / 4.06 | Win |
| calling_station | 7 | +8.966 | [+8.123, +9.809] | 2.88 / 4.20 | Win |
| random | 42 | +6.042 | [+4.715, +7.368] | 2.18 / 2.69 | Win |
| random | 7 | +7.745 | [+6.441, +9.050] | 2.22 / 2.16 | Win |

Thinking time is charged by the official judge against its eight-second bank per half.
Timing varies by host. The highest observed charged time was 4.20 seconds.

Full machine-readable results and judge reports are in `validation/`.
Results establish an edge over the supplied baselines on these seeds; they do not establish tournament strength against other teams.

## Remaining deployment check

Docker Desktop was not running, so the Linux container build and resource-restricted container smoke test were not run.
Run `bash tools/check_build.sh` after starting Docker Desktop. Local HTTP checks do not substitute for that check.

## Reproduce

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest test_agent.py test_strategy.py -q
python verify_solution.py --seeds 7 42
```
