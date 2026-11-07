"""
compare.py - paired A/B test of bot configs on identical duplicate deals.

Every config plays the same seeds against the same opponents, so the
per-deal difference between two configs cancels the card luck: its 95%
interval is far tighter than comparing two separate harness runs.

    python dev/compare.py --opp dev/sparring/jammer.py --seeds 6 \\
        new=agent.py "old=agent.py@fixcount=0,sd_use=0"
    python dev/compare.py --opp zoo sparring --seeds 3 new=agent.py off=agent.py@lookahead=0

The first config is the reference; every other one is reported as its
difference from it ("X - ref"), per opponent and pooled.
"""

import argparse
import math
import os
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import GROUPS, _load, _parse, play_half  # noqa: E402  (also adds repo root to sys.path)

from game import BIG_BLIND, CHOP_Z, AgentConfig  # noqa: E402


def _run(job):
    name, spec, opp, seed, deals = job
    path, ov = _parse(spec)
    opath, oov = _parse(opp)
    mod, omod = _load(path, f"c{name}"), _load(opath, "o")
    config = AgentConfig(num_hands=deals)
    n1, a1, _ = play_half(mod, ov, omod, oov, seed, 1, deals, config)
    n2, a2, _ = play_half(mod, ov, omod, oov, seed, 2, deals, config)
    paired = [(x + y) / BIG_BLIND for x, y in zip(n1, n2)]
    return name, os.path.basename(opp), seed, paired, max(a1.spent, a2.spent), a1.errors + a2.errors


def _ci(xs):
    m = statistics.mean(xs)
    se = statistics.stdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else 0.0
    return m, m - CHOP_Z * se, m + CHOP_Z * se


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("configs", nargs="+", help="name=botpath[@key=value,...]; the first is the reference")
    parser.add_argument("--opp", nargs="+", required=True, help="bot paths and/or groups (zoo, sparring, baselines)")
    parser.add_argument("--seeds", type=int, default=4)
    parser.add_argument("--deals", type=int, default=1000)
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    args = parser.parse_args()

    configs = [c.partition("=")[::2] for c in args.configs]
    opps = [o for g in args.opp for o in GROUPS.get(g, [g])]
    jobs = [(n, s, o, f"cmp{args.seed_offset + k}", args.deals)
            for o in opps for k in range(args.seeds) for n, s in configs]
    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(_run, jobs))

    data = {}  # (name, opp) -> {seed: (paired, spend, errors)}
    for name, opp, seed, paired, spend, errs in results:
        data.setdefault((name, opp), {})[seed] = (paired, spend, errs)
    names = [n for n, _ in configs]
    ref = names[0]
    print(f"{args.deals} deals x {args.seeds} seeds per opponent; reference = {ref}\n")
    pooled = {n: [] for n in names[1:]}
    points = {n: 0.0 for n in names}
    for o in [os.path.basename(x) for x in opps]:
        line = [f"{o[:26]:26}"]
        for n in names:
            runs = data[(n, o)]
            for paired, _, errs in runs.values():
                _, lo, hi = _ci(paired)
                points[n] += 0.0 if errs >= 5 else 1.0 if lo > 0 else 0.0 if hi < 0 else 0.5
            m, _, _ = _ci([x for s in sorted(runs) for x in runs[s][0]])
            line.append(f"{n} {m:+6.2f}")
        for n in names[1:]:
            d = [a - b for s in sorted(data[(n, o)])
                 for a, b in zip(data[(n, o)][s][0], data[(ref, o)][s][0])]
            pooled[n].append(statistics.mean(d))
            m, lo, hi = _ci(d)
            flag = " *" if lo > 0 else " !" if hi < 0 else ""
            line.append(f"| {n}-{ref} {m:+.2f} [{lo:+.2f},{hi:+.2f}]{flag}")
        print("  ".join(line))
    print()
    for n in names:
        spend = max(v[1] for (nn, _), runs in data.items() if nn == n for v in runs.values())
        extra = f"   avg diff vs {ref} {statistics.mean(pooled[n]):+.3f} bb/deal" if n in pooled else ""
        print(f"{n:12} points {points[n]:.1f} / {len(opps) * args.seeds}   max think/half {spend:.2f}s{extra}")
    print(f"\n(* = significantly better than {ref}, ! = significantly worse)   ({time.perf_counter() - start:.0f}s)")


if __name__ == "__main__":
    main()
