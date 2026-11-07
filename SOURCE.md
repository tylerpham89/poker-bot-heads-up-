# Provenance

Official starter: https://github.com/tamu-datathon-org/heads-up-bundle

Downloaded commit: c83ab6eeb7660a2fd1fae7df224315d41fe985a9

`game.py`, `evaluator.py`, `judge_engine.py`, `test_agent.py`, the four original
practice bots, Docker recipes, build tools and `requirements-dev.txt` remain
unchanged. `requirements.txt` adds NumPy to the starter server requirements.
The original `agent.py` server plumbing is unchanged; the identity and three
strategy hooks are configured for PocketEdge v2.

New files implement the policy, native sampler, offline calibration, tests,
comparison tools, packaging and documentation. `fallback_strategy.py` is the
frozen original PocketEdge strategy, preserved for comparisons and fallback.
`baseline-bots/baseline_v1.py` serves that policy through the same HTTP routes.
The native binaries are built from `native/equity.c` using Zig 0.13.0.
`build_native.py` records the build flags and targets.

The pristine checkout remains in `starter/` locally, excluded from the ZIP.
`STARTER_README.md` preserves the official setup instructions. `archive-v1/`
keeps the old submission locally and is excluded from packaging.
