"""
mirror.py - notice an opponent that plays our own strategy, then switch.

Off unless PARAMS["mirror"] is 1. Every half starts on the default strategy.

Watch. At each showdown the opponent's hole cards are revealed. We rebuild
the hand with the game engine from what we saw (our cards, the board, their
cards, the action history; their hand-ending action is a check/call at a
showdown and a fold when we won without one) and ask OUR policy what it
would have done in each of the opponent's spots, from the opponent's seat.
A "shadow" opponent model - what a copy of us in their seat would have
learned about us - is kept up to date on every hand, so the replayed policy
sees the same frequencies a real copy would. Replays use a small rollout
(256 samples), about 0.5 ms each.

Decide. Two sequential probability ratio tests (Wald SPRT) on "same action
as our policy would pick", one Bernoulli trial per replayed decision, with
separate rates preflop and postflop (preflop agreement is much noisier):
    exact   a copy of us            vs anything else      (pre + post trials)
    family  a Monte-Carlo-equity /  vs dissimilar bots    (postflop trials only)
            EV cousin of us
A test accepts when its log-likelihood ratio reaches log(1/ALPHA) and
rejects at log(BETA). We flag "mirror" when either accepts (exact first),
after MIN_HANDS hands, MIN_SHOWDOWNS showdowns and MIN_DECISIONS replays,
and only if a coarse action-frequency check on our opponent model
(bot/opponent.py) also looks like our family. We clear the opponent once
the family test rejects. Once decided nothing more is replayed. Replay stops,
undecided, if the time bank runs low or the detector used its own budget.
Rates are measured in-repo (research_notes/Mirror opponent detection and
counters/detection_experiments.md): same-action agreement with 256-sample
replays, preflop / postflop:
    agent.py 0.70 / 0.94   demon 0.56 / 0.85   mc_grinder 0.49 / 0.77
    tag 0.44 / 0.60   nit 0.51 / 0.49   maniac 0.31 / 0.32   baselines <= 0.33

Switch. On a flag, memory["params"] is updated with MIRROR_COUNTER. The
counter must stay a strategy (never passive or "friendly"): two copies that
both detect each other must keep playing real poker.

Guardrail. After switching we track our net per hand; if it is clearly
negative (mean below -REVERT_Z standard errors after REVERT_MIN hands) the
saved default params come back and we never switch again this half.
"""

import math

from bot import opponent, policy, timebank
from game import Action, Deal, Game, RAISE_ACTIONS, Street

# Counter-strategy bundle: PARAMS overrides applied once the opponent is flagged.
# Placeholder until the counter is chosen (empty = keep playing the default).
MIRROR_COUNTER: dict = {}

REPLAY_SAMPLES = 256    # rollout size for each replayed opponent decision
# (agree prob if H1, agree prob if H0) per street class: 0 preflop, 1 postflop
EXACT_P = ((0.66, 0.50), (0.93, 0.80))
FAMILY_P = (None, (0.74, 0.58))   # preflop ignored: cousins differ most there
ALPHA = 0.001           # tolerated false "mirror" rate
BETA = 0.01             # tolerated missed mirrors
MIN_SHOWDOWNS = 15      # never accept before this many showdowns...
MIN_DECISIONS = 20      # ...replayed decisions...
MIN_HANDS = 150         # ...or hands
MAX_REPLAYS_PER_HAND = 3  # bound the work of one on_hand_end call
MAX_SHOWDOWNS = 200     # give up (stay default) after this many
BUDGET_SECONDS = 0.35   # detector time cap per half
MIN_BANK_LEFT = 2.0     # skip replays when the time bank has less than this left
REVERT_MIN = 100        # hands after the switch before the guardrail may act
REVERT_Z = 2.0          # revert when post-switch mean net < -REVERT_Z standard errors

# Action-frequency envelope of our own bot as seen by a copy of it (pf raise,
# post raise rates from bot/opponent.py); generous, it only vetoes clear misfits.
FP_PF_RAISE = (0.25, 0.75)
FP_POST_RAISE = (0.15, 0.55)



