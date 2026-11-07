"""
harness.py - fast in-process duplicate matches (no HTTP), scored like the judge.

Each match plays the same deals twice with seats swapped, gives each bot a
fresh memory every half, enforces the time bank and error limit the way the
judge does, and scores paired bb/deal with a 95% interval.

Any .py file that defines new_half / choose_action / on_hand_end can play
(agent.py, the baseline bots, dev/zoo/*). Add "@key=value,..." to a bot
path to override bot.policy PARAMS for that bot only.

    python dev/harness.py                                   # agent.py vs baselines + zoo
    python dev/harness.py --opp baselines --deals 1000 --seeds 5
    python dev/harness.py --bot "agent.py@r_oop=0.8" --opp agent.py
"""

import argparse
import glob
import importlib.util
import math
import os
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from game import (BIG_BLIND, CHOP_Z, ERROR_LIMIT, NUM_DEALS, TIME_BANK_SECONDS,  # noqa: E402
                  AgentConfig, Game, button_for_deal, default_action, make_deal)

GROUPS = {
    "baselines": sorted(glob.glob(os.path.join(ROOT, "baseline-bots", "*.py"))),
    "zoo": sorted(p for p in glob.glob(os.path.join(ROOT, "dev", "zoo", "*.py")) if not os.path.basename(p).startswith("_")),
}


def _parse(spec: str) -> tuple[str, dict]:
    path, _, opts = spec.partition("@")
    overrides = {}
    for item in filter(None, opts.split(",")):
        key, _, value = item.partition("=")
        overrides[key] = float(value)
    if not os.path.isabs(path):
        path = os.path.join(ROOT, path)
    return path, overrides


