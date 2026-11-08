"""
mirror_report.py - how often bot/mirror.py flags each kind of opponent.

Plays single halves of agent.py@mirror=1 against each opponent set and
prints the flag rate (detection for self / relatives / the equity family,
false positives for the rest), the hand it flagged on, replay agreement,
replays and detector time per half. Then plays agent.py vs agent.py with
BOTH detectors on vs both off and prints average pot and raise share
(flagging each other must never make the copies play passively).

    python3 dev/mirror_report.py --seeds 3 --deals 1000 --jobs 2
(dev/mirror_test.sh runs this, then the paired value test.)
"""

import argparse
import os
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from harness import GROUPS, ROOT, Player, _load, play_half  # noqa: E402

from bot import mirror  # noqa: E402
from game import RAISE_ACTIONS, AgentConfig, Game, button_for_deal, make_deal  # noqa: E402

ON = {"mirror": 1.0}


def opponent_sets():
    rel = lambda paths: [os.path.relpath(p, ROOT) for p in paths]  # noqa: E731
    equity = rel(GROUPS["equity"])
    challenger = [p for p in ["challenger/challenger.py"] if os.path.exists(os.path.join(ROOT, p))]
    fp = [p for p in rel(GROUPS["zoo"] + GROUPS["sparring"] + GROUPS["baselines"]) if p not in equity]
    return [
        ("self (should flag)", ["agent.py"]),
        ("near-relative", ["demon/demon.py"]),
        ("equity family: cousins + mc_grinder + equity_caller", equity),
        ("independent", challenger),
        ("non-equity bots = false-positive set", fp),
    ]


def _half(job):
    opp, seed, deals = job
    me = _load(os.path.join(ROOT, "agent.py"), "me")
    mod = _load(os.path.join(ROOT, opp), "opp")
    oov = ON if os.path.basename(opp) == "agent.py" else {}
    _, a, _ = play_half(me, ON, mod, oov, seed, 1 + int(seed[-1]) % 2, deals, AgentConfig(num_hands=deals))
    st = mirror.status(a.memory)
    st["errors"] = a.errors + len(a.memory.get("errors", []))
    return opp, st


def _pots(job):
    ov, seed, deals = job
    me = _load(os.path.join(ROOT, "agent.py"), "me")
    config = AgentConfig(num_hands=deals)
    a, b = Player(me, ov, config), Player(me, ov, config)
    tot = raises = acts = 0
    for d in range(deals):
        g = Game(make_deal(seed, d), button_for_deal(d), hand_index=d)
        while not g.is_terminal:
            seat = g.to_act
            g.apply((a, b)[seat].act(g.observation(seat)))
        for seat in (0, 1):
            (a, b)[seat].hand_end(g.hand_result(seat))
        tot += g.result().pot
        raises += sum(r.action in RAISE_ACTIONS for r in g.history)
        acts += len(g.history)
    flags = sum(mirror.status(p.memory)["state"] == "mirror" for p in (a, b))
    return bool(ov), tot / deals, raises / max(acts, 1), flags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--deals", type=int, default=1000)
    ap.add_argument("--jobs", type=int, default=2)
    args = ap.parse_args()
    sets = opponent_sets()
    jobs = [(o, f"mt{s}", args.deals) for _, opps in sets for o in opps for s in range(args.seeds)]
    pot_jobs = [(ov, f"pot{s}", args.deals) for ov in ({}, ON) for s in range(args.seeds)]
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(_half, jobs))
        pot_results = list(pool.map(_pots, pot_jobs))
    by_opp = {}
    for opp, st in results:
        by_opp.setdefault(opp, []).append(st)

    print(f"agent.py@mirror=1, {args.seeds} halves x {args.deals} deals per opponent\n")
    print(f"{'opponent':26} {'flagged':>8} {'kind':>12} {'at hand':>8} {'agree':>6} {'replays':>7} {'det ms':>7} {'err':>4}")
    for title, opps in sets:
        print(f"-- {title}")
        tot = flagged = 0
        for opp in opps:
            sts = by_opp[opp]
            fl = [x for x in sts if x["state"] in ("mirror", "reverted")]
            tot += len(sts)
            flagged += len(fl)
            kinds = ",".join(sorted({x["kind"] for x in fl})) or "-"
            hands = [x["flag_hand"] for x in fl]
            agree = sum(x["agree"] for x in sts) / max(1, sum(x["decisions"] for x in sts))
            print(f"{os.path.basename(opp)[:26]:26} {len(fl):3d}/{len(sts):<4d} {kinds:>12} "
                  f"{statistics.median(hands) if hands else float('nan'):8.0f} {agree:6.3f} "
                  f"{statistics.mean(x['decisions'] for x in sts):7.0f} "
                  f"{1000 * statistics.mean(x['spent'] for x in sts):7.1f} {sum(x['errors'] for x in sts):4d}")
        print(f"   => flagged {flagged}/{tot} halves\n")

    for on in (False, True):
        rs = [r for r in pot_results if r[0] == on]
        print(f"agent.py vs agent.py, both detectors {'on ' if on else 'off'}: "
              f"avg pot {statistics.mean(r[1] for r in rs):.2f} chips, raise share {statistics.mean(r[2] for r in rs):.3f}, "
              f"detectors flagged {sum(r[3] for r in rs)}/{2 * len(rs)}")


if __name__ == "__main__":
    main()
