"""
tearsheet.py - play duplicate matches and write an HTML performance tearsheet.

Uses dev/harness.py's bot loading, time bank and error rules, but logs every
hand so it can break results down by opponent, seat, how hands ended, playing
style (both bots), timing, and the biggest-swing deals.

    python dev/tearsheet.py                                  # agent.py vs baselines + zoo, 3 matches each
    python dev/tearsheet.py --opp baselines --seeds 5
    python dev/tearsheet.py --opp dev/zoo/tag.py --deals 1000 --seeds 10
    python dev/tearsheet.py --bot "agent.py@r_oop=0.8" --out dev/results/r_oop.html

Writes dev/results/tearsheet_<timestamp>.html (open it in a browser) and
prints a short summary. Add --json to also save the raw per-match data.
"""

import argparse
import html
import json
import math
import os
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import GROUPS, ROOT, Player, _load, _parse, _pct  # noqa: E402  (also adds repo root to sys.path)

from evaluator import cards_to_str  # noqa: E402
from game import (BIG_BLIND, CHOP_Z, NUM_DEALS, RAISE_ACTIONS, TIME_BANK_SECONDS,  # noqa: E402
                  Action, AgentConfig, Game, Street, button_for_deal, make_deal)

ENDINGS = ["hero folds preflop", "opp folds preflop", "hero folds flop", "opp folds flop",
           "hero folds turn", "opp folds turn", "hero folds river", "opp folds river", "showdown"]


# ---------------------------------------------------------------------------
# Simulation (runs in worker processes)
# ---------------------------------------------------------------------------

def _style(history, seat):
    """Per-hand style counters for one seat: vpip, pfr, post raises, post calls,
    times facing a raise, folds to a raise."""
    vpip = pfr = False
    raises = calls = faced = folds = 0
    prev = None
    for r in history:
        if r.seat == seat:
            if prev is not None and prev.seat != seat and prev.action in RAISE_ACTIONS:
                faced += 1
                folds += r.action == Action.FOLD
            if r.street == Street.PREFLOP:
                if r.action in RAISE_ACTIONS:
                    vpip = pfr = True
                elif r.action == Action.CHECK_CALL and r.amount > 0:
                    vpip = True
            elif r.action in RAISE_ACTIONS:
                raises += 1
            elif r.action == Action.CHECK_CALL and r.amount > 0:
                calls += 1
        prev = r
    return [int(vpip), int(pfr), raises, calls, faced, folds]


def _play_half(mod_a, ov_a, mod_b, ov_b, seed, half, deals, config):
    a, b = Player(mod_a, ov_a, config), Player(mod_b, ov_b, config)
    seats = (a, b) if half == 1 else (b, a)
    a_seat = 0 if half == 1 else 1
    rows = []
    for d in range(deals):
        button = button_for_deal(d)
        game = Game(make_deal(str(seed), d), button, hand_index=d)
        while not game.is_terminal:
            seat = game.to_act
            game.apply(seats[seat].act(game.observation(seat)))
        for seat in (0, 1):
            seats[seat].hand_end(game.hand_result(seat))
        res = game.result()
        if res.went_to_showdown:
            end, saw_flop = "showdown", True
        else:
            last = res.history[-1]
            end = f"{'hero' if last.seat == a_seat else 'opp'} folds {last.street.name.lower()}"
            saw_flop = last.street >= Street.FLOP
        rows.append({
            "d": d, "btn": int(button == a_seat), "net": res.nets[a_seat], "end": end,
            "flop": int(saw_flop), "sd": int(res.went_to_showdown),
            "hs": _style(res.history, a_seat), "os": _style(res.history, 1 - a_seat),
        })
    return rows, a, b


