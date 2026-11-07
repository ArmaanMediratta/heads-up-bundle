"""
demon_lab.py - evaluate, tune and train demon.py (in-process, judge-like scoring).

    python dev/demon_lab.py eval  --opp agent.py --seeds 6              # demon vs agent.py
    python dev/demon_lab.py eval  --expert sheriff --opp sparring
    python dev/demon_lab.py tune  --expert grinder --gens 6             # CEM on one expert's params
    python dev/demon_lab.py train --rounds 3 --seeds 8                  # Q-residual tables + meta prior

Every job plays a full duplicate match (both halves, seats swapped, fresh
memory per half) through dev/harness.py's play_half, so time banks, errors
and scoring follow the judge's rules.

Results are written to demon_data/demon_q.npz, which demon.py loads at import.
"""

import argparse
import json
import math
import os
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "dev"))

from game import BIG_BLIND, CHOP_Z, TIME_BANK_SECONDS, AgentConfig  # noqa: E402
from harness import GROUPS, _load, _parse, play_half  # noqa: E402

DATA = os.path.join(ROOT, "demon_data", "demon_q.npz")
DEMON = os.path.join(ROOT, "demon.py")
GROUPS = dict(GROUPS, agent=[os.path.join(ROOT, "agent.py")])

# params the tuner may move, with (low, high) bounds
TUNABLE = {
    "r_ip": (0.75, 1.05), "r_oop": (0.65, 1.0), "temp_pre": (0.03, 0.2), "temp_post": (0.05, 0.25),
    "max_cut": (0.6, 0.95), "widen": (0.7, 2.5), "call_cut_scale": (0.2, 1.0),
    "half_fold_scale": (0.5, 1.0), "fe_scale": (0.6, 1.6), "call_bonus": (-0.05, 0.12),
    "raise_bonus": (-0.05, 0.1), "trap": (0.0, 0.25), "trap_eq": (0.6, 0.95), "pf_open": (-0.05, 0.15),
    "defend": (0.0, 0.5), "sd_use": (0.0, 1.0),
}


def _expand(opps):
    out = []
    for o in opps:
        out.extend(GROUPS.get(o, [o]))
    return out


def _load_demon(env: dict, expert_override: dict | None, data_path: str | None):
    for k, v in env.items():
        os.environ[k] = str(v)
    if data_path is not None:
        os.environ["DEMON_DATA"] = data_path
    mod = _load(DEMON, f"demon{os.getpid()}{time.perf_counter_ns()}")
    if expert_override:
        for name, params in expert_override.items():
            mod.EXPERT_PARAMS[name].update(params)
    return mod


def job(spec):
    """One duplicate match. spec: dict(opp, seed, deals, env, experts, data, collect, samples_opp)."""
    np.random.seed(abs(hash(spec["seed"])) % 2**32)
    demon = _load_demon(spec.get("env", {}), spec.get("experts"), spec.get("data"))
    opp_path, opp_ov = _parse(spec["opp"])
    if spec.get("opp_samples") and os.path.basename(opp_path) in ("agent.py", "demon.py"):
        opp_ov = dict(opp_ov, max_samples=float(spec["opp_samples"]))
    if os.path.basename(opp_path) == "demon.py":
        opp = _load_demon({"DEMON_TRAIN": "0", "DEMON_EXPERT": ""}, None, spec.get("data"))
    else:
        opp = _load(opp_path, f"opp{os.getpid()}")
    config = AgentConfig(num_hands=spec["deals"], time_bank_seconds=spec.get("bank", TIME_BANK_SECONDS))
    n1, a1, _ = play_half(demon, {}, opp, opp_ov, spec["seed"], 1, spec["deals"], config)
    n2, a2, _ = play_half(demon, {}, opp, opp_ov, spec["seed"], 2, spec["deals"], config)
    paired = [(x + y) / BIG_BLIND for x, y in zip(n1, n2)]
    mean = sum(paired) / len(paired)
    sd = statistics.stdev(paired)
    se = sd / math.sqrt(len(paired))
    forfeit = a1.forfeited or a2.forfeited
    verdict = "LOSS" if forfeit else "WIN" if mean - CHOP_Z * se > 0 else "LOSS" if mean + CHOP_Z * se < 0 else "CHOP"
    out = {"opp": os.path.basename(opp_path), "seed": spec["seed"], "mean": mean, "sd": sd,
           "verdict": verdict, "errors": a1.errors + a2.errors,
           "spend": max(a1.spent, a2.spent), "tag": spec.get("tag")}
    if spec.get("collect"):
        out["log"] = a1.memory.get("log", []) + a2.memory.get("log", [])
        out["hand_log"] = a1.memory.get("hand_log", []) + a2.memory.get("hand_log", [])
    return out


