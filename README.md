# PocketEdge v2

An improved bot for the TAMU Datathon short-deck, five-card Omaha challenge.
See `RUN_WITH_FRIEND.md` to compare it with another player's bot, and
`OPTIMIZATION.md` for measured improvements and complete test results.

## Run

Extract the entire ZIP, then open a terminal in the folder containing `agent.py`.
Python 3.10 or newer is required.

```text
python -m pip install -r requirements-dev.txt
python -m pytest -q
python agent.py
```

The bot listens on port 5008. Set `PORT` to change it. On macOS/Linux use
`python3` if needed. The ZIP contains all model data and native libraries;
Python packages are installed through pip. No compiler or API key is needed.

For this original workspace only, dependencies are also available by setting
`$env:PYTHONPATH = (Resolve-Path ../.codex-deps).Path` in PowerShell.

## What improved

- A native sampler replaces Python's inner equity loop. It uses the exact
  official short-deck hand scores and the two-hole-card/three-board-card rule.
  The policy uses 320 flop, 448 turn, and 1,024 river samples, reducing the
  counts if needed to stay within its computation budget.
- A small preflop model is calibrated on 8,000 independently simulated hands,
  with 2,048 Monte Carlo samples per hand. Its held-out equity RMSE was 0.0143.
- Opponent ranges account for visible bets on earlier streets, opponent
  betting frequency, and observed showdown bluffs. Turn range information
  is used when acting on the turn; the river range model uses available
  preflop, flop and river strength estimates.
- Calls use pot odds; value raises account for how the opponent's range is
  selected by calling. Limited river bluffs adapt to observed folds.

The native libraries are provided for Windows x64, Linux x64/ARM64 and macOS
Intel/Apple Silicon. Windows was tested directly. Linux and macOS binaries
were cross-compiled and have not been executed on those operating systems.
A slower Python fallback is available on unsupported platforms or if loading
fails; the recorded v2 timing results require the native engine.

## Verify

```text
python verify_solution.py --seeds 7 42 --output-dir my-results
python verify_solution.py --opponents v1 --seeds 1009 2027 --output-dir versus-v1
```

The first command tests all four official baselines through the unmodified
HTTP judge. The second tests the frozen v1 policy. Both play 1,000 deals in
both seat orders and save results. Ports 15008 and 15009 must be free.
Add `--keep-going` to finish after a reliability failure; exit status 1 still
indicates that errors, forfeits, exhausted banks, or skipped calls occurred.

`arena.py` runs direct strategy comparisons with the old bot and three
synthetic opponents (`equity`, `tight`, `pressure`). Those measure strategy
quality and compute time, while HTTP tests measure the tournament time bank.
These are development opponents, not your friend's private code.

## Files and reproduction

`strategy.py` implements the policy, `native_engine.py` loads the accelerator,
`native/equity.c` is its source, and `preflop-model.json` is the trained model.
`fallback_strategy.py` preserves the v1 policy for reproducible comparisons.

To rebuild the native libraries, install `ziglang==0.13.0` and run
`python build_native.py`. To retrain preflop calibration, run
`python train_preflop.py --hands 8000 --samples 2048`. Neither step is needed
to run the supplied ZIP. `package_solution.py` recreates the shareable ZIP.

## Submit

The registered team name is `goons`, configured as the default `PARTICIPANT`
in `agent.py`. The bot identifies itself as `PocketEdge v2`.
Start Docker Desktop and run `bash tools/check_build.sh` from Git Bash or WSL.
Docker validation remains outstanding because the daemon was unavailable.

Put this directory's contents at the root of your public team repository,
commit and push, then submit the full 40-character commit SHA using the
organizer's form. Registration and submission are separate organizer steps.
Team registration and the organizer submission form are handled separately.

The unchanged organizer instructions are in `STARTER_README.md`; provenance
is in `SOURCE.md`. Older v1 measurements are retained in `VALIDATION.md` and
`comparison-results/`; current v2 results are in `OPTIMIZATION.md` and
`optimization-results/`. These are tested heuristics, not a solved equilibrium
or a guarantee of winning against any particular player.