def _llr_table(ps):
    return tuple(None if p is None else (math.log(p[0] / p[1]), math.log((1 - p[0]) / (1 - p[1])))
                 for p in ps)


_EXACT = _llr_table(EXACT_P)
_FAMILY = _llr_table(FAMILY_P)
_ACCEPT = math.log(1.0 / ALPHA)
_REJECT = math.log(BETA)


def init(memory: dict) -> None:
    memory["mirror"] = {
        "state": "watch",       # watch | mirror | clear | stopped | reverted
        "kind": "",             # "exact" or "family" once flagged
        "llr": 0.0, "llr_family": 0.0, "decisions": 0, "agree": 0, "showdowns": 0,
        "flag_hand": -1, "spent": 0.0, "skipped": 0,
        "hand": -1, "hole": (), "is_button": False, "history": (), "last": None,
        "shadow": None,         # the opponent's model of us, built on first use
        "saved_params": None,
        "post_n": 0, "post_sum": 0.0, "post_sq": 0.0,
    }


def enabled(memory: dict) -> bool:
    return bool(memory.get("params", {}).get("mirror", 0)) and "mirror" in memory


def note_decision(obs, action, memory: dict) -> None:
    """Remember what we saw and did (the last call of a hand is what hand_end needs)."""
    m = memory["mirror"]
    if m["state"] != "watch":
        return
    m["hand"] = obs.hand_index
    m["hole"] = obs.hole_cards
    m["is_button"] = obs.is_button
    m["history"] = obs.action_history
    m["last"] = action


def _shadow(memory: dict) -> dict:
    m = memory["mirror"]
    if m["shadow"] is None:
        params = dict(memory["params"])
        params["mirror"] = 0
        params["max_samples"] = REPLAY_SAMPLES
        params["mix_eps"] = 0.0
        sh = {"params": params, "np_rng": memory["np_rng"], "raise_cap": memory.get("raise_cap", 4),
              "last_eq": 0.5, "tb_bank": 1e9, "tb_spent": 0.0}
        opponent.init(sh)
        m["shadow"] = sh
    return m["shadow"]


def _fingerprint_ok(memory: dict) -> bool:
    pf, post = opponent.pf_raise_freq(memory), opponent.post_raise_freq(memory)
    return FP_PF_RAISE[0] <= pf <= FP_PF_RAISE[1] and FP_POST_RAISE[0] <= post <= FP_POST_RAISE[1]


def _replay(result, memory: dict, sd: bool) -> list:
    """Rebuild the hand (we are seat 0) and walk the opponent's decisions.
    Updates the shadow model; returns [(their action, our policy's action)] at showdown."""
    m = memory["mirror"]
    sh = _shadow(memory)
    acted = m["hand"] == result.hand_index
    if acted:
        hole, button = tuple(m["hole"]), 0 if m["is_button"] else 1
        seq = [(0 if a.is_me else 1, a.action) for a in m["history"]] + [(0, m["last"])]
    else:  # we never got a turn: the opponent (button) folded first
        hole, button, seq = None, 1, []
    board = list(result.board)
    used = set(hole or ()) | set(board) | set(result.opp_hole or ())
    spare = [c for c in range(36) if c not in used]
    if hole is None:
        hole, spare = tuple(sorted(spare[:5])), spare[5:]
    if sd:
        opp = tuple(sorted(result.opp_hole))
    else:
        opp, spare = tuple(sorted(spare[:5])), spare[5:]
    full_board = tuple(board + spare[:5 - len(board)])
    g = Game(Deal(hole_cards=(tuple(sorted(hole)), opp), board=full_board), button, hand_index=result.hand_index)
    pairs = []
    replay = sd and m["state"] == "watch"

    def opp_turn(action):
        obs = g.observation(1)
        opponent.observe(obs, sh)
        if replay and len(obs.legal_actions) > 1 and len(pairs) < MAX_REPLAYS_PER_HAND:
            ours = policy.decide(obs, sh, 0.0)
            pairs.append((action, ours, obs.raise_to, int(obs.street != Street.PREFLOP)))
        opponent.note_our_action(action, obs, sh)
        g.apply(action)

    for seat, action in seq:
        if g.is_terminal or g.to_act != seat:
            return []  # history doesn't fit the engine: skip this hand
        if seat == 1:
            opp_turn(action)
        else:
            g.apply(action)
    # the opponent's hand-ending action(s), never seen in a history
    while not g.is_terminal:
        if g.to_act != 1:
            return []
        opp_turn(Action.CHECK_CALL if sd else Action.FOLD)
    if g.result().nets[0] != result.my_net:
        return []  # reconstruction disagrees with the judge: don't trust it
    opponent.hand_end(g.hand_result(1), sh)
    return pairs


