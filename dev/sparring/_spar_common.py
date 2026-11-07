"""Shared helpers for the sparring bots in dev/sparring.

Deliberately independent of bot/: everything here is built only from the
rules (game.py) and the hand evaluator (evaluator.py), so these opponents do
not share our bot's hand-strength model or its blind spots.
"""

import bisect
import os
import random
import sys
import time
from itertools import combinations

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from evaluator import (FLUSH, FULL_HOUSE, NUM_CARDS, STRAIGHT, THREE_OF_A_KIND,  # noqa: E402,F401
                       TWO_PAIR, card_rank, card_suit, category_of, get_table, omaha_score)
from game import RAISE_ACTIONS, Action, Street  # noqa: E402,F401

# ---------------------------------------------------------------------------
# Preflop: a hand-made heuristic, calibrated to a percentile at import time
# ---------------------------------------------------------------------------


def _two_card_value(a: int, b: int) -> float:
    ra, rb = card_rank(a), card_rank(b)
    hi, lo = max(ra, rb), min(ra, rb)
    v = (hi + lo) / 16.0                      # high cards, 0..1
    if ra == rb:
        v += 0.6 + hi / 16.0                  # pocket pair, bigger = better
    else:
        gap = hi - lo
        wheel = hi == 8 and lo <= 3           # A with 6-9 makes the A-6-7-8-9 wheel
        if gap <= 4 or wheel:
            v += 0.25 - 0.04 * (gap if not wheel else 2)
    if card_suit(a) == card_suit(b) and ra != rb:
        v += 0.35 + hi / 40.0                 # flushes beat full houses in short deck
    return v


def raw_hand_score(hole) -> float:
    vals = sorted((_two_card_value(a, b) for a, b in combinations(hole, 2)), reverse=True)
    suits = [card_suit(c) for c in hole]
    ranks = [card_rank(c) for c in hole]
    penalty = 0.0
    if max(suits.count(s) for s in set(suits)) >= 4:
        penalty += 0.3                        # 4+ of a suit kills your own flush outs
    if max(ranks.count(r) for r in set(ranks)) >= 3:
        penalty += 0.4                        # trips in hand: only 2 can be used
    return vals[0] + 0.5 * vals[1] + 0.25 * vals[2] - penalty


_rng = random.Random(12345)
_CALIBRATION = sorted(raw_hand_score(_rng.sample(range(NUM_CARDS), 5)) for _ in range(4000))


def hand_pct(hole) -> float:
    """Preflop strength as a percentile 0..1 among random 5-card hands."""
    return bisect.bisect_left(_CALIBRATION, raw_hand_score(hole)) / len(_CALIBRATION)


# ---------------------------------------------------------------------------
# Postflop
# ---------------------------------------------------------------------------


def mc_equity(hole, board, iters: int = 40, budget_s: float = 0.003, rng=random) -> float:
    """Monte-Carlo equity vs one random 5-card hand. Stops early at budget_s."""
    dead = set(hole) | set(board)
    deck = [c for c in range(NUM_CARDS) if c not in dead]
    need = 5 - len(board)
    start = time.perf_counter()
    wins = n = 0.0
    for _ in range(iters):
        draw = rng.sample(deck, 5 + need)
        full = list(board) + draw[5:]
        me, opp = omaha_score(hole, full), omaha_score(draw[:5], full)
        wins += 1.0 if me > opp else 0.5 if me == opp else 0.0
        n += 1
        if time.perf_counter() - start > budget_s:
            break
    return wins / n if n else 0.5


def best_score(hole, board) -> int:
    """Best exactly-2-hole + exactly-3-board score for a 3, 4 or 5 card board."""
    if len(board) == 5:
        return omaha_score(hole, board)
    table = get_table()
    hole_masks = [(1 << a) | (1 << b) for a, b in combinations(hole, 2)]
    board_masks = [(1 << a) | (1 << b) | (1 << c) for a, b, c in combinations(board, 3)]
    return max(table[h | b] for h in hole_masks for b in board_masks)


def made_category(obs) -> int:
    """Best made-hand category right now (needs 3+ board cards), else -1."""
    if len(obs.board) < 3:
        return -1
    return category_of(best_score(obs.hole_cards, obs.board))


def flush_draw(hole, board) -> bool:
    """True if two hole cards of one suit plus exactly two board cards of it (needs 1 more)."""
    if len(board) >= 5:
        return False
    for s in range(4):
        if sum(card_suit(c) == s for c in hole) >= 2 and sum(card_suit(c) == s for c in board) == 2:
            return True
    return False


def board_flush_possible(board) -> bool:
    """3+ board cards share a suit, so someone could hold a flush."""
    return any(sum(card_suit(c) == s for c in board) >= 3 for s in range(4))


def pot_odds(obs) -> float:
    return obs.to_call / (obs.pot + obs.to_call) if obs.to_call else 0.0


def raise_or_call(obs, action=Action.RAISE_POT):
    if action in obs.legal_actions:
        return action
    for a in RAISE_ACTIONS:
        if a in obs.legal_actions:
            return a
    return Action.CHECK_CALL


def check_or_fold(obs):
    return Action.CHECK_CALL if obs.to_call == 0 else Action.FOLD


def opp_raised_this_street(obs) -> bool:
    return any((not a.is_me) and a.street == obs.street and a.action in RAISE_ACTIONS
               for a in obs.action_history)