def run_jobs(specs, workers):
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(job, specs))


def summarize(results, title=""):
    if title:
        print(title)
    print(f"{'opponent':28} {'bb/deal':>8} {'95% CI':>18} {'W-C-L':>7} {'err':>4} {'think':>6}")
    tot = 0.0
    for opp in sorted({r["opp"] for r in results}, key=lambda o: [r["opp"] for r in results].index(o)):
        rs = [r for r in results if r["opp"] == opp]
        m = sum(r["mean"] for r in rs) / len(rs)
        n = len(rs) * 1000
        se = math.sqrt(sum(r["sd"] ** 2 for r in rs) / len(rs)) / math.sqrt(n)
        wcl = [sum(r["verdict"] == v for r in rs) for v in ("WIN", "CHOP", "LOSS")]
        tot += wcl[0] + 0.5 * wcl[1]
        print(f"{opp[:28]:28} {m:+8.3f} [{m - 1.96 * se:+7.3f},{m + 1.96 * se:+7.3f}] "
              f"{'-'.join(map(str, wcl)):>7} {sum(r['errors'] for r in rs):4d} "
              f"{max(r['spend'] for r in rs):5.2f}s")
    print(f"points {tot:.1f}/{len(results)}  mean {sum(r['mean'] for r in results) / len(results):+.3f} bb/deal")


# ---------------------------------------------------------------------------
# data file helpers
# ---------------------------------------------------------------------------

def load_data():
    if os.path.exists(DATA):
        z = np.load(DATA, allow_pickle=False)
        return {k: z[k] for k in z.files}
    return {}


def save_data(d):
    os.makedirs(os.path.dirname(DATA), exist_ok=True)
    tmp = DATA + ".tmp.npz"
    np.savez_compressed(tmp, **d)
    os.replace(tmp, DATA)


def expert_params_from_data(d):
    sys.path.insert(0, ROOT)
    import demon  # noqa: F401  (module defaults)
    names = demon.EXPERT_NAMES
    params = {n: dict(demon.EXPERTS[n]) for n in names}
    if "expert_params" in d:
        keys = [str(k) for k in d["expert_keys"]]
        for e, n in enumerate(names):
            params[n].update({k: float(v) for k, v in zip(keys, d["expert_params"][e])})
    return names, params


def store_expert_params(d, names, params):
    keys = sorted(params[names[0]])
    d["expert_keys"] = np.array(keys)
    d["expert_params"] = np.array([[params[n][k] for k in keys] for n in names], dtype=np.float64)


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def cmd_eval(a):
    env = {"DEMON_TRAIN": "0", "DEMON_EXPERT": a.expert or "", "DEMON_SAMPLES": "1024"}
    experts = None
    if a.set:
        import demon
        ov = {k: float(v) for k, v in (kv.split("=") for kv in a.set.split(","))}
        experts = {n: dict(ov) for n in demon.EXPERT_NAMES}
    specs = [dict(opp=o, seed=f"e{a.seed_offset + s}", deals=a.deals, env=env, data=a.data,
                  bank=a.bank, experts=experts) for o in _expand(a.opp) for s in range(a.seeds)]
    t = time.time()
    res = run_jobs(specs, a.jobs)
    summarize(res, f"demon{'[' + a.expert + ']' if a.expert else ''} | {a.deals} deals x {a.seeds} seeds")
    print(f"({time.time() - t:.0f}s)")


