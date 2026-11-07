"""TAG: tight-aggressive table player. Raises good starting hands, bets made
hands on the river, calls draws cheaply, folds weak hands to big bets."""

from _common import Action, Street, made_category, preflop, raise_if_legal


def new_half(config, memory):
    pass


def choose_action(obs, memory):
    eq, pct = preflop.strength(obs.hole_cards)
    pot_odds = obs.to_call / (obs.pot + obs.to_call) if obs.to_call else 0.0
    if obs.street == Street.PREFLOP:
        if pct > 0.7:
            return raise_if_legal(obs)
        if pct > 0.35 and pot_odds < 0.35:
            return Action.CHECK_CALL
        return Action.CHECK_CALL if obs.to_call == 0 else Action.FOLD
    cat = made_category(obs)
    if cat >= 5 or (cat < 0 and eq > 0.6):
        return raise_if_legal(obs, Action.RAISE_HALF)
    if cat >= 3 or (cat < 0 and pot_odds < 0.3) or obs.to_call == 0:
        return Action.CHECK_CALL
    return Action.FOLD


def on_hand_end(result, memory):
    pass
