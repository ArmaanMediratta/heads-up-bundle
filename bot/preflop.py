"""
preflop.py - the precomputed starting-hand table (see dev/build_preflop_table.py).

EQ[i]  equity vs a random hand of the hand at fasteval.HAND_MASKS[i]
PCT[i] that hand's strength percentile among all 376,992 hands (0 worst, 1 best)
"""

import os

import numpy as np

from bot import fasteval as F

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "preflop.npz")

EQ = np.load(_PATH)["eq"].astype(np.float64)
_order = np.argsort(EQ, kind="stable")
PCT = np.empty(len(EQ))
PCT[_order] = np.arange(len(EQ)) / (len(EQ) - 1)


def strength(hole) -> tuple[float, float]:
    """(equity vs random, percentile) of 5 hole cards."""
    i = int(F.hand_index(np.sort(np.asarray(hole, dtype=np.intp))[None, :])[0])
    return float(EQ[i]), float(PCT[i])
