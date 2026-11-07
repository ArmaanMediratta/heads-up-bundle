"""
leaks.py - show WHERE our bot wins and loses chips against an opponent.

Plays an in-process duplicate match (same deals twice, seats swapped, fresh
memory per half, judge-style time bank and error rules via dev/harness.py)
and breaks the result down from our bot's point of view:

  * bb/deal with a 95% interval (paired, like the judge)
  * chips by how each hand ended (we folded on street X facing Y, they
    folded, showdown won/lost) and by position
  * our action frequencies per street, facing a bet vs not
  * the biggest losing hands, with cards and the full action line

    python dev/leaks.py --opp dev/sparring/stabber.py
    python dev/leaks.py --opp sparring --deals 1000 --seeds 2 --worst 15
"""

import argparse
import math
import os
import statistics
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

from harness import GROUPS, Player, _load, _parse  # noqa: E402

from evaluator import cards_to_str  # noqa: E402
from game import (BIG_BLIND, CHOP_Z, NUM_DEALS, RAISE_ACTIONS, TIME_BANK_SECONDS, Action,  # noqa: E402
                  AgentConfig, Game, Street, button_for_deal, make_deal)

SHORT = {Action.FOLD: "F", Action.CHECK_CALL: "C", Action.RAISE_HALF: "h", Action.RAISE_POT: "P"}


def facing(obs) -> str:
    """What our bot is facing at a decision: 'bet' if it must call, else 'none'."""
    if obs.to_call == 0:
        return "none"
    last = next((a for a in reversed(obs.action_history) if not a.is_me), None)
    if last is None or obs.street == Street.PREFLOP and obs.raises_this_street == 0:
        return "blind"
    return "pot" if last.action == Action.RAISE_POT else "half"


def play_half(mod_a, mod_b, seed, half, deals, config, decisions, hands):
    a, b = Player(mod_a, {}, config), Player(mod_b, {}, config)
    seats = (a, b) if half == 1 else (b, a)
    me = 0 if half == 1 else 1
    nets = []
    for d in range(deals):
        deal = make_deal(str(seed), d)
        game = Game(deal, button_for_deal(d), hand_index=d)
        last_my_facing = None
        while not game.is_terminal:
            seat = game.to_act
            obs = game.observation(seat)
            action = seats[seat].act(obs)
            if seat == me:
                last_my_facing = facing(obs)
                decisions.append((obs.street, last_my_facing, action))
            game.apply(action)
        for s in (0, 1):
            seats[s].hand_end(game.hand_result(s))
        res = game.result()
        last = res.history[-1]
        if not res.went_to_showdown:
            ended = (f"we folded {last.street.name.lower()} vs {last_my_facing}" if last.seat == me
                     else f"they folded {last.street.name.lower()}")
        else:
            ended = ("showdown split" if res.winner_seat is None
                     else "showdown won" if res.winner_seat == me else "showdown lost")
        line = " | ".join(
            "".join(("us:" if r.seat == me else "op:") + SHORT[r.action] + " " for r in res.history if r.street == st).strip()
            for st in Street if any(r.street == st for r in res.history))
        hands.append({
            "net": res.nets[me], "ended": ended, "button": game.button_seat == me, "seed": seed,
            "half": half, "deal": d, "me": cards_to_str(deal.hole_cards[me]),
            "opp": cards_to_str(deal.hole_cards[1 - me]), "board": cards_to_str(res.board_revealed),
            "line": line,
        })
        nets.append(res.nets[me])
    return nets, a, b