def run_job(job):
    bot_spec, opp_spec, seed, deals, bank = job
    (pa, oa), (pb, ob) = _parse(bot_spec), _parse(opp_spec)
    mod_a, mod_b = _load(pa, "a"), _load(pb, "b")
    config = AgentConfig(num_hands=deals, time_bank_seconds=bank)
    r1, a1, b1 = _play_half(mod_a, oa, mod_b, ob, seed, 1, deals, config)
    r2, a2, b2 = _play_half(mod_a, oa, mod_b, ob, seed, 2, deals, config)
    paired = [(x["net"] + y["net"]) / BIG_BLIND for x, y in zip(r1, r2)]
    mean = sum(paired) / len(paired)
    se = statistics.stdev(paired) / math.sqrt(len(paired)) if len(paired) > 1 else 0.0
    lo, hi = mean - CHOP_Z * se, mean + CHOP_Z * se
    forfeit, opp_forfeit = a1.forfeited or a2.forfeited, b1.forfeited or b2.forfeited
    if forfeit:
        verdict = "LOSS"
    elif opp_forfeit:
        verdict = "WIN"
    else:
        verdict = "WIN" if lo > 0 else "LOSS" if hi < 0 else "CHOP"
    return {
        "opp": os.path.basename(opp_spec.partition("@")[0]), "seed": seed, "paired": paired,
        "mean": mean, "lo": lo, "hi": hi, "verdict": verdict,
        "forfeit": forfeit, "opp_forfeit": opp_forfeit,
        "rows": r1 + r2, "times": a1.times + a2.times,
        "errors": a1.errors + a2.errors, "skipped": a1.skipped + a2.skipped,
        "opp_errors": b1.errors + b2.errors, "spend": [a1.spent, a2.spent],
    }


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _ratio(a, b):
    return a / b if b else float("nan")


def _style_summary(rows, key):
    n = len(rows)
    tot = [sum(r[key][i] for r in rows) for i in range(6)]
    flop = sum(r["flop"] for r in rows)
    sd = sum(r["sd"] for r in rows)
    # W$SD only makes sense for the hero side of the row (net is hero's).
    sd_won = sum(1 for r in rows if r["sd"] and (r["net"] > 0 if key == "hs" else r["net"] < 0))
    return {
        "VPIP": _ratio(tot[0], n), "PFR": _ratio(tot[1], n),
        "Postflop aggression (raises / calls)": _ratio(tot[2], tot[3]),
        "Fold to a raise": _ratio(tot[5], tot[4]),
        "Went to showdown (of flops seen)": _ratio(sd, flop),
        "Won at showdown": _ratio(sd_won, sd),
    }


