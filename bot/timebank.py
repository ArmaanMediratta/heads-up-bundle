"""
timebank.py - our own accounting of the judge's per-half thinking bank.

The judge charges every request's time beyond a 1 ms grace. We measure our
own hook time with perf_counter, add a per-request overhead allowance for
the server plumbing, and hand out a per-decision budget that leaves a wide
safety margin for a slower tournament CPU.
"""

import time

OVERHEAD_PER_REQUEST = 0.0004   # assumed JSON/HTTP handling cost we can't measure
GRACE = 0.001                   # the judge doesn't charge the first 1 ms of each request
SAFETY_FRACTION = 0.5           # only plan to spend this share of what is left
MAX_DECISION = 0.015            # hard cap per decision (far below the 1 s limit)
MIN_DECISION = 0.0004
PANIC_SECONDS = 0.6             # below this, use one minimum-size rollout (fits in the grace)


def init(memory: dict, bank_seconds: float, num_hands: int) -> None:
    memory["tb_bank"] = float(bank_seconds)
    memory["tb_spent"] = 0.0
    memory["tb_hands"] = int(num_hands)
    memory["tb_decisions"] = 0


def charge(memory: dict, seconds: float) -> None:
    # Conservative: on_hand_end usually shares a request with choose_action, but
    # we charge each hook as if it paid its own overhead.
    memory["tb_spent"] += max(0.0, seconds + OVERHEAD_PER_REQUEST - GRACE)


def left(memory: dict) -> float:
    return memory["tb_bank"] - memory["tb_spent"]


def panic(memory: dict) -> bool:
    return left(memory) < PANIC_SECONDS


def budget(memory: dict, hand_index: int) -> float:
    """Seconds this decision may spend on simulation."""
    memory["tb_decisions"] += 1
    hands_done = max(hand_index, 1)
    per_hand = max(memory["tb_decisions"] / hands_done, 1.5)
    decisions_left = max((memory["tb_hands"] - hand_index) * per_hand, 1.0)
    share = SAFETY_FRACTION * left(memory) / decisions_left
    return min(MAX_DECISION, max(MIN_DECISION, share))


def now() -> float:
    return time.perf_counter()