def _same(theirs, ours, raise_to) -> bool:
    if theirs == ours:
        return True
    # RAISE_HALF and RAISE_POT can be the same total (pot-limit / all-in caps)
    return (theirs in RAISE_ACTIONS and ours in RAISE_ACTIONS
            and raise_to.get(theirs) == raise_to.get(ours))


def hand_end(result, memory: dict) -> None:
    if not enabled(memory):
        return
    m = memory["mirror"]
    if m["state"] == "mirror":
        _guardrail(result, memory)
        return
    if m["state"] != "watch":
        return
    if timebank.left(memory) < MIN_BANK_LEFT or m["spent"] > BUDGET_SECONDS:
        m["state"] = "stopped"
        return
    start = timebank.now()
    sd = result.opp_hole is not None
    pairs = _replay(result, memory, sd)
    if sd:
        m["showdowns"] += 1
    for theirs, ours, rt, post in pairs:
        agree = _same(theirs, ours, rt)
        m["decisions"] += 1
        m["agree"] += agree
        m["llr"] += _EXACT[post][0 if agree else 1]
        if _FAMILY[post] is not None:
            m["llr_family"] += _FAMILY[post][0 if agree else 1]
    # never decide "mirror" on thin evidence; a rejection may come any time
    ready = (m["showdowns"] >= MIN_SHOWDOWNS and m["decisions"] >= MIN_DECISIONS
             and result.hand_index + 1 >= MIN_HANDS)
    if ready and m["llr"] >= _ACCEPT and _fingerprint_ok(memory):
        _switch(result, memory, "exact")
    elif ready and m["llr_family"] >= _ACCEPT and _fingerprint_ok(memory):
        _switch(result, memory, "family")
    elif m["llr_family"] <= _REJECT and m["llr"] < _ACCEPT:
        m["state"] = "clear"
    elif m["showdowns"] >= MAX_SHOWDOWNS:
        m["state"] = "clear"
    m["spent"] += timebank.now() - start


def _switch(result, memory: dict, kind: str = "exact") -> None:
    m = memory["mirror"]
    m["state"], m["kind"], m["flag_hand"] = "mirror", kind, result.hand_index
    m["saved_params"] = dict(memory["params"])
    memory["params"].update(MIRROR_COUNTER)


def _guardrail(result, memory: dict) -> None:
    m = memory["mirror"]
    x = float(result.my_net)
    m["post_n"] += 1
    m["post_sum"] += x
    m["post_sq"] += x * x
    n = m["post_n"]
    if n < REVERT_MIN:
        return
    mean = m["post_sum"] / n
    var = max(m["post_sq"] / n - mean * mean, 1e-9) * n / (n - 1)
    if mean / math.sqrt(var / n) < -REVERT_Z or not _fingerprint_ok(memory):
        memory["params"].clear()
        memory["params"].update(m["saved_params"])
        m["state"] = "reverted"


def status(memory: dict) -> dict:
    """Small summary for tests and dev scripts."""
    m = memory.get("mirror", {})
    return {k: m.get(k) for k in ("state", "kind", "llr", "llr_family", "decisions", "agree", "showdowns", "flag_hand", "spent")}
