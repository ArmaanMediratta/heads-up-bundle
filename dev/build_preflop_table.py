"""
build_preflop_table.py - offline: equity vs a random hand for every Short
Deck PLO5 starting hand, written to bot/data/preflop.npz.

All C(36,5) = 376,992 hands are grouped into suit-isomorphic classes
(hands equal up to relabelling suits). One representative per class gets a
Monte Carlo equity, and every hand inherits its class value. The output
array is indexed like bot.fasteval.HAND_MASKS.

Run once from the repo root (takes about a minute):
    python dev/build_preflop_table.py [--samples 4000] [--seed 0]
"""

import argparse
import itertools
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from bot import fasteval as F  # noqa: E402
from bot.equity import _batch  # noqa: E402


def canonical_classes(hands: np.ndarray) -> np.ndarray:
    """Class id for each hand (N, 5): min over the 24 suit relabellings."""
    ranks, suits = hands >> 2, hands & 3
    best = None
    for perm in itertools.permutations(range(4)):
        relabelled = np.sort(ranks * 4 + np.array(perm)[suits], axis=1)
        key = (relabelled * (36 ** np.arange(5))).sum(axis=1)
        best = key if best is None else np.minimum(best, key)
    _, inverse = np.unique(best, return_inverse=True)
    return inverse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=4000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    start = time.perf_counter()
    hands = np.array(list(itertools.combinations(range(36), 5)), dtype=np.intp)
    hands = hands[np.argsort(F.hand_index(hands))]  # same order as HAND_MASKS
    classes = canonical_classes(hands)
    n_classes = classes.max() + 1
    print(f"{len(hands)} hands, {n_classes} suit classes ({time.perf_counter() - start:.1f}s)")

    reps = np.zeros(n_classes, dtype=np.intp)
    reps[classes] = np.arange(len(hands))
    rng = np.random.default_rng(args.seed)
    class_eq = np.zeros(n_classes)
    for c in range(n_classes):
        win, _, _, _ = _batch(hands[reps[c]].tolist(), [], args.samples, rng, None)
        class_eq[c] = win.mean()
        if c % 2000 == 0:
            print(f"  class {c}/{n_classes} ({time.perf_counter() - start:.0f}s)")

    eq = class_eq[classes].astype(np.float32)
    out = os.path.join(ROOT, "bot", "data", "preflop.npz")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    np.savez_compressed(out, eq=eq)
    print(f"wrote {out}: eq range {eq.min():.3f}-{eq.max():.3f}, mean {eq.mean():.3f} "
          f"({time.perf_counter() - start:.0f}s)")


if __name__ == "__main__":
    main()
