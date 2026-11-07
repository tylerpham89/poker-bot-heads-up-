"""Run the unmodified HTTP judge against all supplied practice opponents."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parent


def wait_ready(process, port):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Server on {port} exited with {process.returncode}")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=0.5) as r:
                if r.status == 200:
                    return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError(f"Server on {port} did not become healthy")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--deals", type=int, default=1000)
    parser.add_argument("--seeds", nargs="+", default=["7", "42"])
    parser.add_argument("--opponents", nargs="+", default=["random", "calling_station", "always_half", "always_pot"])
    parser.add_argument("--output-dir", default="validation")
    parser.add_argument("--keep-going", action="store_true", help="Finish all matches even if reliability checks fail")
    args = parser.parse_args()
    output = ROOT / args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    summary = []
    failed = False
    for opponent in args.opponents:
        for seed in args.seeds:
            processes, logs = [], []
            label = f"{opponent}-seed{seed}-deals{args.deals}"
            try:
                for script, port in [("agent.py", 15008), (f"baseline-bots/baseline_{opponent}.py", 15009)]:
                    log = open(output / f"{label}-{port}.log", "w")
                    logs.append(log)
                    env = dict(os.environ, PORT=str(port))
                    proc = subprocess.Popen([sys.executable, script], cwd=ROOT, env=env,
                                            stdout=log, stderr=subprocess.STDOUT,
                                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                    processes.append(proc)
                    wait_ready(proc, port)
                result = subprocess.run([sys.executable, "judge_engine.py", "--agent1", "http://127.0.0.1:15008",
                    "--agent2", "http://127.0.0.1:15009", "--deals", str(args.deals), "--seed", seed,
                    "--json", str(output / f"{label}.json")], cwd=ROOT, capture_output=True, text=True)
                (output / f"{label}.txt").write_text(result.stdout + result.stderr)
                print(result.stdout, flush=True)
                result.check_returncode()
                data = json.loads((output / f"{label}.json").read_text())
                bad = [s for s in data["agent_stats"]["agent1"]
                       if s["errors"] or s["forfeited"] or s["timed_out"] or s["skipped_calls"]]
                if bad:
                    failed = True
                    if not args.keep_going:
                        raise RuntimeError(f"Bot failed reliability checks: {bad}")
                    print(f"RELIABILITY FAILURE: {label}: {bad}", flush=True)
                summary.append({"opponent": opponent, "seed": seed, "deals": args.deals,
                                "verdict": data["verdict"],
                                "bb_per_deal": data["mean_bb_per_deal"],
                                "thinking_seconds": [s["time_seconds"] for s in data["agent_stats"]["agent1"]],
                                "reliable": not bad,
                                "result_file": f"{label}.json"})
            finally:
                for proc in processes:
                    proc.terminate()
                for proc in processes:
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                for log in logs:
                    log.close()
    previous = json.loads((output / "runs.json").read_text()) if (output / "runs.json").exists() else []
    indexed = {r["result_file"]: r for r in previous + summary}
    (output / "runs.json").write_text(json.dumps(list(indexed.values()), indent=2) + "\n")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