def summarize(opp, ms, deals):
    paired = [x for m in ms for x in m["paired"]]
    n = len(paired)
    mean = sum(paired) / n
    std = statistics.stdev(paired) if n > 1 else 0.0
    se = std / math.sqrt(n) if n else 0.0
    rows = [r for m in ms for r in m["rows"]]
    times = [t for m in ms for t in m["times"]]

    def group(pred):
        sel = [r for r in rows if pred(r)]
        tot = sum(r["net"] for r in sel) / BIG_BLIND
        return {"hands": len(sel), "share": _ratio(len(sel), len(rows)), "bb": tot,
                "bb_per_hand": _ratio(tot, len(sel))}

    swings = []
    for m in ms:
        nets = {(i // deals + 1, r["d"]): r["net"] for i, r in enumerate(m["rows"])}
        for d, p in enumerate(m["paired"]):
            swings.append((p, m["seed"], d, nets[(1, d)] / BIG_BLIND, nets[(2, d)] / BIG_BLIND))
    swings.sort()

    def deal_info(s):
        p, seed, d, h1, h2 = s
        deal = make_deal(str(seed), d)
        return {"paired": p, "seed": seed, "deal": d, "h1": h1, "h2": h2,
                "hero1": cards_to_str(deal.hole_cards[0]), "hero2": cards_to_str(deal.hole_cards[1]),
                "board": cards_to_str(deal.board)}

    return {
        "opp": opp, "matches": len(ms), "deals": n, "mean": mean, "std": std,
        "lo": mean - CHOP_Z * se, "hi": mean + CHOP_Z * se,
        "wcl": [sum(m["verdict"] == v for m in ms) for v in ("WIN", "CHOP", "LOSS")],
        "per_match": [{"seed": m["seed"], "mean": m["mean"], "lo": m["lo"], "hi": m["hi"],
                       "verdict": m["verdict"]} for m in ms],
        "curves": [list(_cumsum(m["paired"])) for m in ms],
        "position": {"Button (acts first preflop, last after)": group(lambda r: r["btn"]),
                     "Big blind": group(lambda r: not r["btn"])},
        "endings": {e: group(lambda r, e=e: r["end"] == e) for e in ENDINGS},
        "showdown_split": {
            "Showdown won": group(lambda r: r["sd"] and r["net"] > 0),
            "Showdown lost": group(lambda r: r["sd"] and r["net"] < 0),
            "Showdown split": group(lambda r: r["sd"] and r["net"] == 0)},
        "hero_style": _style_summary(rows, "hs"), "opp_style": _style_summary(rows, "os"),
        "timing": {
            "decisions": len(times), "avg_ms": 1000 * _ratio(sum(times), len(times)),
            "p50_ms": 1000 * _pct(times, .5), "p99_ms": 1000 * _pct(times, .99),
            "max_ms": 1000 * max(times, default=0.0),
            "think_half_avg": statistics.mean(s for m in ms for s in m["spend"]),
            "think_half_max": max(s for m in ms for s in m["spend"]),
            "errors": sum(m["errors"] for m in ms), "skipped": sum(m["skipped"] for m in ms),
            "opp_errors": sum(m["opp_errors"] for m in ms),
            "forfeits": sum(m["forfeit"] for m in ms), "opp_forfeits": sum(m["opp_forfeit"] for m in ms),
        },
        "worst": [deal_info(s) for s in swings[:5]],
        "best": [deal_info(s) for s in swings[::-1][:5]],
    }


def _cumsum(xs):
    t = 0.0
    for x in xs:
        t += x
        yield t


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

CSS = """
:root{color-scheme:light;--bg:#f6f6f4;--surface:#fcfcfb;--text:#0b0b0b;--text2:#52514e;--muted:#8a8984;
--grid:#e6e5e0;--axis:#c9c8c2;--pos:#2a78d6;--neg:#e34948;--ctx:#b9b8b2;--border:#e2e1dc;
--win:#008300;--chop:#9a7400;--loss:#c62d2c}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#121211;--surface:#1a1a19;
--text:#f0efec;--text2:#c3c2b7;--muted:#8d8c85;--grid:#2c2c2a;--axis:#45443f;--pos:#3987e5;--neg:#e66767;
--ctx:#4d4c47;--border:#2e2e2b;--win:#3fae3f;--chop:#d6a838;--loss:#ef7a79}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#121211;--surface:#1a1a19;--text:#f0efec;--text2:#c3c2b7;
--muted:#8d8c85;--grid:#2c2c2a;--axis:#45443f;--pos:#3987e5;--neg:#e66767;--ctx:#4d4c47;--border:#2e2e2b;
--win:#3fae3f;--chop:#d6a838;--loss:#ef7a79}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:18px;margin:0 0 12px}h3{font-size:14px;margin:18px 0 8px;color:var(--text2)}
.sub{color:var(--text2);margin:0 0 20px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:18px;margin:0 0 18px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:0 0 18px}
.tile{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px 14px}
.tile .k{color:var(--text2);font-size:12px}.tile .v{font-size:22px;font-weight:600;font-variant-numeric:tabular-nums}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th,td{padding:5px 8px;text-align:right;border-bottom:1px solid var(--grid);white-space:nowrap}
th{color:var(--text2);font-weight:500;font-size:12px}th:first-child,td:first-child{text-align:left}
.scroll{overflow-x:auto}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:0 24px}
.WIN{color:var(--win);font-weight:600}.CHOP{color:var(--chop);font-weight:600}.LOSS{color:var(--loss);font-weight:600}
.pos{color:var(--pos)}.neg{color:var(--neg)}
.mono{font-family:ui-monospace,Consolas,monospace;font-size:12px}
.warn{color:var(--loss);font-weight:600}
svg text{fill:var(--text2);font-size:11px}
.chart{position:relative}
.tip{position:absolute;pointer-events:none;background:var(--surface);border:1px solid var(--border);border-radius:6px;
padding:6px 8px;font-size:12px;box-shadow:0 2px 8px rgba(0,0,0,.15);display:none;white-space:nowrap}
.legend{display:flex;gap:16px;color:var(--text2);font-size:12px;margin:4px 0 0}
.sw{display:inline-block;width:14px;height:2px;vertical-align:middle;margin-right:6px}
nav a{color:var(--pos);margin-right:12px;text-decoration:none}
"""

JS = """
document.querySelectorAll('.chart[data-line]').forEach(function(el){
  var d=JSON.parse(el.dataset.line), svg=el.querySelector('svg'), tip=el.querySelector('.tip'),
      cross=svg.querySelector('.cross');
  svg.addEventListener('mousemove',function(ev){
    var r=svg.getBoundingClientRect(), vx=(ev.clientX-r.left)*d.W/r.width;
    var i=Math.round((vx-d.L)/(d.W-d.L-d.R)*(d.xs.length-1));
    if(i<0||i>=d.xs.length){tip.style.display='none';cross.style.display='none';return;}
    var x=d.L+i/(d.xs.length-1)*(d.W-d.L-d.R);
    cross.setAttribute('x1',x);cross.setAttribute('x2',x);cross.style.display='';
    var h='<b>deal '+(d.xs[i]+1)+'</b><br>average: '+d.avg[i].toFixed(1)+' bb';
    if(d.lines.length>1) h+='<br>matches: '+d.lines.map(function(l){return l[i].toFixed(0)}).join(', ');
    tip.innerHTML=h;tip.style.display='block';
    var px=ev.clientX-r.left; tip.style.left=(px>r.width*0.6?px-tip.offsetWidth-12:px+12)+'px';tip.style.top='8px';
  });
  svg.addEventListener('mouseleave',function(){tip.style.display='none';cross.style.display='none';});
});
"""


def _e(x):
    return html.escape(str(x))


def _f(x, digits=2, sign=False, pct=False):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "–"
    if pct:
        return f"{100 * x:.1f}%"
    return f"{x:+.{digits}f}" if sign else f"{x:.{digits}f}"


def _cls(x):
    return "pos" if x > 0 else "neg" if x < 0 else ""


def _nice_ticks(lo, hi, n=5):
    if hi <= lo:
        hi = lo + 1
    raw = (hi - lo) / n
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    start = math.floor(lo / step) * step
    ticks = []
    t = start
    while t <= hi + step * 1e-9:
        ticks.append(round(t, 10))
        t += step
    return ticks


def svg_overview(sums):
    """Horizontal bars: mean bb/deal per opponent with a 95% CI whisker."""
    L, R, row, top = 190, 70, 30, 24
    W, H = 760, top + row * len(sums) + 10
    lo = min(0.0, min(s["lo"] for s in sums))
    hi = max(0.0, max(s["hi"] for s in sums))
    ticks = _nice_ticks(lo, hi, 6)
    lo, hi = min(lo, ticks[0]), max(hi, ticks[-1])
    sx = lambda v: L + (v - lo) / (hi - lo) * (W - L - R)  # noqa: E731
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="bb per deal by opponent">']
    for t in ticks:
        out.append(f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{top - 6}" y2="{H - 6}" '
                   f'stroke="var(--{"axis" if t == 0 else "grid"})" stroke-width="1"/>')
        out.append(f'<text x="{sx(t):.1f}" y="{top - 10}" text-anchor="middle">{t:g}</text>')
    for i, s in enumerate(sums):
        y = top + i * row + row / 2
        x0, x1 = sx(0), sx(s["mean"])
        color = "var(--pos)" if s["mean"] >= 0 else "var(--neg)"
        bx, bw = min(x0, x1), max(abs(x1 - x0), 1)
        out.append(f'<g><title>{_e(s["opp"])}: {s["mean"]:+.2f} bb/deal, 95% CI '
                   f'[{s["lo"]:+.2f}, {s["hi"]:+.2f}], W-C-L {"-".join(map(str, s["wcl"]))}</title>')
        out.append(f'<rect x="{L}" y="{y - row / 2}" width="{W - L}" height="{row}" fill="transparent"/>')
        out.append(f'<text x="{L - 10}" y="{y + 4}" text-anchor="end" style="fill:var(--text)">{_e(s["opp"])}</text>')
        out.append(f'<rect x="{bx:.1f}" y="{y - 8}" width="{bw:.1f}" height="16" rx="4" fill="{color}"/>')
        out.append(f'<line x1="{sx(s["lo"]):.1f}" x2="{sx(s["hi"]):.1f}" y1="{y}" y2="{y}" '
                   f'stroke="var(--text)" stroke-width="1.5"/>')
        for v in (s["lo"], s["hi"]):
            out.append(f'<line x1="{sx(v):.1f}" x2="{sx(v):.1f}" y1="{y - 5}" y2="{y + 5}" '
                       f'stroke="var(--text)" stroke-width="1.5"/>')
        out.append(f'<text x="{W - R + 8}" y="{y + 4}" style="fill:var(--text)">{s["mean"]:+.2f}</text></g>')
    out.append("</svg>")
    return "".join(out)


def svg_curves(curves):
    """Cumulative paired bb across the match: one thin line per match + the average."""
    L, R, T, B, W, H = 52, 14, 12, 26, 760, 240
    n = min(len(c) for c in curves)
    step = max(1, n // 300)
    xs = list(range(0, n, step))
    if xs[-1] != n - 1:
        xs.append(n - 1)
    lines = [[c[i] for i in xs] for c in curves]
    avg = [sum(col) / len(col) for col in zip(*lines)]
    lo = min(0.0, min(min(l) for l in lines))
    hi = max(0.0, max(max(l) for l in lines))
    ticks = _nice_ticks(lo, hi, 5)
    lo, hi = min(lo, ticks[0]), max(hi, ticks[-1])
    sx = lambda i: L + i / (len(xs) - 1) * (W - L - R)  # noqa: E731
    sy = lambda v: T + (hi - v) / (hi - lo) * (H - T - B)  # noqa: E731
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="cumulative bb over the match">']
    for t in ticks:
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{sy(t):.1f}" y2="{sy(t):.1f}" '
                   f'stroke="var(--{"axis" if t == 0 else "grid"})" stroke-width="1"/>')
        out.append(f'<text x="{L - 6}" y="{sy(t) + 4:.1f}" text-anchor="end">{t:g}</text>')
    for frac in (0, .25, .5, .75, 1):
        i = round(frac * (len(xs) - 1))
        out.append(f'<text x="{sx(i):.1f}" y="{H - 8}" text-anchor="middle">{xs[i] + 1}</text>')
    pts = lambda ys: " ".join(f"{sx(i):.1f},{sy(v):.1f}" for i, v in enumerate(ys))  # noqa: E731
    if len(lines) > 1:
        for ln in lines:
            out.append(f'<polyline points="{pts(ln)}" fill="none" stroke="var(--ctx)" stroke-width="1.2"/>')
    out.append(f'<polyline points="{pts(avg)}" fill="none" stroke="var(--pos)" stroke-width="2"/>')
    out.append(f'<line class="cross" y1="{T}" y2="{H - B}" stroke="var(--muted)" stroke-width="1" style="display:none"/>')
    out.append("</svg>")
    data = json.dumps({"W": W, "L": L, "R": R, "xs": xs, "avg": [round(v, 2) for v in avg],
                       "lines": [[round(v, 1) for v in ln] for ln in lines]})
    legend = ('<div class="legend"><span><i class="sw" style="background:var(--pos)"></i>average of matches</span>'
              + ('<span><i class="sw" style="background:var(--ctx)"></i>each match</span>' if len(lines) > 1 else "")
              + '<span>x: deal · y: cumulative paired bb</span></div>')
    return f'<div class="chart" data-line=\'{_e(data)}\'>{"".join(out)}<div class="tip"></div></div>{legend}'


def _group_table(title, groups):
    rows = "".join(
        f'<tr><td>{_e(k)}</td><td>{g["hands"]}</td><td>{_f(g["share"], pct=True)}</td>'
        f'<td class="{_cls(g["bb"])}">{_f(g["bb"], 1, sign=True)}</td>'
        f'<td class="{_cls(g["bb_per_hand"]) if g["hands"] else ""}">{_f(g["bb_per_hand"], 2, sign=True)}</td></tr>'
        for k, g in groups.items() if g["hands"])
    return (f'<h3>{_e(title)}</h3><div class="scroll"><table><tr><th></th><th>hands</th><th>share</th>'
            f'<th>total bb</th><th>bb / hand</th></tr>{rows}</table></div>')


def _deals_table(title, deals):
    rows = "".join(
        f'<tr><td>{_e(d["seed"])} #{d["deal"]}</td><td class="{_cls(d["paired"])}">{d["paired"]:+.1f}</td>'
        f'<td class="mono">{_e(d["hero1"])}</td><td class="{_cls(d["h1"])}">{d["h1"]:+.1f}</td>'
        f'<td class="mono">{_e(d["hero2"])}</td><td class="{_cls(d["h2"])}">{d["h2"]:+.1f}</td>'
        f'<td class="mono">{_e(d["board"])}</td></tr>' for d in deals)
    return (f'<h3>{_e(title)}</h3><div class="scroll"><table><tr><th>seed / deal</th><th>paired bb</th>'
            f'<th>our cards, half 1</th><th>bb</th><th>our cards, half 2</th><th>bb</th><th>board</th></tr>'
            f'{rows}</table></div>')


def opp_section(s, bank):
    t = s["timing"]
    warn = ' <span class="warn">over 4 s, little margin on a slower CPU</span>' if t["think_half_max"] > bank / 2 else ""
    flags = []
    if t["errors"]:
        flags.append(f'<span class="warn">{t["errors"]} errors</span>')
    if t["forfeits"]:
        flags.append(f'<span class="warn">{t["forfeits"]} forfeited matches</span>')
    if t["skipped"]:
        flags.append(f'<span class="warn">{t["skipped"]} decisions auto-played (bank empty or forfeited)</span>')
    per_match = "".join(
        f'<tr><td>{_e(m["seed"])}</td><td class="{_cls(m["mean"])}">{m["mean"]:+.3f}</td>'
        f'<td>[{m["lo"]:+.2f}, {m["hi"]:+.2f}]</td><td class="{m["verdict"]}">{m["verdict"]}</td></tr>'
        for m in s["per_match"])
    style_rows = "".join(
        f'<tr><td>{_e(k)}</td><td>{_f(v, pct=True) if "aggression" not in k else _f(v, 2)}</td>'
        f'<td>{_f(s["opp_style"][k], pct=True) if "aggression" not in k else _f(s["opp_style"][k], 2)}</td></tr>'
        for k, v in s["hero_style"].items())
    anchor = "opp-" + "".join(ch if ch.isalnum() else "-" for ch in s["opp"])
    return f"""
<section class="card" id="{anchor}">
  <h2>vs {_e(s["opp"])}</h2>
  <div class="tiles">
    <div class="tile"><div class="k">bb / deal (paired)</div><div class="v {_cls(s['mean'])}">{s['mean']:+.3f}</div></div>
    <div class="tile"><div class="k">95% CI, pooled</div><div class="v" style="font-size:16px">[{s['lo']:+.2f}, {s['hi']:+.2f}]</div></div>
    <div class="tile"><div class="k">W-C-L ({s['matches']} matches)</div><div class="v">{'-'.join(map(str, s['wcl']))}</div></div>
    <div class="tile"><div class="k">std per deal</div><div class="v">{s['std']:.1f} bb</div></div>
    <div class="tile"><div class="k">think per half (max)</div><div class="v">{t['think_half_max']:.2f}s</div></div>
  </div>
  {"<p>" + " · ".join(flags) + "</p>" if flags else ""}
  <h3>Cumulative result over the match</h3>
  {svg_curves(s["curves"])}
  <div class="grid2">
    <div>{_group_table("By seat (single hands, not paired)", s["position"])}</div>
    <div>{_group_table("At showdown", s["showdown_split"])}</div>
  </div>
  {_group_table("How hands ended", s["endings"])}
  <div class="grid2">
    <div><h3>Playing style</h3><div class="scroll"><table><tr><th></th><th>us</th><th>opponent</th></tr>{style_rows}</table></div></div>
    <div><h3>Timing</h3><div class="scroll"><table>
      <tr><td>decisions</td><td>{t['decisions']}</td></tr>
      <tr><td>avg / p50 / p99 / max ms</td><td>{t['avg_ms']:.2f} / {t['p50_ms']:.2f} / {t['p99_ms']:.2f} / {t['max_ms']:.1f}</td></tr>
      <tr><td>think per half avg / max</td><td>{t['think_half_avg']:.2f}s / {t['think_half_max']:.2f}s of {bank:g}s{warn}</td></tr>
      <tr><td>our errors / auto-played</td><td>{t['errors']} / {t['skipped']}</td></tr>
      <tr><td>opponent errors / forfeits</td><td>{t['opp_errors']} / {t['opp_forfeits']}</td></tr>
    </table></div></div>
  </div>
  <h3>Per match</h3><div class="scroll"><table><tr><th>seed</th><th>bb/deal</th><th>95% CI</th><th>verdict</th></tr>{per_match}</table></div>
  {_deals_table("Biggest losing deals", s["worst"])}
  {_deals_table("Biggest winning deals", s["best"])}
</section>"""


def render(sums, args, elapsed):
    total = len(sums) and sum(s["matches"] for s in sums)
    points = sum(s["wcl"][0] + 0.5 * s["wcl"][1] for s in sums)
    wcl = [sum(s["wcl"][i] for s in sums) for i in range(3)]
    errors = sum(s["timing"]["errors"] for s in sums)
    worst_think = max(s["timing"]["think_half_max"] for s in sums)
    overview_rows = "".join(
        f'<tr><td><a href="#opp-{"".join(ch if ch.isalnum() else "-" for ch in s["opp"])}">{_e(s["opp"])}</a></td>'
        f'<td class="{_cls(s["mean"])}">{s["mean"]:+.3f}</td><td>[{s["lo"]:+.2f}, {s["hi"]:+.2f}]</td>'
        f'<td>{"-".join(map(str, s["wcl"]))}</td><td>{s["std"]:.1f}</td>'
        f'<td>{s["timing"]["avg_ms"]:.2f}</td><td>{s["timing"]["p99_ms"]:.2f}</td>'
        f'<td>{s["timing"]["think_half_max"]:.2f}s</td><td>{s["timing"]["errors"]}</td></tr>' for s in sums)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bot Tearsheet</title><style>{CSS}</style></head>
<body><main>
<h1>Tearsheet: {_e(args.bot)}</h1>
<p class="sub">{len(sums)} opponents × {args.seeds} duplicate matches × {args.deals} deals · bank {args.bank:g}s/half ·
seed offset {args.seed_offset} · {time.strftime('%Y-%m-%d %H:%M')} · ran in {elapsed:.0f}s</p>
<div class="tiles">
  <div class="tile"><div class="k">points</div><div class="v">{points:.1f} / {total}</div></div>
  <div class="tile"><div class="k">W-C-L</div><div class="v">{'-'.join(map(str, wcl))}</div></div>
  <div class="tile"><div class="k">our errors</div><div class="v {'neg' if errors else ''}">{errors}</div></div>
  <div class="tile"><div class="k">worst think / half</div><div class="v {'neg' if worst_think > args.bank / 2 else ''}">{worst_think:.2f}s</div></div>
</div>
<section class="card"><h2>Result by opponent</h2>
<p class="sub" style="margin-bottom:8px">Bar = mean paired bb/deal, whisker = pooled 95% CI. A whisker clear of 0 means a significant edge.</p>
{svg_overview(sums)}
<div class="scroll"><table><tr><th>opponent</th><th>bb/deal</th><th>95% CI</th><th>W-C-L</th><th>std</th>
<th>avg ms</th><th>p99 ms</th><th>think/half max</th><th>errors</th></tr>{overview_rows}</table></div>
</section>
{''.join(opp_section(s, args.bank) for s in sums)}
<p class="sub">Paired bb = our result on a deal summed over both seats (duplicate), in big blinds. Verdicts use the
judge's rule: WIN if the match CI is above 0, LOSS if below, CHOP otherwise; a forfeit loses.</p>
</main><script>{JS}</script></body></html>"""


# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bot", default="agent.py", help='bot under test, e.g. "agent.py@r_oop=0.8"')
    parser.add_argument("--opp", nargs="+", default=["baselines", "zoo"],
                        help="bot paths and/or the groups 'baselines', 'zoo'")
    parser.add_argument("--deals", type=int, default=NUM_DEALS)
    parser.add_argument("--seeds", type=int, default=3, help="duplicate matches per opponent")
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument("--bank", type=float, default=TIME_BANK_SECONDS)
    parser.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    parser.add_argument("--out", help="output .html (default dev/results/tearsheet_<time>.html)")
    parser.add_argument("--json", action="store_true", help="also save the summary as .json next to the html")
    args = parser.parse_args()

    opps = []
    for o in args.opp:
        opps.extend(GROUPS.get(o, [o]))
    jobs = [(args.bot, o, f"h{args.seed_offset + s}", args.deals, args.bank)
            for o in opps for s in range(args.seeds)]
    print(f"playing {len(jobs)} matches ({len(opps)} opponents x {args.seeds}) on {args.jobs} workers...")
    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(run_job, jobs))
    elapsed = time.perf_counter() - start

    sums = []
    for o in opps:
        name = os.path.basename(o.partition("@")[0])
        ms = [r for r in results if r["opp"] == name]
        if ms:
            sums.append(summarize(name, ms, args.deals))

    out = args.out or os.path.join(ROOT, "dev", "results", f"tearsheet_{time.strftime('%Y%m%d_%H%M%S')}.html")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render(sums, args, elapsed))
    if args.json:
        with open(os.path.splitext(out)[0] + ".json", "w", encoding="utf-8") as fh:
            json.dump(sums, fh, indent=1, default=float)

    print(f"\n{'opponent':30} {'bb/deal':>8} {'95% CI':>18} {'W-C-L':>7} {'err':>4} {'think/half':>10}")
    for s in sums:
        print(f"{s['opp'][:30]:30} {s['mean']:+8.3f} [{s['lo']:+7.2f},{s['hi']:+7.2f}] "
              f"{'-'.join(map(str, s['wcl'])):>7} {s['timing']['errors']:4d} {s['timing']['think_half_max']:9.2f}s")
    points = sum(s["wcl"][0] + 0.5 * s["wcl"][1] for s in sums)
    print(f"\npoints {points:.1f} / {len(results)}   ({elapsed:.0f}s)\ntearsheet: {os.path.abspath(out)}")


if __name__ == "__main__":
    main()
