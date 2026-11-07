"""
fasteval.py - vectorised Short Deck Omaha hand scoring with numpy.

The key table is PT[pair, triple]: the 5-card score of a hole-card pair
(one of C(36,2) = 630) plus a board triple (one of C(36,3) = 7140), or -1
when they share a card. An Omaha hand is then the max of PT over its 10 hole
pairs x 10 board triples, which numpy does for a whole batch in one gather.

Scores are exactly evaluator.py's scores (built from evaluator.get_table()),
so they compare the same way the judge's omaha_score does.
"""

from itertools import combinations

import numpy as np

from evaluator import NUM_CARDS, get_table

PAIRS5 = np.array(list(combinations(range(5), 2)), dtype=np.intp)    # (10, 2)
TRIPLES5 = np.array(list(combinations(range(5), 3)), dtype=np.intp)  # (10, 3)

BIT = np.uint64(1) << np.arange(NUM_CARDS, dtype=np.uint64)


def _build():
    table = get_table()
    masks = np.fromiter(table.keys(), dtype=np.uint64, count=len(table))
    scores = np.fromiter(table.values(), dtype=np.int32, count=len(table))
    order = np.argsort(masks)
    hand_masks, hand_scores = masks[order], scores[order]

    pairs = list(combinations(range(NUM_CARDS), 2))
    triples = list(combinations(range(NUM_CARDS), 3))
    pair_idx = np.full((NUM_CARDS, NUM_CARDS), -1, dtype=np.intp)
    for i, (a, b) in enumerate(pairs):
        pair_idx[a, b] = pair_idx[b, a] = i
    trip_idx = np.full((NUM_CARDS,) * 3, -1, dtype=np.intp)
    for i, (a, b, c) in enumerate(triples):
        for x, y, z in ((a, b, c), (a, c, b), (b, a, c), (b, c, a), (c, a, b), (c, b, a)):
            trip_idx[x, y, z] = i

    pair_masks = BIT[np.array(pairs)].sum(axis=1, dtype=np.uint64)
    trip_masks = BIT[np.array(triples)].sum(axis=1, dtype=np.uint64)
    union = pair_masks[:, None] | trip_masks[None, :]
    pos = np.searchsorted(hand_masks, union)
    np.minimum(pos, len(hand_masks) - 1, out=pos)
    pt = hand_scores[pos]
    pt[(pair_masks[:, None] & trip_masks[None, :]) != 0] = -1
    return hand_masks, pair_idx, trip_idx, pt


HAND_MASKS, PAIR_IDX, TRIP_IDX, PT = _build()


def hole_pairs(hole) -> np.ndarray:
    """Pair indices of 5 hole cards: shape (..., 10). Works on (5,) or (N, 5)."""
    h = np.asarray(hole)
    return PAIR_IDX[h[..., PAIRS5[:, 0]], h[..., PAIRS5[:, 1]]]


def board_triples(board) -> np.ndarray:
    """Triple indices of the 3-card combos of a board: (..., C(len,3))."""
    b = np.asarray(board)
    combos = np.array(list(combinations(range(b.shape[-1]), 3)), dtype=np.intp)
    return TRIP_IDX[b[..., combos[:, 0]], b[..., combos[:, 1]], b[..., combos[:, 2]]]


def board5_triples(boards: np.ndarray) -> np.ndarray:
    """Triple indices for a batch of full boards (N, 5) -> (N, 10)."""
    return TRIP_IDX[boards[:, TRIPLES5[:, 0]], boards[:, TRIPLES5[:, 1]], boards[:, TRIPLES5[:, 2]]]


def best_score(pairs: np.ndarray, triples: np.ndarray) -> np.ndarray:
    """Max of PT over pairs x triples. pairs (N, P) or (P,), triples (N, T) or (T,)."""
    if pairs.ndim == 1:
        pairs = pairs[None, :]
    if triples.ndim == 1:
        triples = triples[None, :]
    return PT[pairs[:, :, None], triples[:, None, :]].max(axis=(1, 2))


def hand_index(cards: np.ndarray) -> np.ndarray:
    """Position of each 5-card set (N, 5) in HAND_MASKS (indexes per-hand tables)."""
    masks = BIT[cards].sum(axis=-1, dtype=np.uint64)
    return np.searchsorted(HAND_MASKS, masks)