def report(bot_spec, opp_spec, deals, seeds, bank, worst):
    (pa, _), (pb, _) = _parse(bot_spec), _parse(opp_spec)
    mod_a, mod_b = _load(pa, "a"), _load(pb, "b")
    config = AgentConfig(num_hands=deals, time_bank_seconds=bank)
    decisions, hands, paired = [], [], []
    errors = skipped = opp_errors = opp_skipped = 0
    spend = 0.0
    for s in range(seeds):
        seed = f"leak{s}"
        n1, a1, b1 = play_half(mod_a, mod_b, seed, 1, deals, config, decisions, hands)
        n2, a2, b2 = play_half(mod_a, mod_b, seed, 2, deals, config, decisions, hands)
        paired += [(x + y) / BIG_BLIND for x, y in zip(n1, n2)]
        errors += a1.errors + a2.errors
        skipped += a1.skipped + a2.skipped
        opp_errors += b1.errors + b2.errors
        opp_skipped += b1.skipped + b2.skipped
        spend = max(spend, a1.spent, a2.spent)

    mean = statistics.fmean(paired)
    se = statistics.stdev(paired) / math.sqrt(len(paired))
    n_deals = len(paired)
    print(f"\n=== {os.path.basename(bot_spec)} vs {os.path.basename(opp_spec)}  "
          f"({deals} deals x {seeds} seeds) ===")
    print(f"bb/deal {mean:+.3f}  95% CI [{mean - CHOP_Z * se:+.3f}, {mean + CHOP_Z * se:+.3f}]   "
          f"our errors {errors}, time-bank skips {skipped}, max spend {spend:.2f}s/{bank:.0f}s")
    if opp_errors or opp_skipped:
        print(f"WARNING: opponent had {opp_errors} errors and {opp_skipped} time-bank skips; "
              f"results overstate us")

    print("\nHow hands ended (our chips, in bb per deal; sorted worst first):")
    by_end = defaultdict(lambda: [0, 0.0])
    for h in hands:
        by_end[h["ended"]][0] += 1
        by_end[h["ended"]][1] += h["net"] / BIG_BLIND
    for k, (cnt, bb) in sorted(by_end.items(), key=lambda kv: kv[1][1]):
        print(f"  {k:32} {cnt:6d} hands  {100 * cnt / len(hands):5.1f}%   {bb / n_deals:+7.3f} bb/deal")

    print("\nBy position (bb per deal):")
    for pos in (True, False):
        hs = [h for h in hands if h["button"] == pos]
        print(f"  {'button / SB' if pos else 'big blind':12} {sum(h['net'] for h in hs) / BIG_BLIND / n_deals:+7.3f}")

    print("\nOur action frequencies (%):")
    print(f"  {'street':8} {'facing':6} {'n':>6} {'fold':>6} {'chk/call':>8} {'half':>6} {'pot':>6}")
    groups = defaultdict(lambda: defaultdict(int))
    for st, fc, act in decisions:
        groups[(st, fc)][act] += 1
    for (st, fc), counts in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        n = sum(counts.values())
        pct = {a: 100 * counts[a] / n for a in Action}
        print(f"  {st.name.lower():8} {fc:6} {n:6d} {pct[Action.FOLD]:6.1f} {pct[Action.CHECK_CALL]:8.1f} "
              f"{pct[Action.RAISE_HALF]:6.1f} {pct[Action.RAISE_POT]:6.1f}")

    if worst:
        print(f"\nBiggest {worst} losing hands (F=fold C=check/call h=half-pot raise P=pot raise):")
        for h in sorted(hands, key=lambda h: h["net"])[:worst]:
            print(f"  {h['net'] / BIG_BLIND:+6.1f}bb {'BTN' if h['button'] else 'BB '} "
                  f"us [{h['me']}] opp [{h['opp']}] board [{h['board']}]  {h['ended']}")
            print(f"           {h['line']}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bot", default="agent.py")
    p.add_argument("--opp", nargs="+", required=True, help="bot paths and/or groups: baselines, zoo, sparring")
    p.add_argument("--deals", type=int, default=NUM_DEALS)
    p.add_argument("--seeds", type=int, default=1)
    p.add_argument("--bank", type=float, default=TIME_BANK_SECONDS)
    p.add_argument("--worst", type=int, default=10, help="how many biggest losing hands to list")
    args = p.parse_args()
    for o in args.opp:
        for path in GROUPS.get(o, [o]):
            report(args.bot, path, args.deals, args.seeds, args.bank, args.worst)


if __name__ == "__main__":
    main()
