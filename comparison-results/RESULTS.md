# Latest baseline comparison

Rerun on Windows with Python 3.11.9. Both bots played locally through the unchanged official HTTP judge.

PocketEdge won all eight duplicate matches: 16,000 hands across four opponents and seeds 7 and 42.
There were zero exceptions/illegal-action errors or forfeits. However, four of the sixteen halves exhausted the eight-second time bank, across three matches. A total of 1,315 decisions were skipped.
These timing failures mean the solution does not consistently satisfy the runtime target on this host.

| Opponent | Seed | bb/deal | 95% interval | Thinking seconds, halves 1 / 2 | Exhausted halves | Skipped decisions |
|---|---:|---:|---|---|---:|---:|
| always_half | 42 | +12.106 | [+10.709, +13.503] | 6.92 / 7.72 | 0 | 0 |
| always_half | 7 | +11.309 | [+9.880, +12.739] | 8.00 / 6.75 | 1 | 36 |
| always_pot | 42 | +6.902 | [+5.272, +8.532] | 5.37 / 6.92 | 0 | 0 |
| always_pot | 7 | +6.547 | [+4.893, +8.201] | 5.01 / 5.68 | 0 | 0 |
| calling_station | 42 | +7.350 | [+6.535, +8.165] | 8.01 / 8.02 | 2 | 960 |
| calling_station | 7 | +8.643 | [+7.793, +9.492] | 8.01 / 7.90 | 1 | 319 |
| random | 42 | +6.987 | [+5.668, +8.306] | 6.35 / 5.33 | 0 | 0 |
| random | 7 | +7.827 | [+6.513, +9.141] | 5.30 / 6.45 | 0 | 0 |

The earlier validation is retained in `../validation/` and `../VALIDATION.md`.
The strategy and server code are unchanged. Timing affects the adaptive sampling budget and can therefore change actions and scores across runs.
The comparison tool was updated only to finish all matches and retain reports after a reliability failure.

Baseline wins do not predict the result against another team. Use `../RUN_WITH_FRIEND.md` for direct head-to-head instructions.

Machine-readable results: `comparison.csv` and `summary.json`. Individual `.json` and `.txt` files are the full official judge outputs.
