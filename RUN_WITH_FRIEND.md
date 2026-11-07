# Run PocketEdge locally

Extract the entire ZIP into a new folder. Open a terminal in that folder
(the folder containing `agent.py`). Use Python 3.10 or newer.

```text
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

On macOS/Linux, use `python3` if `python` is unavailable. A virtual environment
is recommended. No trained model, private file, API key, or external service
is needed. Dependencies are installed by pip; they are not embedded in the ZIP.
Do not use the original author's `.codex-deps` command on another computer.

## Play your own bot

1. In terminal 1, run `python agent.py`. PocketEdge listens on port 5008.
2. In terminal 2, start your bot on port 5009. It must implement the same
   HTTP protocol as this challenge's `agent.py`. If it is another copy of
   this starter, set `PORT` before starting it:

   Windows PowerShell:

   ```powershell
   $env:PORT = "5009"
   python path/to/your/agent.py
   ```

   macOS/Linux:

   ```sh
   PORT=5009 python3 path/to/your/agent.py
   ```

3. In terminal 3, run the judge from the extracted PocketEdge folder:

   ```text
   python judge_engine.py --agent1 http://127.0.0.1:5008 --agent2 http://127.0.0.1:5009 --deals 1000 --seed 7 --json friend-seed7.json
   python judge_engine.py --agent1 http://127.0.0.1:5008 --agent2 http://127.0.0.1:5009 --deals 1000 --seed 42 --json friend-seed42.json
   ```

PocketEdge is **agent 1**. Each command plays 2,000 hands, swapping seats and
reusing the deals. A positive `bb/deal` favors PocketEdge. The confidence
interval and final verdict indicate whether the advantage is clear enough
to count as a match win. Keep errors, forfeits, time usage, and skipped
decisions alongside the score. Run both bots on the same machine, and close
unnecessary heavy applications for a more useful timing comparison.

For a quick setup check, use `--deals 100` first. Use 1,000 deals for results
comparable to the included reports. Stop servers with Ctrl+C when finished.

## Practice baselines without another bot

This starts and cleans up both servers automatically on ports 15008/15009:

```text
python verify_solution.py --seeds 7 42 --keep-going --output-dir my-results
```

The runner tests four practice opponents and saves all results. With
`--keep-going`, reliability failures are recorded and the remaining matches
continue; the command still exits with status 1 if any reliability check
failed. Without this flag, it stops at the first failure.

## Version and timing

This package contains **PocketEdge v2**, which uses a native sampler and an
updated betting policy. The complete model, source and native binaries are
included. No compiler is required to run it. To confirm acceleration:

```text
python -c "from native_engine import LIB; print(LIB)"
```

This should display a loaded library, rather than `None`. Windows x64 has
been tested directly. Linux x64/ARM64 and macOS Intel/Apple Silicon libraries
were cross-compiled and are included, but have not been tested on those OSes.
If acceleration cannot load, the bot uses a slower fallback; its timing may
not match the v2 reports.

The old v1 package sometimes exhausted its time bank. See `OPTIMIZATION.md`
for current v2 results and `comparison-results/` for those older v1 results.
Docker's full restricted-container validation remains outstanding.
