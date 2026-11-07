"""Flush hunter: only plays suited hands, chases flush draws, raises big with
flushes, and folds full houses / trips when a flush is possible. Probes:
short-deck ranking mistakes (flush > full house, trips > straight) and
whether our bot can bluff scary boards."""

from _spar_common import (FLUSH, FULL_HOUSE, Action, Street, board_flush_possible, card_suit,
                          check_or_fold, flush_draw, hand_pct, made_category, pot_odds, raise_or_call)


def new_half(config, memory):
    pass


def _suited(hole):
    suits = [card_suit(c) for c in hole]
    return max(suits.count(s) for s in set(suits)) >= 2


def choose_action(obs, memory):
    if obs.street == Street.PREFLOP:
        if not _suited(obs.hole_cards):
            return check_or_fold(obs)
        pct = hand_pct(obs.hole_cards)
        if pct > 0.75:
            return raise_or_call(obs, Action.RAISE_HALF)
        return Action.CHECK_CALL if pct > 0.25 and pot_odds(obs) < 0.4 else check_or_fold(obs)
    cat = made_category(obs)
    if cat >= FLUSH:
        return raise_or_call(obs, Action.RAISE_POT)
    if flush_draw(obs.hole_cards, obs.board):
        if obs.to_call == 0:
            return raise_or_call(obs, Action.RAISE_HALF)    # semi-bluff
        return Action.CHECK_CALL if pot_odds(obs) < 0.4 else Action.FOLD
    if board_flush_possible(obs.board):
        return check_or_fold(obs)                           # scared of the flush, even with a full house
    if cat >= FULL_HOUSE:
        return raise_or_call(obs, Action.RAISE_HALF)
    return check_or_fold(obs)


def on_hand_end(result, memory):
    pass