def cmd_tune(a):
    """Cross-entropy method over one expert's parameters, common random seeds per generation."""
    d = load_data()
    names, params = expert_params_from_data(d)
    keys = [k for k in (a.keys.split(",") if a.keys else TUNABLE)]
    base = params[a.expert]
    mu = np.array([base[k] for k in keys])
    lo = np.array([TUNABLE[k][0] for k in keys])
    hi = np.array([TUNABLE[k][1] for k in keys])
    sigma = (hi - lo) * 0.18
    opps = _expand(a.opp)
    rng = np.random.default_rng(a.rng)
    env = {"DEMON_TRAIN": "0", "DEMON_EXPERT": a.expert, "DEMON_SAMPLES": str(a.samples)}
    best_score, best_vec = None, mu.copy()
    for gen in range(a.gens):
        cands = [mu.copy()] + [np.clip(mu + sigma * rng.standard_normal(len(mu)), lo, hi)
                               for _ in range(a.pop - 1)]
        seeds = [f"t{gen}_{s}_{a.rng}" for s in range(a.seeds)]
        specs = []
        for ci, c in enumerate(cands):
            ov = {a.expert: dict(zip(keys, map(float, c)))}
            for o in opps:
                for s in seeds:
                    specs.append(dict(opp=o, seed=s, deals=a.deals, env=env, experts=ov, data=a.data,
                                      tag=ci, opp_samples=a.samples))
        t = time.time()
        res = run_jobs(specs, a.jobs)
        scores = []
        for ci in range(len(cands)):
            per_opp = {}
            for r in res:
                if r["tag"] == ci:
                    per_opp.setdefault(r["opp"], []).append(r["mean"])
            # weighted mean over opponents (agent.py counts double: it's the target)
            tot = wsum = 0.0
            for o, ms in per_opp.items():
                wt = a.agent_weight if o == "agent.py" else 1.0
                tot += wt * sum(ms) / len(ms)
                wsum += wt
            scores.append(tot / wsum)
        order = np.argsort(scores)[::-1]
        elite = np.array([cands[i] for i in order[:a.elite]])
        print(f"gen {gen}: best {scores[order[0]]:+.3f} (cand {order[0]}), incumbent {scores[0]:+.3f}, "
              f"elite mean {np.mean([scores[i] for i in order[:a.elite]]):+.3f}  ({time.time() - t:.0f}s)")
        # keep the incumbent unless something clearly beat it on these seeds
        if scores[order[0]] > scores[0]:
            best_vec = cands[order[0]]
        best_score = scores[order[0]]
        mu = 0.5 * mu + 0.5 * elite.mean(axis=0)
        sigma = np.maximum(0.6 * sigma + 0.4 * elite.std(axis=0), (hi - lo) * 0.03)
        print("   mu:", {k: round(float(v), 3) for k, v in zip(keys, mu)})
    final = 0.5 * best_vec + 0.5 * mu if a.blend else mu
    params[a.expert].update({k: float(v) for k, v in zip(keys, final)})
    d = load_data()
    store_expert_params(d, names, params)
    save_data(d)
    print(f"saved {a.expert}:", json.dumps({k: round(v, 3) for k, v in params[a.expert].items()}))
    return best_score


def fit_residuals(logs, ridge, sweeps=25):
    """Backfitting ridge regression of residual returns on the one-hot lenses, per action."""
    sys.path.insert(0, ROOT)
    import demon
    L = np.asarray(logs, dtype=np.float64)
    nl = demon.NL
    keys = L[:, :nl].astype(np.int64)
    act = L[:, nl].astype(np.int64)
    base = L[:, nl + 1]
    g = L[:, nl + 2]
    target = np.clip(g - base, -demon.RESID_CLIP, demon.RESID_CLIP)
    theta = [np.zeros((n, demon.NA)) for n in demon.LENS_SIZE]
    count = [np.zeros((n, demon.NA)) for n in demon.LENS_SIZE]
    for i, n in enumerate(demon.LENS_SIZE):
        idx = keys[:, i] * demon.NA + act
        count[i] = np.bincount(idx, minlength=n * demon.NA).reshape(n, demon.NA).astype(np.float64)
    pred = np.zeros(len(L))
    contrib = [np.zeros(len(L)) for _ in range(nl)]
    for sweep in range(sweeps):
        for i, n in enumerate(demon.LENS_SIZE):
            idx = keys[:, i] * demon.NA + act
            partial = target - (pred - contrib[i])
            s = np.bincount(idx, weights=partial, minlength=n * demon.NA)
            c = np.bincount(idx, minlength=n * demon.NA)
            th = (s / (c + ridge)).reshape(n, demon.NA)
            theta[i] = th
            new = th.reshape(-1)[idx]
            pred += new - contrib[i]
            contrib[i] = new
    resid_var = float(np.mean((target - pred) ** 2))
    print(f"  fit: {len(L)} decisions, target var {float(np.var(target)):.2f} -> residual var {resid_var:.2f}")
    return theta, count


