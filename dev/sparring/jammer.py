"""Jammer: with the top ~30% of hands it keeps re-raising the pot preflop
(at 40bb that gets all-in fast); otherwise it folds / checks. Probes: our
all-in calling thresholds in big pots."""

from _spar_common import (THREE_OF_A_KIND, Action, Street, check_or_fold, hand_pct, made_category,
                          raise_or_call)


def new_half(config, memory):
    pass


def choose_action(obs, memory):
    jam = hand_pct(obs.hole_cards) >= 0.7
    if obs.street == Street.PREFLOP:
        return raise_or_call(obs, Action.RAISE_POT) if jam else check_or_fold(obs)
    if jam or made_category(obs) >= THREE_OF_A_KIND:
        return raise_or_call(obs, Action.RAISE_POT)
    return check_or_fold(obs)


def on_hand_end(result, memory):
    pass