def _load(path: str, tag: str):
    if os.path.dirname(path) not in sys.path:
        sys.path.insert(0, os.path.dirname(path))  # zoo bots import their sibling _common.py
    spec = importlib.util.spec_from_file_location(f"harness_{tag}_{abs(hash(path))}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Player:
    """One bot for one half, with the judge's time bank and error rules."""

    def __init__(self, module, overrides: dict, config: AgentConfig):
        self.m, self.memory = module, {}
        self.spent, self.errors, self.skipped = 0.0, 0, 0
        self.times: list[float] = []
        self.forfeited = False
        self.bank = config.time_bank_seconds
        self._call(lambda: module.new_half(config, self.memory))
        if overrides and "params" in self.memory:
            self.memory["params"].update(overrides)

    def _call(self, fn):
        start = time.perf_counter()
        try:
            return fn(), True
        except Exception:
            self._error()
            return None, False
        finally:
            elapsed = time.perf_counter() - start
            self.spent += max(0.0, elapsed - 0.001)
            if elapsed > 1.0:
                self._error()

    def _error(self):
        self.errors += 1
        if self.errors >= ERROR_LIMIT:
            self.forfeited = True

    def act(self, obs):
        if self.forfeited or self.spent >= self.bank:
            self.skipped += 1
            return default_action(obs.to_call)
        start = time.perf_counter()
        action, ok = self._call(lambda: self.m.choose_action(obs, self.memory))
        self.times.append(time.perf_counter() - start)
        if ok:
            try:
                action = type(obs.legal_actions[0])(action) if not hasattr(action, "name") else action
            except Exception:
                action = None
            if action in obs.legal_actions:
                return action
            self._error()
        return default_action(obs.to_call)

    def hand_end(self, result):
        if not self.forfeited and self.spent < self.bank:
            self._call(lambda: self.m.on_hand_end(result, self.memory))


def play_half(mod_a, ov_a, mod_b, ov_b, seed, half: int, deals: int, config: AgentConfig):
    """Bot A sits in seat 0 in half 1 and seat 1 in half 2. Returns A's nets and both players."""
    a, b = Player(mod_a, ov_a, config), Player(mod_b, ov_b, config)
    seats = (a, b) if half == 1 else (b, a)
    a_seat = 0 if half == 1 else 1
    nets = []
    for d in range(deals):
        game = Game(make_deal(str(seed), d), button_for_deal(d), hand_index=d)
        while not game.is_terminal:
            seat = game.to_act
            game.apply(seats[seat].act(game.observation(seat)))
        for seat in (0, 1):
            seats[seat].hand_end(game.hand_result(seat))
        nets.append(game.result().nets[a_seat])
    return nets, a, b


def run_match(job):
    bot_spec, opp_spec, seed, deals, bank = job
    (pa, oa), (pb, ob) = _parse(bot_spec), _parse(opp_spec)
    mod_a, mod_b = _load(pa, "a"), _load(pb, "b")
    config = AgentConfig(num_hands=deals, time_bank_seconds=bank)
    n1, a1, b1 = play_half(mod_a, oa, mod_b, ob, seed, 1, deals, config)
    n2, a2, b2 = play_half(mod_a, oa, mod_b, ob, seed, 2, deals, config)
    paired = [(x + y) / BIG_BLIND for x, y in zip(n1, n2)]
    mean = sum(paired) / len(paired)
    se = statistics.stdev(paired) / math.sqrt(len(paired))
    lo, hi = mean - CHOP_Z * se, mean + CHOP_Z * se
    forfeit = a1.forfeited or a2.forfeited
    verdict = "LOSS" if forfeit else "WIN" if lo > 0 else "LOSS" if hi < 0 else "CHOP"
    times = a1.times + a2.times
    return {
        "opp": os.path.basename(opp_spec), "seed": seed, "mean": mean, "lo": lo, "hi": hi,
        "std": statistics.stdev(paired), "verdict": verdict,
        "errors": a1.errors + a2.errors, "skipped": a1.skipped + a2.skipped,
        "opp_errors": b1.errors + b2.errors,
        "spend": max(a1.spent, a2.spent), "times": times,
    }


def _pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bot", default="agent.py")
    parser.add_argument("--opp", nargs="+", default=["baselines", "zoo"],
                        help="bot paths and/or the groups 'baselines', 'zoo'")
    parser.add_argument("--deals", type=int, default=NUM_DEALS)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument("--bank", type=float, default=TIME_BANK_SECONDS,
                        help="time bank per half (lower it to mimic a slower CPU)")
    parser.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    args = parser.parse_args()

    opps = []
    for o in args.opp:
        opps.extend(GROUPS.get(o, [o]))
    jobs = [(args.bot, o, f"h{args.seed_offset + s}", args.deals, args.bank)
            for o in opps for s in range(args.seeds)]
    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(run_match, jobs))

    print(f"{args.bot} | {args.deals} deals x {args.seeds} seeds | bank {args.bank}s\n")
    print(f"{'opponent':32} {'bb/deal':>8} {'95% CI (pooled)':>18} {'W-C-L':>7} "
          f"{'err':>4} {'skip':>5} {'p50ms':>6} {'p99ms':>6} {'max spend':>9}")
    total_points = 0.0
    for o in opps:
        rs = [r for r in results if r["opp"] == os.path.basename(o)]
        n = len(rs) * args.deals
        mean = sum(r["mean"] for r in rs) / len(rs)
        pooled_se = math.sqrt(sum(r["std"] ** 2 for r in rs) / len(rs)) / math.sqrt(n)
        wcl = [sum(r["verdict"] == v for r in rs) for v in ("WIN", "CHOP", "LOSS")]
        total_points += wcl[0] + 0.5 * wcl[1]
        times = [t for r in rs for t in r["times"]]
        print(f"{os.path.basename(o)[:32]:32} {mean:+8.3f} [{mean - 1.96 * pooled_se:+7.3f},"
              f"{mean + 1.96 * pooled_se:+7.3f}] {'-'.join(map(str, wcl)):>7} "
              f"{sum(r['errors'] for r in rs):4d} {sum(r['skipped'] for r in rs):5d} "
              f"{1000 * _pct(times, .5):6.2f} {1000 * _pct(times, .99):6.2f} "
              f"{max(r['spend'] for r in rs):8.2f}s")
    print(f"\npoints {total_points:.1f} / {len(results)}   ({time.perf_counter() - start:.0f}s)")


if __name__ == "__main__":
    main()