def cmd_train(a):
    """Rounds of: play (epsilon-greedy) vs the pool -> refit Q residual tables on all experience."""
    sys.path.insert(0, ROOT)
    import demon
    opps = _expand(a.opp)
    weights = {o: (a.agent_weight if os.path.basename(o) == "agent.py" else 1) for o in opps}
    all_logs, all_hands = [], []
    for rnd in range(a.rounds):
        env = {"DEMON_TRAIN": "1", "DEMON_EPS": str(a.eps), "DEMON_EXPERT": "",
               "DEMON_SAMPLES": str(a.samples)}
        specs = [dict(opp=o, seed=f"q{rnd}_{s}_{a.rng}", deals=a.deals, env=env, collect=True,
                      opp_samples=a.samples)
                 for o in opps for s in range(a.seeds * weights[o])]
        t = time.time()
        res = run_jobs(specs, a.jobs)
        for r in res:
            all_logs.extend(r["log"])
            all_hands.extend(r["hand_log"])
        print(f"round {rnd}: {len(specs)} matches, {len(all_logs)} decisions total "
              f"({time.time() - t:.0f}s); mean while exploring "
              f"{sum(r['mean'] for r in res) / len(res):+.3f} bb/deal")
        theta, count = fit_residuals(all_logs, a.ridge)
        d = load_data()
        for i, name in enumerate(demon.LENS_NAMES):
            d[f"theta_{name}"] = theta[i]
            d[f"count_{name}"] = count[i]
        # meta prior: mean hand result per (profile cell, expert), shrunk to the expert's overall mean
        H = np.asarray(all_hands, dtype=np.float64)
        cell, ex, net = H[:, 0].astype(int), H[:, 1].astype(int), H[:, 2]
        overall = np.array([net[ex == e].mean() if (ex == e).any() else 0.0 for e in range(demon.NE)])
        meta = np.zeros((27, demon.NE))
        for c in range(27):
            for e in range(demon.NE):
                m = (cell == c) & (ex == e)
                k = 400.0
                meta[c, e] = (net[m].sum() + k * overall[e]) / (m.sum() + k)
        d["meta_q"] = meta
        print("  expert overall bb/hand:", {n: round(float(v), 3) for n, v in zip(demon.EXPERT_NAMES, overall)})
        save_data(d)


def cmd_meta(a):
    """Meta prior from dedicated per-expert duplicate matches (lower variance than hand logs)."""
    sys.path.insert(0, ROOT)
    import demon
    opps = _expand(a.opp)
    specs = []
    for e in demon.EXPERT_NAMES:
        env = {"DEMON_TRAIN": "0", "DEMON_EXPERT": e, "DEMON_SAMPLES": str(a.samples)}
        for o in opps:
            for s in range(a.seeds):
                specs.append(dict(opp=o, seed=f"m{s}_{a.rng}", deals=a.deals, env=env, tag=e,
                                  opp_samples=a.samples, collect=True))
    res = run_jobs(specs, a.jobs)
    table = {}
    for r in res:
        table.setdefault(r["opp"], {}).setdefault(r["tag"], []).append(r["mean"])
    print(f"{'opponent':26}" + "".join(f"{e:>11}" for e in demon.EXPERT_NAMES))
    for o, row in table.items():
        print(f"{o[:26]:26}" + "".join(f"{np.mean(row[e]):+11.3f}" for e in demon.EXPERT_NAMES))
    # profile cell each opponent ends up in: take the most common cell in its hand logs
    sums = np.zeros((27, demon.NE))
    ns = np.zeros((27, demon.NE))
    for r in res:
        e = demon.EXPERT_NAMES.index(r["tag"])
        for cell, _, _ in r["hand_log"][200:]:   # once the profile has settled
            sums[int(cell), e] += r["mean"] / 2
            ns[int(cell), e] += 1
    overall = np.array([np.mean([r["mean"] / 2 for r in res if r["tag"] == e]) for e in demon.EXPERT_NAMES])
    meta = (sums + 300 * overall) / (ns + 300)
    d = load_data()
    d["meta_q"] = meta
    save_data(d)
    print("meta prior saved; overall per hand:", np.round(overall, 3))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--opp", nargs="+", default=["agent"])
    common.add_argument("--deals", type=int, default=1000)
    common.add_argument("--seeds", type=int, default=4)
    common.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    common.add_argument("--rng", type=int, default=0)
    common.add_argument("--samples", type=int, default=768)
    common.add_argument("--agent-weight", type=int, default=3)
    e = sub.add_parser("eval", parents=[common])
    e.add_argument("--expert", default="")
    e.add_argument("--seed-offset", type=int, default=0)
    e.add_argument("--data", default=None)
    e.add_argument("--bank", type=float, default=TIME_BANK_SECONDS)
    e.add_argument("--set", default="", help="override params on every expert, e.g. defend=0,sd_use=0")
    t = sub.add_parser("tune", parents=[common])
    t.add_argument("--expert", required=True)
    t.add_argument("--keys", default="")
    t.add_argument("--gens", type=int, default=5)
    t.add_argument("--pop", type=int, default=12)
    t.add_argument("--elite", type=int, default=4)
    t.add_argument("--blend", action="store_true")
    t.add_argument("--data", default=None)
    r = sub.add_parser("train", parents=[common])
    r.add_argument("--rounds", type=int, default=2)
    r.add_argument("--eps", type=float, default=0.06)
    r.add_argument("--ridge", type=float, default=30.0)
    m = sub.add_parser("meta", parents=[common])
    a = p.parse_args()
    {"eval": cmd_eval, "tune": cmd_tune, "train": cmd_train, "meta": cmd_meta}[a.cmd](a)


if __name__ == "__main__":
    main()
