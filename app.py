"""12-month edges: the idea-map seeds on the S&P 500, long-only (Alex 2026-11-06: "let's actually just go for a 12 m
edge version ... get the 12m data up with a dashboard").

Every formula Haiku drafted from the idea map (241 areas in 31 families, guided by Opus examples), graded free on
training years only: each month, buy the top fifth of S&P 500 stocks by the formula (equal weight, financials out),
hold 12 months, subtract the equal-weighted S&P 500. Only formulas with training t (non-overlapping, grade.py t_test) of
at least 1 are shown anywhere on the page (Alex 2026-11-10: "we shouldn't show these ... training t <1"); the rest stay
in the data file, unused. ("Seed", t >= 1, was the idea-map rule for the grow step, which was dropped 2026-11-06.) Hosted like the event-study page (sharadar/event_site): it reads only
data/dash12.json.gz in this folder (export.py), no market data. The 2024+ columns are hidden until the viewer turns
them on (Alex 2026-11-06: "a revealable column"); they are shown only, never used to pick.

Run (from the repo root): C:\\Python310\\python.exe -m streamlit run sharadar\\edge12_site\\app.py --server.port 8541
Secrets (.streamlit/secrets.toml on the host; optional locally): password.
History only, not investment advice.
"""
from __future__ import annotations

import gzip
import hmac
import html
import json
import os
import subprocess
import sys
from pathlib import Path

import hashlib

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

HERE = Path(__file__).resolve().parent
DATA = HERE / "data" / "dash12.json.gz"
UMAP = HERE / "data" / "umap12.json.gz"  # build_umap.py
SERIES = HERE / "data" / "series12.json.gz"
click3d = components.declare_component("click3d", path=str(HERE / "click3d"))  # 3D chart that reports clicks
EXPORT = HERE / "export.py"
LOCAL = (HERE.parent / "playbook" / "horserace" / "im_dash_data.py").exists()  # inside the repo, not on the host

# Page: lifted from blackbird-search/app.py (Alex 2026-11-10: "lift the background and the plane design and
# everything from the prev blackbird dashboard"): gunmetal-steel-titanium radial gradient, white and soft text, Helvetica (was Saira),
# the SR-71 blueprint watermark (logo.svg, copied from blackbird-search), black rounded cards, pill buttons.
from urllib.parse import quote  # noqa: E402
GUNMETAL, STEEL, TITANIUM = "#14181C", "#262E34", "#3A444B"
BLACK, WHITE = "#000000", "#FFFFFF"
SOFT, EDGE = "#D5DADF", "#8D959C"
SR71_URI = "data:image/svg+xml," + quote((HERE / "logo.svg").read_text(encoding="utf-8"))
# Plot names kept for the chart code: the 3D panel is see-through so the page gradient shows behind it.
GROUND, CARD, FIELD = "rgba(0,0,0,0)", BLACK, "#14161A"
LINE, BRONZE, BRONZE_HI, BRONZE_DIM = TITANIUM, SOFT, WHITE, EDGE  # 3D grids draw see-through colours near solid
# Landscape sheet (Alex 2026-11-10: "hot yellow to red for the top third, then fade to transparent, then fade to
# grey/white ... a bone ash/ceramic color to end", "intl orange, grey/graphite and then light grey/white"): positions
# are shares of the sheet's own height range.
INTL_ORANGE = "#FF4F00"
# Top third runs yellow -> international orange -> red, red highest (Alex 2026-11-10: "red as the top of the scale,
# not yellow").
# The middle third dims to graphite (Alex 2026-11-10: "the middle 3rd isn't darkening").
SHEET_SCALE = [[0, "#ECE7DD"], [0.18, "#C9C6BF"], [1 / 3, "#7E8187"], [0.42, "#3A3E44"], [0.58, "#3A3E44"],
               [2 / 3, "#FFD21F"], [0.8, INTL_ORANGE], [0.9, "#E63A12"], [1, "#B3201A"]]
# Picker (Alex 2026-11-10: "add inferno and lajolla"): exact stops from plotly.colors.sequential.Inferno and from
# cmcrameri's lajolla sampled at 9 even points.
_even = lambda cs: [[i / (len(cs) - 1), c] for i, c in enumerate(cs)]  # noqa: E731
SHEET_SCALES = {
    "Lunar": SHEET_SCALE,
    "Inferno": _even(["#000004", "#1b0c41", "#4a0c6b", "#781c6d", "#a52c60", "#cf4446", "#ed6925", "#fb9b06",
                      "#f7d13d", "#fcffa4"]),
    "Lajolla": _even(["#191900", "#372411", "#67342a", "#a64644", "#d9604e", "#e58851", "#edae54", "#f7da74",
                      "#fffecb"]),
}
DOT_SCALE = [[0, "#ECE7DD"], [0.35, "#9C9EA2"], [0.5, "#5A5F66"], [0.68, "#FFD21F"], [0.85, INTL_ORANGE],
             [1, "#B3201A"]]
SCALE = DOT_SCALE  # the 2D "does it hold up" chart

st.set_page_config(page_title="Blackbird Edge Atlas", layout="wide")
st.markdown(f"""<style>
@import url("https://fonts.googleapis.com/css2?family=Syne:wght@800&display=swap");
.stApp {{color-scheme:dark; background:radial-gradient(120% 90% at 50% -10%, {TITANIUM} 0%, {STEEL} 45%, {GUNMETAL} 100%) fixed;}}
[data-testid="stHeader"] {{background:transparent;}}
[data-testid="stAppDeployButton"], [data-testid="stDecoration"] {{display:none;}}
.block-container {{max-width:1900px; padding-top:2.2rem;}}
.logo {{display:flex; align-items:baseline; gap:1.4rem; flex-wrap:nowrap; white-space:nowrap; min-height:107px; margin:0 0 .5rem 0; padding-left:4px;
  background:url("{SR71_URI}") no-repeat 0 10px / 680px 97px;}}
.word {{display:inline-block; color:{WHITE} !important; font-style:normal;
  font-size:3.2rem; line-height:1; text-transform:uppercase; letter-spacing:.2em; font-weight:800; white-space:nowrap;
  font-family:Syne, "Arial Black", sans-serif !important; -webkit-text-stroke:2px {WHITE};}}  /* wordmark: Syne 800, 2px outline (Alex 2026-11-10: "do syne") */
.tag {{color:{SOFT} !important; font-size:1.35rem; letter-spacing:.14em; font-weight:700; text-transform:uppercase;
  font-family:"Helvetica Neue", Helvetica, Arial, sans-serif !important;}}  /* Helvetica, heavier (Alex 2026-11-10) */
.stApp, .stApp p, .stApp span, .stApp label, .stApp li, .stApp div, .stApp button {{color:{WHITE};}}
.stApp, .stApp *:not(.word):not(.tag):not([data-testid="stIconMaterial"]):not(.material-symbols-rounded):not(code):not(pre),
[data-baseweb="popover"], [data-baseweb="popover"] *, [role="tooltip"], [role="tooltip"] * {{
  font-family:"Helvetica Neue", Helvetica, Arial, sans-serif !important; -webkit-font-smoothing:antialiased;}}
.stApp h2, .stApp h3 {{color:{WHITE} !important; font-weight:600; font-size:1.05rem !important; text-transform:uppercase;
  letter-spacing:.16em; border-bottom:1px solid {EDGE}; padding-bottom:.35rem; margin-top:1.6rem;}}
.stApp h2::before, .stApp h3::before {{content:""; display:inline-block; width:.55rem; height:.55rem; background:{INTL_ORANGE};
  margin-right:.6rem; vertical-align:.05rem;}}
textarea, input {{background:transparent !important; color:{WHITE} !important; caret-color:{WHITE};}}
[data-baseweb="textarea"], [data-baseweb="input"], [data-baseweb="select"] > div {{background:{BLACK} !important; border:1px solid {EDGE} !important; border-radius:2px !important;}}
[data-baseweb="textarea"]:focus-within, [data-baseweb="input"]:focus-within {{border-color:{INTL_ORANGE} !important;}}
input::placeholder, textarea::placeholder {{color:{SOFT} !important; -webkit-text-fill-color:{SOFT} !important; opacity:1 !important;}}
.stButton button, [data-testid="stLinkButton"] a {{background:transparent; border:1px solid {EDGE}; border-radius:2px !important; min-height:2.4rem;
  text-transform:uppercase; letter-spacing:.1em;}}
.stButton button *, [data-testid="stLinkButton"] a * {{color:{WHITE} !important; font-size:.92rem !important; font-weight:500;}}
.stButton button:hover, [data-testid="stLinkButton"] a:hover {{border-color:{INTL_ORANGE};}}
button:focus-visible, a:focus-visible {{outline:2px solid {INTL_ORANGE}; outline-offset:2px;}}
[data-testid="stExpander"] details {{border:1px solid {EDGE} !important; border-radius:2px !important; background:transparent !important;}}
[data-testid="stExpander"] summary, [data-testid="stExpander"] details[open] summary, [data-testid="stExpander"] summary:focus {{background:transparent !important; color:{WHITE} !important;}}
[data-testid="stExpander"] summary * {{color:{WHITE} !important;}}
[data-testid="stExpander"] summary:hover {{background:rgba(0,0,0,.25) !important;}}
[data-testid="stMetricLabel"] p {{color:{SOFT} !important; text-transform:uppercase; letter-spacing:.12em; font-size:.72rem !important;}}
[data-testid="stMetric"] {{border-left:2px solid {INTL_ORANGE}; padding-left:.8rem;}}
[data-testid="stDataFrame"] > div {{border-radius:2px !important;}}
.muted {{color:{SOFT} !important; font-size:.92rem;}}
.card {{background:{BLACK}; border:1px solid {TITANIUM}; border-left:3px solid {INTL_ORANGE}; border-radius:0; padding:.9rem 1.1rem;
  margin:6px 0 12px 0;}}
.card b {{color:{WHITE};}}
.stApp [data-stale="true"] {{opacity:1 !important; transition:none !important;}}
</style>""", unsafe_allow_html=True)


def secret(k: str):
    try:
        return st.secrets.get(k) or os.environ.get(k.upper())
    except Exception:  # noqa: BLE001  (no secrets file locally)
        return os.environ.get(k.upper())


def api_key():
    """The host's secret; locally, the process or the Windows user variable (as blackbird-search/app.py)."""
    k = secret("ANTHROPIC_API_KEY")
    if k:
        return k
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as h:
            return winreg.QueryValueEx(h, "ANTHROPIC_API_KEY")[0] or None
    except (ImportError, OSError):
        return None


# ── philosophy screen (Alex 2026-11-10: "a philosophy screen based on a natural language promptbox connected to ...
# sonnet ... subset out the idea areas or ideas that align with a growth trajectory that also believes a bunch of
# other tenets"; like Chinook's philosophy specs, scratch/draft_philosophy.py). Each idea area is split by which end
# it buys, since a growth philosophy can back the buy-high side of an area and oppose the buy-low side.
PHIL_MODEL = "claude-sonnet-5-5"  # $2 / $10 per million tokens in / out
PHIL_SYSTEM = (
    "You screen stock-selection ideas against an investor's philosophy. Each item is one idea area of long-only, "
    "12-month-hold S&P 500 formulas, on one side: 'buys high' holds the stocks with the highest formula values, "
    "'buys low' the lowest. Example hypotheses show what the formulas mean. First split the philosophy into short "
    "tenets. Then give every item a fit: 'aligned' if a manager holding this philosophy would want these stocks and "
    "at least one tenet clearly supports it with none against; 'partly' if some tenets support it and none oppose; "
    "'neutral' if the tenets say nothing about it; 'conflicts' if any tenet argues against owning these stocks. "
    "Judge the side bought, not the topic: buying the most leveraged firms conflicts with a low-leverage tenet. "
    "'why' names the tenet(s) involved in at most 15 words. Return every item id exactly once.")
PHIL_SCHEMA = {
    "type": "object",
    "properties": {
        "tenets": {"type": "array", "items": {"type": "string"}},
        "items": {"type": "array", "items": {
            "type": "object",
            "properties": {"id": {"type": "integer"},
                           "fit": {"type": "string", "enum": ["aligned", "partly", "neutral", "conflicts"]},
                           "why": {"type": "string"}},
            "required": ["id", "fit", "why"], "additionalProperties": False}},
    },
    "required": ["tenets", "items"], "additionalProperties": False,
}


def phil_items(rows: list) -> list:
    """(area, side) groups with their family, count and the two shortest hypotheses as examples."""
    g: dict = {}
    for row in rows:
        side = "buys high" if str(row.get("bet", "")).startswith("higher") else "buys low"
        g.setdefault((row["area"], side), {"family": row["family"], "hyp": []})["hyp"].append(row.get("hypothesis") or "")
    out = []
    for i, ((area, side), v) in enumerate(sorted(g.items())):
        ex = sorted((h for h in v["hyp"] if h), key=len)[:2]
        out.append({"id": i, "area": area, "side": side, "family": v["family"], "n": len(v["hyp"]),
                    "examples": [e[:220] for e in ex]})
    return out


@st.cache_data(show_spinner=False, max_entries=50)
def phil_screen(philosophy: str, items_json: str) -> dict:
    import anthropic
    items = json.loads(items_json)
    lines = [f"{it['id']} | {it['area']} | {it['side']} | family: {it['family']} | e.g. " + " / ".join(it["examples"])
             for it in items]
    user = (f"PHILOSOPHY:\n{philosophy}\n\nITEMS (id | idea area | side | family | example hypotheses):\n"
            + "\n".join(lines))
    client = anthropic.Anthropic(api_key=api_key())
    with client.messages.stream(model=PHIL_MODEL, max_tokens=32000, system=PHIL_SYSTEM,
                                output_config={"effort": "low",
                                               "format": {"type": "json_schema", "schema": PHIL_SCHEMA}},
                                messages=[{"role": "user", "content": user}]) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason == "refusal":
        raise RuntimeError("the model declined this request")
    if msg.stop_reason == "max_tokens":
        raise RuntimeError("the answer was cut off before every idea was scored")
    data = json.loads(next(b.text for b in msg.content if b.type == "text"))
    u = msg.usage
    data["cost"] = (u.input_tokens * 2 + u.output_tokens * 10) / 1e6
    return data


pw = secret("password")
if pw and not st.session_state.get("ok"):
    x = st.text_input("Password", type="password")
    if x and hmac.compare_digest(x, pw):
        st.session_state.ok = True
        st.rerun()
    elif x:
        st.error("Wrong password")
    st.stop()


@st.cache_data(show_spinner=False)
def load(mtime: float) -> dict:
    with gzip.open(DATA, "rt", encoding="utf-8") as fh:
        return json.load(fh)


@st.cache_data(show_spinner=False)
def load_map(mtime: float) -> dict:
    with gzip.open(UMAP, "rt", encoding="utf-8") as fh:
        return json.load(fh)


FULL = HERE / "data" / "fullperiod12.json.gz"


@st.cache_data(show_spinner=False)
def load_full(mtime: float) -> dict:
    """build_fullperiod.py: every formula's 12-month edge per formation month, and the equal-weighted S&P 500's own
    12-month return and cash, all x 10,000."""
    with gzip.open(FULL, "rt", encoding="utf-8") as fh:
        d = json.load(fh)
    n = len(d["months"])
    nan_row = [np.nan] * n
    d["E"] = np.array([nan_row if e is None else [np.nan if v is None else v / 1e4 for v in e] for e in d.pop("e")])
    for k in ("bench", "rf"):
        d[k] = np.array([np.nan if v is None else v / 1e4 for v in d[k]])
    return d


def full_period_view(L: pd.DataFrame, lay: dict, lm: dict) -> None:
    """Full period (Alex 2026-11-11: "a full period visualization, like average sharpe or steadiness metric, so I can v
    simply show someone the patches which had the steadiest returns over the entire period. Make sure to note sharpe
    vs eq wt bmark's value"). Patches as in the videos (make_video.py): each theme region owns the map cells where its
    formulas carry the most kernel weight. A region's score: average its formulas' 12-month edges over the equal-
    weighted S&P 500 month by month, then mean / sd of that series over every formation, 1998-12 to 2025-09."""
    fp = load_full(FULL.stat().st_mtime)
    E = fp["E"][L.index.to_numpy()]
    has = np.isfinite(E).any(axis=1)
    L, E = L[has], E[has]
    x, y = np.asarray(lay["x"])[L.index], np.asarray(lay["y"])[L.index]
    regs = lay["regions"]
    rx, ry = np.array([g["x"] for g in regs]), np.array([g["y"] for g in regs])
    names = [a["name"] for a in lm["areas"]]
    ax_, ay_ = np.asarray(lay["ax"]), np.asarray(lay["ay"])
    area_reg = {nm: int(np.argmin((rx - ax_[i]) ** 2 + (ry - ay_[i]) ** 2)) for i, nm in enumerate(names)}
    reg = np.array([area_reg[a] for a in L.area])
    low = ~L.bet.str.startswith("higher").to_numpy()
    # each formula on its own, no blending (Alex 2026-11-11: "lose the patch averaging"): its full-period Sharpe =
    # mean / sd of its own 12-month edges (24+ formations); a patch shows the median of its formulas
    cnt = np.isfinite(E).sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        f_mu, f_sd = np.nanmean(E, 1), np.nanstd(E, 1, ddof=1)
        f_sh = np.where(cnt >= 24, f_mu / f_sd, np.nan)
        f_pos = np.where(cnt >= 24, (E > 0).sum(1) / cnt, np.nan)
    rows = []
    for k in range(len(regs)):
        m = (reg == k) & np.isfinite(f_sh)
        if m.sum() < 5:
            continue
        rows.append(dict(k=k, theme=regs[k].get("theme", regs[k]["label"]), sharpe=float(np.median(f_sh[m])),
                         edge=float(np.median(f_mu[m])), pos=float(np.median(f_pos[m])), n=int(m.sum()),
                         low=low[m].mean()))
    R = pd.DataFrame(rows).sort_values("sharpe", ascending=False).reset_index(drop=True)
    R["rank"] = np.arange(1, len(R) + 1)
    b = fp["bench"] - fp["rf"]
    b = b[np.isfinite(b)]
    b_sh = b.mean() / b.std(ddof=1)

    # contour map (Alex 2026-11-11: "a map w contours again that basically highlights ideas that generated stable
    # returns over the entire period that can form sort of a core factor set"): each spot = kernel-weighted average of
    # nearby formulas' full-period Sharpe (make_video.py's rule: smoothing 5% of the map width, blank under 3
    # formulas' weight or where the nearest formula is over 1.8 smoothing widths away). Core: the top share of
    # formulas by full-period Sharpe, drawn as dots and listed below.
    ok = np.isfinite(f_sh)
    xs_, ys_, zs_ = x[ok], y[ok], f_sh[ok]
    span = max(np.ptp(lay["x"]), np.ptp(lay["y"]))
    bw, pad = 0.05 * span, 0.125 * span
    gx = np.linspace(min(lay["x"]) - pad, max(lay["x"]) + pad, 140)
    gy = np.linspace(min(lay["y"]) - pad, max(lay["y"]) + pad, 140)
    GX, GY = np.meshgrid(gx, gy)
    ws, wz = np.zeros(GX.shape), np.zeros(GX.shape)
    dmin = np.full(GX.shape, np.inf)
    for i0 in range(0, len(xs_), 150):
        d2 = (GX[..., None] - xs_[i0:i0 + 150]) ** 2 + (GY[..., None] - ys_[i0:i0 + 150]) ** 2
        dmin = np.minimum(dmin, d2.min(-1))
        w = np.exp(-d2 / (2 * bw * bw))
        ws += w.sum(-1)
        wz += (w * zs_[i0:i0 + 150]).sum(-1)
    Z = np.where((ws >= 3) & (dmin <= (1.8 * bw) ** 2), wz / np.maximum(ws, 1e-12), np.nan)
    lo, hi = float(np.nanpercentile(Z, 5)), float(np.nanpercentile(Z, 99.5))  # spread the colours over most of the map
    # two ways to pick the core (Alex 2026-11-11: "or alternatively, the best picks for the factor tenets, with an eye
    # toward stability"): the top share overall, or the steadiest few in each theme so every theme is represented
    cc = st.columns([1.3, 2.5])
    how = cc[0].radio("Core set", ["Top overall", "Best per theme"], horizontal=True, key="fp_how",
                      label_visibility="collapsed")
    if how == "Top overall":
        top = cc[1].select_slider("Top share", [1, 2, 5, 10, 20], value=5, format_func=lambda v: f"top {v}%",
                                  key="fp_core", label_visibility="collapsed")
        cut = float(np.nanpercentile(f_sh, 100 - top))
        core = ok & (f_sh >= cut)
        core_note = f"the core set (Sharpe ≥ {cut:.2f})"
    else:
        per = cc[1].select_slider("Per theme", [1, 2, 3, 5], value=2, format_func=lambda v: f"{v} per theme",
                                  key="fp_per", label_visibility="collapsed")
        core = np.zeros(len(f_sh), bool)
        for k in np.unique(reg):
            ii = np.flatnonzero((reg == k) & ok)
            core[ii[np.argsort(-f_sh[ii])[:per]]] = True
        core_note = f"the {per} highest-Sharpe formulas in each theme"
    # same top-down select map as the other views (Alex 2026-11-11: "why aren't the dots consistent across views, and
    # why can't I select them and have them appear in the table below ... full period is still a top down select
    # view"): filled contours, formula dots hidden until a box or lasso selects them, idea areas as small soft dots
    # (a dot inside adds its whole area). Core formulas show as dots in the same style. The table lists the selection,
    # or the core set when nothing is selected.
    FSC = [[0, "#2A2E33"], [0.35, "#5A5F66"], [0.55, "#FFD21F"], [0.78, INTL_ORANGE], [1, "#B3201A"]]
    themes = np.array([regs[k].get("theme", regs[k]["label"]) for k in reg])
    side = np.where(low, "buys low", "buys high")
    cd = np.stack([L.name.fillna("Unnamed"), themes, np.char.mod("%.2f", np.nan_to_num(f_sh)),
                   np.char.mod("%.0f", np.nan_to_num(f_pos) * 100), side], axis=1)
    hov = ("<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[4]}<br>Sharpe vs eq-wt S&P %{customdata[2]} · "
           "beat the index in %{customdata[3]}% of holds<extra></extra>")
    fig = go.Figure(go.Contour(
        x=gx, y=gy, z=Z, zmin=lo, zmax=hi, ncontours=18, colorscale=FSC,
        contours=dict(coloring="fill", showlines=True), line=dict(color=FIELD, width=0.6), opacity=0.85,
        hoverinfo="skip",
        colorbar=dict(title=dict(text="Sharpe vs<br>eq-wt S&P", font=dict(color=BRONZE)),
                      tickfont=dict(color=BRONZE_DIM), thickness=12, len=0.6, outlinewidth=0)))
    fig.add_trace(go.Scattergl(x=x, y=y, mode="markers", name="formulas",  # 1: every formula, hidden until selected
                               marker=dict(size=4, color=np.nan_to_num(f_sh, nan=lo), colorscale=FSC, cmin=lo, cmax=hi,
                                           line=dict(color=BLACK, width=0.4), opacity=0),
                               selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=0)),
                               hoverinfo="skip", customdata=cd, hovertemplate=hov))
    ka = pd.DataFrame({"name": [a["name"] for a in lm["areas"]], "x": lay["ax"], "y": lay["ay"]})
    kn = ka[ka.name.isin(L.area)]
    fig.add_trace(go.Scattergl(x=kn.x, y=kn.y, mode="markers", name="areas",  # 2: idea areas, small soft dots
                               marker=dict(size=4, color="rgba(255,255,255,.55)"), customdata=kn[["name"]].to_numpy(),
                               hovertemplate="<b>%{customdata[0]}</b><extra></extra>"))
    ci = np.flatnonzero(core)
    fig.add_trace(go.Scattergl(x=x[ci], y=y[ci], mode="markers", name="core",  # 3: the core set, same dot style
                               marker=dict(size=5, color=f_sh[ci], colorscale=FSC, cmin=lo, cmax=hi,
                                           line=dict(color=WHITE, width=0.8)),
                               customdata=cd[ci], hovertemplate=hov))
    fig.update_layout(height=860, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor=GROUND, plot_bgcolor=GROUND,
                      showlegend=False, dragmode="select",
                      font=dict(color=BRONZE, family='"Helvetica Neue", Helvetica, Arial, sans-serif'),
                      xaxis=dict(visible=False, range=[float(x.min()) - .02 * np.ptp(x), float(x.max()) + .02 * np.ptp(x)]),
                      yaxis=dict(visible=False, scaleanchor="x",
                                 range=[float(y.min()) - .02 * np.ptp(y), float(y.max()) + .02 * np.ptp(y)]),
                      hoverlabel=dict(bgcolor=CARD, bordercolor=BRONZE, font=dict(color=BRONZE_HI)))
    st.markdown(f"<p class='muted'>Sharpe of each formula's 12-month return over the equal-weighted S&P 500, holds "
                f"started {pd.Period(fp['months'][0]).strftime('%b %Y')} to "
                f"{pd.Period(fp['months'][-1]).strftime('%b %Y')}. White-ringed dots: {core_note}. Drag a box to list "
                f"formulas; double-click to clear. Equal-weighted S&P 500 itself: Sharpe <b>{b_sh:.2f}</b> over "
                f"cash.</p>", unsafe_allow_html=True)
    ev = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode=("box", "lasso"),
                         key="land_flat_full", config={"displaylogo": False})
    try:
        pts = ev.selection.points
    except AttributeError:
        pts = []
    pick = {int(q["point_index"]) for q in pts if q.get("curve_number") == 1}
    pick |= {int(ci[int(q["point_index"])]) for q in pts if q.get("curve_number") == 3}
    pick_areas = {kn.name.iloc[int(q["point_index"])] for q in pts if q.get("curve_number") == 2}
    if pick_areas:
        pick |= set(np.flatnonzero(L.area.isin(pick_areas).to_numpy()).tolist())
    sel = np.zeros(len(L), bool)
    sel[sorted(pick)] = True
    if sel.any():
        st.markdown(f"<div class='card'><b>{int(sel.sum()):,} formulas selected</b> · "
                    f"{L[sel].area.nunique()} idea areas · median Sharpe vs eq-wt S&P "
                    f"{np.nanmedian(f_sh[sel]):.2f}</div>", unsafe_allow_html=True)
    else:
        sel = core
    C = L[sel]
    T = C.assign(theme=themes[sel], fsh=f_sh[sel], edge=f_mu[sel] * 100, pos=f_pos[sel] * 100,
                 side=side[sel]).sort_values("fsh", ascending=False)
    # plain words (Alex 2026-11-11: "a natural language explanation of the formula/hypothesis down in the table"):
    # the drafter's own hypothesis, and the formula read out by runlog/explain.py (mechanical operator wording)
    try:
        sys.path.insert(0, str(HERE.parent / "runlog"))
        import explain as _ex
        from explain import render as _words
        sys.path.insert(0, str(HERE.parent / "playbook" / "horserace"))
        from monthly_vars import MONTHLY as _mv  # monthly price variables (ret_1, retvol_12, me_m, ...)
        _ex.FIELDS.update({k: v[0].lower() for k, v in _mv.items()})
    except Exception:  # noqa: BLE001  (not shipped to the host: words precomputed by publish.py)
        try:
            _wmap = json.load(gzip.open(HERE / "data" / "words12.json.gz", "rt", encoding="utf-8"))
            _words = lambda e: _wmap.get(e, "")  # noqa: E731
        except Exception:  # noqa: BLE001
            _words = None
    T = T.assign(idea=T.hypothesis.fillna(""),
                 words=[_words(e) if _words else "" for e in T.expression])
    st.dataframe(T[["name", "idea", "words", "theme", "area", "side", "fsh", "edge", "pos", "t", "expression"]],
                 hide_index=True,
                 use_container_width=True, height=min(38 + 35 * len(T), 600),
                 column_config={"name": "Formula", "idea": st.column_config.TextColumn("Hypothesis", width="large"),
                                "words": st.column_config.TextColumn("Formula in words", width="large"),
                                "theme": "Theme", "area": "Idea area", "side": "Side",
                                "fsh": st.column_config.NumberColumn("Sharpe vs eq-wt S&P", format="%.2f"),
                                "edge": st.column_config.NumberColumn("Avg 12-month edge (%)", format="%.1f"),
                                "pos": st.column_config.NumberColumn("Holds beating index (%)", format="%.0f"),
                                "t": st.column_config.NumberColumn("Training t", format="%.2f"),
                                "expression": "Expression"})
    with st.expander("By theme", expanded=False):
        TT = R.assign(edge=R.edge * 100, pos=R.pos * 100,
                      side=[("buys low" if v >= 0.7 else "buys high" if v <= 0.3 else f"{v:.0%} buy low")
                            for v in R.low])
        st.dataframe(TT[["rank", "theme", "sharpe", "edge", "pos", "n", "side"]], hide_index=True,
                     use_container_width=True, height=min(38 + 35 * len(TT), 740),
                     column_config={"rank": "#", "theme": "Theme",
                                    "sharpe": st.column_config.NumberColumn("Median Sharpe vs eq-wt S&P",
                                                                            format="%.2f"),
                                    "edge": st.column_config.NumberColumn("Median avg 12-month edge (%)",
                                                                          format="%.1f"),
                                    "pos": st.column_config.NumberColumn("Median holds beating index (%)",
                                                                         format="%.0f"),
                                    "n": "Formulas", "side": "Side"})


@st.cache_data(show_spinner=False)
def load_series(mtime: float) -> dict:
    with gzip.open(SERIES, "rt", encoding="utf-8") as fh:
        d = json.load(fh)
    for k in ("v", "v6", "k", "k6"):  # v/v6: Sharpe at 12/6-month half-life; k/k6: Kelly (build_series.py)
        if k in d:
            v = np.asarray(d.pop(k), dtype=float)
            d[k] = np.where(v == -128, np.nan, v / (d["kstep"] if k.startswith("k") else d["step"]))
    return d


def direction(up: int, down: int) -> str:
    """Which end of the formula an area's formulas buy (Alex 2026-11-10: mark buy-high vs buy-low on hover)."""
    if up and not down:
        return "buys high"
    if down and not up:
        return "buys low"
    return f"{up} buy high, {down} buy low" if up or down else ""


def theme_text(keep: np.ndarray, gx, gy, regions, A: pd.DataFrame) -> np.ndarray:
    """Sheet hover (Alex 2026-11-10: "if I mouse over an area I want to see the general description on that theme"):
    the nearest region's 3 words, then the idea areas in that region (largest first). Each area belongs to the region
    with the nearest centre, which is how build_umap.py's k-means grouped them."""
    blank = np.full(keep.shape, "", dtype=object)
    if not regions:
        return blank
    rx = np.array([g["x"] for g in regions])
    ry = np.array([g["y"] for g in regions])
    own = np.argmin((A.x.to_numpy()[:, None] - rx) ** 2 + (A.y.to_numpy()[:, None] - ry) ** 2, axis=1)
    desc = []
    for j, g in enumerate(regions):
        names = A[own == j].sort_values("n", ascending=False).name.tolist()
        more = f"<br>and {len(names) - 6} more" if len(names) > 6 else ""
        tag = dict(zip(A.name, A.dir)) if "dir" in A else {}
        desc.append(f"<b>{html.escape(g['label'])}</b><br>" + "<br>".join(
            "· " + html.escape(a) + (f" <span style='color:#8E979F'>({tag[a]})</span>" if tag.get(a) else "")
            for a in names[:6]) + more)
    desc = np.array(desc, dtype=object)
    near_r = np.argmin((gx[None, :, None] - rx) ** 2 + (gy[:, None, None] - ry) ** 2, axis=2)
    return np.where(keep, desc[near_r], blank)


def hollow_scale() -> list:
    """Opacity by sheet value (Alex 2026-11-10: "middle 3rd transparent"): positions are shares of the sheet's own
    range (the surface's cmin..cmax is set to that range), the middle third see-through."""
    return [[0, 1], [0.2, 1], [1 / 3, 0.33], [2 / 3, 0.33], [0.78, 1], [1, 1]]  # middle at 33% (Alex 2026-11-10)


def fingerprint(rows: list) -> str:  # same as build_umap.py
    return hashlib.sha1("\n".join(r["expression"] for r in rows).encode("utf-8")).hexdigest()


@st.cache_data(show_spinner=False)
def sheet(x: tuple, y: tuple, z: tuple, bw: float, ratio: bool = False, n: int = 80, min_w: float = 5.0,
          bounds: tuple | None = None):
    """Gaussian kernel-weighted average of z on an n x n grid; blank where under 5 dots' worth of weight is near.
    ratio: the weighted average divided by the weighted spread (sd) of z nearby, so steady and high beats high and
    erratic (Alex 2026-11-10); the spread is floored at a quarter of z's overall sd so a few alike dots can't explode."""
    x, y, z = np.asarray(x), np.asarray(y), np.asarray(z)
    ok = np.isfinite(z)  # Over time keeps formulas with no value yet on this date; they do not shape the sheet
    x, y, z = x[ok], y[ok], z[ok]
    pad = 0.5  # fixed, so the grid (and the neighbour hover below) does not move with the smoothing
    x0, x1, y0, y1 = bounds or (x.min(), x.max(), y.min(), y.max())  # the whole map, so frames share one grid
    gx = np.linspace(x0 - pad, x1 + pad, n)
    gy = np.linspace(y0 - pad, y1 + pad, n)
    gz = np.full((n, n), np.nan)
    for i, yv in enumerate(gy):  # one grid row at a time keeps memory small
        w = np.exp(-((gx[:, None] - x[None, :]) ** 2 + (yv - y[None, :]) ** 2) / (2 * bw * bw))
        s = w.sum(1)
        m = (w @ z) / np.maximum(s, 1e-12)
        if ratio:
            sd = np.sqrt(np.maximum((w @ (z * z)) / np.maximum(s, 1e-12) - m * m, 0))
            m = m / np.maximum(sd, 0.25 * float(np.std(z)))
        gz[i] = np.where(s >= min_w, m, np.nan)
    return gx, gy, gz


@st.cache_data(show_spinner=False)
def near(x: tuple, y: tuple, lab: tuple, val: tuple, vname: str, keep: tuple, n: int = 80, k: int = 7):
    """Hover text for each grid point: the k nearest formulas on the map, grouped by area tag (count and values),
    nearest area first. Blank where the sheet is blank (keep)."""
    x, y, val = np.asarray(x), np.asarray(y), np.asarray(val)
    gx = np.linspace(x.min() - 0.5, x.max() + 0.5, n)
    gy = np.linspace(y.min() - 0.5, y.max() + 0.5, n)
    out = np.empty((n, n), dtype=object)
    for i, yv in enumerate(gy):
        d2 = (gx[:, None] - x[None, :]) ** 2 + (yv - y[None, :]) ** 2
        idx = np.argpartition(d2, k, axis=1)[:, :k]
        for j in range(n):
            if not keep[i][j]:
                out[i, j] = ""
                continue
            groups: dict = {}
            for m in idx[j][np.argsort(d2[j, idx[j]])]:
                groups.setdefault(lab[m], []).append(val[m])
            out[i, j] = "<br>".join(
                f"{html.escape(a)} · {vname} " + ", ".join(f"{v:.2f}" for v in vs) for a, vs in groups.items())
    return out


if not DATA.exists() and LOCAL:
    subprocess.run([sys.executable, str(EXPORT)], check=True)
d = load(DATA.stat().st_mtime)
df = pd.DataFrame(d["rows"])
df = df[df.t >= 1]  # training t below 1 is left out everywhere (Alex 2026-11-10); index = position in d["rows"]
ROWS = [d["rows"][i] for i in df.index]

from wordmark import svg as wordmark_svg  # noqa: E402  (hand-built faceted BLACKBIRD, Alex 2026-11-10)
_wm = "data:image/svg+xml," + quote(wordmark_svg(height=58))  # st.html strips inline svg; an img keeps it
st.html("<div class='logo'><span class='word'>Blackbird</span><span class='tag'>Edge Atlas</span></div>")
st.markdown("<p class='muted'>S&P 500 · top quintile, equal weight · 12-month hold vs equal-weighted index · "
            "training 1999–2022 · training t ≥ 1</p>", unsafe_allow_html=True)

seeds = df  # every formula on the page has training t >= 1

unseen = bool(d.get("unseen"))  # 2024+ always shown (Alex 2026-11-10); never used to pick


# ── idea landscape (Alex 2026-11-10: hypothesis + bet -> TF-IDF -> UMAP, height = t, kernel-weighted sheet) ────────
st.subheader("Idea landscape")
lm = load_map(UMAP.stat().st_mtime) if UMAP.exists() else None
if lm is None or "layouts" not in lm or lm["fingerprint"] != fingerprint(d["rows"]):
    st.markdown("<p class='muted'>The landscape is out of date with the formulas. Run build_umap.py to redraw it.</p>",
                unsafe_allow_html=True)
else:
    # Intro, view and formula filter sit behind Display settings with the rest (Alex 2026-11-10: "hide this behind
    # display settings too")
    phil_keep = None
    with st.container(key="phil_box"):
        pc = st.columns([6, 1.5, 1.7, 1.9], vertical_alignment="bottom")
        # saved screens, free to reload (Alex 2026-11-11: "philosophy screen the full period view by the large cap
        # growth mantra we've used as a recurring example"): data/phil_<name>.json from prep_phil.py / prep_video_notes.py
        saved = {"Large-cap growth": "lcg", "Oakmark value": "oakmark"}
        saved = {k: HERE / "data" / f"phil_{v}.json" for k, v in saved.items() if (HERE / "data" / f"phil_{v}.json").exists()}

        def load_saved() -> None:
            pick_ = st.session_state.get("phil_saved")
            if pick_ in saved:
                res_ = json.loads(saved[pick_].read_text(encoding="utf-8"))
                # the saved ids are positions in the item list of that run; re-key by (area, side) to this page's items
                by = {(g["area"], g["side"]): g for g in res_.get("groups", [])}
                res_["items"] = [{"id": it["id"], "fit": by[(it["area"], it["side"])]["fit"],
                                  "why": by[(it["area"], it["side"])].get("why", "")}
                                 for it in phil_items(ROWS) if (it["area"], it["side"]) in by]
                st.session_state["phil"] = {"text": res_.get("philosophy", pick_), "res": res_}
                st.session_state["phil_text"] = res_.get("philosophy", "")
            elif pick_ == "None":
                st.session_state.pop("phil", None)

        if saved:
            pc[3].selectbox("Saved screens", ["None"] + list(saved), key="phil_saved", on_change=load_saved,
                            label_visibility="collapsed", help="Reload a screen run earlier (no API call).")
        phil_text = pc[0].text_input(
            "Philosophy screen", key="phil_text",
            placeholder="Philosophy screen, e.g. GARP: rising sales and margins, moats, low leverage",
            label_visibility="collapsed",
            help=f"{PHIL_MODEL} marks each idea area (by side bought) aligned / partly / neutral / conflicts. ~$0.20.")
        run_phil = pc[1].button("Screen", key="phil_go", use_container_width=True, disabled=not phil_text.strip())
        if run_phil:
            if not api_key():
                st.error("No ANTHROPIC_API_KEY on this host.")
            else:
                try:
                    with st.spinner("Reading the philosophy against every idea area..."):
                        res = phil_screen(phil_text.strip(), json.dumps(phil_items(ROWS)))
                    st.session_state["phil"] = {"text": phil_text.strip(), "res": res}
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Screen failed: {exc}")
        ph = st.session_state.get("phil")
        if ph:
            res, its = ph["res"], phil_items(ROWS)
            fit = {x["id"]: x for x in res["items"]}
            keep_lv = pc[2].selectbox("Show", ["Aligned", "Aligned + partly", "All"], key="phil_show",
                                      label_visibility="collapsed")
            ok = {"Aligned": {"aligned"}, "Aligned + partly": {"aligned", "partly"}}.get(keep_lv)
            tagged = [dict(it, fit=fit.get(it["id"], {}).get("fit", "neutral"),
                           why=fit.get(it["id"], {}).get("why", "")) for it in its]
            if ok:
                phil_keep = {(t["area"], t["side"]) for t in tagged if t["fit"] in ok}
            cnt = {k: sum(t["fit"] == k for t in tagged) for k in ("aligned", "partly", "neutral", "conflicts")}
            st.markdown(f"<p class='muted'>{html.escape(' · '.join(res.get('tenets', [])))} — "
                        f"{cnt['aligned']} aligned · {cnt['partly']} partly · {cnt['neutral']} neutral · "
                        f"{cnt['conflicts']} conflict</p>", unsafe_allow_html=True)
            with st.expander("Screen results", expanded=False):
                order = {"aligned": 0, "partly": 1, "neutral": 2, "conflicts": 3}
                T = pd.DataFrame(tagged).assign(o=lambda t: t.fit.map(order)).sort_values(["o", "n"],
                                                                                         ascending=[True, False])
                st.dataframe(T[["fit", "area", "side", "family", "n", "why"]].rename(columns={
                    "fit": "Fit", "area": "Idea area", "side": "Side", "family": "Family", "n": "Formulas",
                    "why": "Why"}), hide_index=True, use_container_width=True, height=360)
    views = ["What persisted", "Over time", "Explore"] if SERIES.exists() else ["What persisted", "Explore"]
    if FULL.exists():
        views.append("Full period")
    vrow = st.columns([3, 1.6], vertical_alignment="center")  # view picker + top-down toggle (Alex 2026-11-10)
    view = vrow[0].radio("View", views, horizontal=True, key="land_view", label_visibility="collapsed",
                    help="What persisted: every formula with training t of at least 1 (low-coverage ones included); "
                         "dots and sheet are their 2024+ Sharpe (Jan 2024 to Sep 2025 formations, after training). "
                         "Over time: every formula, valued by its trailing Sharpe on the date you pick. "
                         "Explore: every control.")
    persisted = view == "What persisted"
    box = st.expander("Display settings", expanded=False)
    box.markdown("<p class='muted'>Dots: formulas, placed by idea. Diamonds/knots: idea areas. Sheet: best-fit "
                 "surface; red = strongest.</p>", unsafe_allow_html=True)
    overtime = view == "Over time"
    if overtime:
        ts = load_series(SERIES.stat().st_mtime)
        # Play (Alex 2026-11-10: "a play button so the over time view can slowly step through the diff date
        # slices"): each rerun moves the date on by the chosen step, then reruns again after a short pause.
        ss = st.session_state
        if ss.get("land_date") not in ts["dates"]:
            ss["land_date"] = ts["dates"][-1]
        if ss.get("ot_play"):
            j = ts["dates"].index(ss["land_date"]) + int(ss.get("ot_step", 3))
            if j >= len(ts["dates"]):
                ss["ot_play"] = False
                j = len(ts["dates"]) - 1
            ss["land_date"] = ts["dates"][j]
        # < play > (Alex 2026-11-10: "a forward/back one increment on each side of the play button"): the arrows move
        # one step of the chosen size and stop any play-through.
        pcol = st.columns([0.55, 0.8, 0.55, 1.1, 1.5, 1.1, 4.6])

        def nudge(k: int) -> None:
            ss["ot_play"] = False
            j = ts["dates"].index(ss["land_date"]) + k * int(ss.get("ot_step", 3))
            ss["land_date"] = ts["dates"][min(max(j, 0), len(ts["dates"]) - 1)]

        pcol[0].button("‹", key="ot_back", use_container_width=True, on_click=nudge, args=(-1,), help="Back one step")
        if pcol[1].button("❚❚" if ss.get("ot_play") else "▶", key="ot_btn", use_container_width=True,
                          help="Pause" if ss.get("ot_play") else "Play"):
            if not ss.get("ot_play") and ss["land_date"] == ts["dates"][-1]:
                ss["land_date"] = ts["dates"][0]  # at the end: start again from the first date
            ss["ot_play"] = not ss.get("ot_play")
            st.rerun()
        pcol[2].button("›", key="ot_fwd", use_container_width=True, on_click=nudge, args=(1,), help="Forward one step")
        pcol[3].selectbox("Step", [1, 3, 6, 12], index=1, key="ot_step", format_func=lambda m: f"{m} mo",
                          label_visibility="collapsed")
        hl_opts = [f"{ts['halflife']} mo half-life"] + ([f"{ts['fast_halflife']} mo half-life"] if "v6" in ts else [])
        hl_pick = pcol[4].selectbox("Weighting", hl_opts, key="ot_hl", label_visibility="collapsed",
                                    help="How fast old holds fade from each formula's trailing Sharpe. 6 months "
                                         "picks up areas heating or cooling sooner; 12 months is steadier.")
        fast = hl_pick.startswith(str(ts.get("fast_halflife")))
        kelly = "k" in ts and st.session_state.get("ot_measure", "Sharpe") == "Kelly"
        tv = ts[("k6" if fast else "k") if kelly else ("v6" if fast and "v6" in ts else "v")]
        pcol[5].selectbox("Measure", ["Sharpe", "Kelly"], key="ot_measure", label_visibility="collapsed",
                          help="Sharpe: mean / sd of the 12-month edges. Kelly: mean / variance.")
        when = pcol[6].select_slider("Date", ts["dates"], key="land_date", label_visibility="collapsed",
                                help="Each formula's value on this date: its Sharpe over 12-month holds already "
                                     f"finished by then, weighting recent ones more (weight halves every "
                                     f"{ts['halflife']} months).")
        tv = tv[df.index.to_numpy()]  # series rows follow d["rows"]
        df = df.assign(trail=tv[:, ts["dates"].index(when)],
                       trail_any=np.isfinite(tv).any(axis=1))  # same dots on every date, so frames glide
        box.markdown(f"<p class='muted'><b>Over time.</b> Trailing Sharpe on {when}, completed holds only "
                     f"({ts['have']:,} formulas with history).</p>", unsafe_allow_html=True)
    if persisted:
        box.markdown("<p class='muted'><b>What persisted.</b> 2024+ Sharpe (out of sample) of formulas above the "
                     "training-t cut.</p>", unsafe_allow_html=True)
    tcut = 1.0
    if True:  # every view (Alex 2026-11-10: "I also need a training t>1.6"; t < 1 never shown)
        # the bars used in past runs (Alex 2026-11-10): 1 = this run's seed rule, 1.645 = the horse race's out-of-
        # sample hit bar, 1.96 = the horse race's training hit bar (HORSERACE_SPEC.md)
        cuts = ["Training t ≥ 1", "Training t ≥ 1.645", "Training t ≥ 1.96"]
        pick_cut = box.radio("Which formulas", cuts, horizontal=True, key=f"land_cut2_{view}",
                            help="Filter on training t only (formations 1999 to 2022); low-coverage formulas "
                                 "included. 2024+ is never used to choose.")
        tcut = float(pick_cut.split("≥ ")[1])
    if view == "Full period":
        FL = df[df.t >= tcut]
        if phil_keep is not None:
            side_ = np.where(FL.bet.str.startswith("higher"), "buys high", "buys low")
            FL = FL[[(a, s_) in phil_keep for a, s_ in zip(FL.area, side_)]]
        full_period_view(FL, lm["layouts"]["islands"], lm)
        st.stop()
    hopts = {"Training Sharpe": ("sharpe", 1.0), "Training t": ("t", 1.0)}
    if overtime:
        hopts["Trailing Kelly" if st.session_state.get("ot_measure") == "Kelly" else "Trailing Sharpe"] = ("trail", 1.0)
    if unseen or persisted:
        hopts |= {"2024+ Sharpe": ("unseen_sharpe", 1.0), "2024+ edge (%)": ("unseen_mean", 100.0)}
    t0 = box.columns([1.3, 2.2, 2.2])
    mode = t0[0].radio("Layout", ["Islands", "UMAP"], horizontal=True, key="land_lay",
                       help="A/B (Alex 2026-11-10). Islands: areas placed by how alike their ideas' words are, each "
                            "area's ideas in a tight cluster around its spot. UMAP: every formula placed by its words, "
                            "pulled toward its area by the slider.")
    pulls = sorted((k for k, v in lm["layouts"].items()  # a layout UMAP left blank (pull 1 did) is skipped
                    if k != "islands" and np.isfinite(np.asarray(v["x"], dtype=float)).all()), key=float)
    if mode == "UMAP":
        pull = t0[1].select_slider("Pull toward idea area", pulls,
                                   value="0.5" if "0.5" in pulls else pulls[len(pulls) // 2], key="land_pull",
                                   help="How hard formulas of one idea area are drawn together. 0: placed by their "
                                        "words alone. 1: each area packed together. Each setting is built ahead of "
                                        "time (build_umap.py).")
        lay = lm["layouts"][pull]
    else:
        lay = lm["layouts"].get("islands") or lm["layouts"][pulls[-1]]
    ratio = (not persisted) and (not overtime) and t0[2].radio(
        "Sheet and knots show", ["Average ÷ spread", "Average"], horizontal=True, key="land_score",
        help="Average ÷ spread: the nearby average divided by how much it varies across nearby variations, so steady "
             "and high beats high and erratic. Average: the plain average.") == "Average ÷ spread"
    c = box.columns([2, 1.4, 1.4, 1.4, 1.1])
    hname = "2024+ Sharpe" if persisted else (
        "Trailing Kelly" if st.session_state.get("ot_measure") == "Kelly" else "Trailing Sharpe") if overtime else c[0].radio(
        "Height", list(hopts), horizontal=True, key="land_h",
        help="2024+ choices appear when 2024+ results are revealed above.")
    bwp = c[1].slider("Smoothing", 0.5, 8.0, 4.0 if persisted or overtime or mode != "Islands" else 2.0, 0.25,
                      format="%.2f%%", key=f"land_bwp_{mode}_{persisted}",
                      help="Width of the averaging window, as a share of the map's width. Wider gives a calmer "
                           "sheet; narrower follows single areas.")
    # Dots are one formula's raw value; average ÷ spread is in other units, so the two are never drawn together
    # (Alex 2026-11-10: "if you can't have them in the same units don't show them at the same time").
    dots = c[4].checkbox("Show dots", value=not ratio, key=f"land_dots_{ratio}", disabled=ratio,
                         help="Only with Average: dots are each formula's own value, in the same units as the sheet. "
                              "Average ÷ spread is a different unit, so dots are hidden there.") and not ratio
    explode = c[2].radio("Sheet and dots", ["Together", "Exploded"], horizontal=True, key="land_mode",
                         disabled=ratio or persisted or overtime,
                         help="Together: one height scale, the sheet at its real value among the dots. Exploded: the "
                              "sheet in its own band under the dots, stretched so its hills and dips stand out.")
    explode = explode == "Exploded" and not ratio and not persisted and not overtime
    stretch = (c[2].slider("Sheet stretch", 1.0, 10.0, 3.0, 0.5, key="land_k",
                           help="Exploded view: the sheet is drawn this many times taller than its value. Hover or the "
                                "colour bar give its real value.") if explode else 1.0)
    which = "t cut"
    web = True  # area knots always shown; the threads between them are optional (Alex 2026-11-10: "toggle, default off")
    threads = c[4].checkbox("Show threads", value=False, key="land_threads",
                            help="Lines joining each idea area to its 3 most similar areas by words, where the two also "
                                 "sit close on the map.")
    scale_name = "Lunar"  # the only scale (Alex 2026-11-10: "keep lunar as only option, lose selector")
    labels = c[4].radio("Labels", ["Themes on hover", "Themes", "Areas", "None"], key="land_labels",
                        help="Themes: nearby idea areas grouped into 20 regions, each named by the 3 words that set "
                             "its ideas apart from the rest. Areas: every idea area's name at its knot (crowded; zoom "
                             "in).")
    hollow = c[2].checkbox("Clear the middle", value=True, key="land_hollow3",
                           help="The middle third of the sheet's height range is mostly see-through (33%): top third orange, "
                                "bottom third pale grey.")
    style = c[3].radio("Draw as", ["Sliced sheet", "Contour lines", "Sheet"], key="land_style",
                       help="Sliced sheet: the solid surface with dark lines of equal height cut into it. Contour "
                            "lines: only the lines, so the dots stay visible. Sheet: the plain surface.")
    col, scale = hopts[hname]
    L = df.assign(ux=np.asarray(lay["x"])[df.index], uy=np.asarray(lay["y"])[df.index], idea=df.hypothesis.fillna("") + " Bet: " + df.bet + ".")
    L = L[(L.trail_any if overtime else L[col].notna()) & (L.t >= tcut)]
    if phil_keep is not None:  # philosophy screen: only the (area, side) groups it kept
        side_ = np.where(L.bet.str.startswith("higher"), "buys high", "buys low")
        L = L[[(a, s_) in phil_keep for a, s_ in zip(L.area, side_)]]
    x, y, z = L.ux.to_numpy(), L.uy.to_numpy(), L[col].to_numpy() * scale
    bw = bwp / 100 * max(np.ptp(lay["x"]), np.ptp(lay["y"]))
    gx, gy, gz = sheet(tuple(x), tuple(y), tuple(z), bw, ratio, min_w=2.0,
                       bounds=(min(lay["x"]), max(lay["x"]), min(lay["y"]), max(lay["y"])))
    sname = f"{hname} {'avg ÷ spread' if ratio else 'average'}"
    lim = float(np.nanpercentile(np.abs(z), 97)) or 1.0  # dots
    slim = float(np.nanpercentile(np.abs(gz), 99)) or 1.0  # sheet: own range, so its hills and dips show
    # Two height scales on one axis (plotly has one z axis per 3D plot): dots in their own units on top, the sheet in
    # its own band underneath, stretched; each band gets its own tick labels.
    s0, s1 = float(np.nanmin(gz)), float(np.nanmax(gz))
    d0, d1 = (float(np.nanpercentile(z, 1)), float(np.nanpercentile(z, 99))) if dots else (0.0, 0.0)
    base = d0 - 0.15 * (d1 - d0) - stretch * (s1 - s0) if dots and explode else s0
    to_band = lambda v: base + stretch * (np.asarray(v) - s0)  # noqa: E731  (Together: the identity)
    hi_ = L.bet.str.startswith("higher").groupby(L.area).sum()
    lo_ = (~L.bet.str.startswith("higher")).groupby(L.area).sum()
    areas_dir = pd.DataFrame(lm["areas"]).assign(x=lay["ax"], y=lay["ay"])
    areas_dir["dir"] = [direction(int(hi_.get(a, 0)), int(lo_.get(a, 0))) for a in areas_dir.name]
    figure = go.Figure()
    figure.add_trace(go.Surface(
        x=gx, y=gy, z=to_band(gz), surfacecolor=gz, customdata=gz, colorscale=SHEET_SCALES[scale_name],
        text=np.where(np.isnan(gz), "", theme_text(~np.isnan(gz), gx, gy, lay.get("regions"), areas_dir)
                      + "<br><span style='color:#8C9096'>sheet " + sname.lower() + " "
                      + np.char.mod("%.2f", np.nan_to_num(gz)).astype(object) + "</span>"), cmin=s0, cmax=s1, opacity=0.95, showscale=True, showlegend=False,
        hidesurface=style == "Contour lines",
        **({"opacityscale": hollow_scale()} if hollow else {}),
        colorbar=dict(title=dict(text=f"Sheet: {sname}", font=dict(color=BRONZE)), tickfont=dict(color=BRONZE_DIM),
                      thickness=12, len=0.6, outlinewidth=0),
        lighting=dict(ambient=0.72, diffuse=0.55, specular=0.12, roughness=0.6, fresnel=0.04),
        lightposition=dict(x=1500, y=-800, z=2500),
        contours=dict(z=(dict(show=True, usecolormap=True, project_z=False, width=4, start=-slim, end=slim,
                              size=slim / 6) if style == "Contour lines"
                         else dict(show=True, usecolormap=False, color=FIELD, project_z=False, width=3,
                                   start=-slim, end=slim, size=slim / 6) if style == "Sliced sheet"
                         else dict(show=True, usecolormap=True, project_z=True, width=1))),
        hovertemplate="%{text}<extra></extra>"))
    marks = (1.6, 2.0) if col == "t" and not ratio else ()  # Alex 2026-11-10: mark t = 1.6 and t = 2 (t units only)
    for lev, colr in zip(marks, (BRONZE_HI, "#FFF0C8")):
        figure.add_trace(go.Surface(
            x=gx[[0, -1]], y=gy[[0, -1]], z=np.full((2, 2), lev), colorscale=[[0, colr], [1, colr]], showscale=False,
            opacity=0.13, hoverinfo="skip", contours=dict(x=dict(show=True, color=colr, width=2, start=gx[0],
                                                                  end=gx[-1], size=gx[-1] - gx[0]),
                                                           y=dict(show=True, color=colr, width=2, start=gy[0],
                                                                  end=gy[-1], size=gy[-1] - gy[0]))))
        figure.add_trace(go.Scatter3d(x=[gx[-1]], y=[gy[0]], z=[lev], mode="text", text=[f"t = {lev:g}"],
                                      textposition="middle right", textfont=dict(color=colr, size=12),
                                      hoverinfo="skip", showlegend=False))
    if web:
        A = pd.DataFrame(lm["areas"]).assign(x=lay["ax"], y=lay["ay"])
        g = L.groupby("area")[col]
        floor = 0.25 * float(np.std(z))
        A["med"] = A.name.map((g.mean() / np.maximum(g.std(), floor / scale) if ratio else g.mean()) * (1 if ratio else scale))
        A["cnt"] = A.name.map(g.size()).fillna(0).astype(int)
        A["seeds"] = A.cnt
        best = L.sort_values(col, ascending=False).drop_duplicates("area").set_index("area")
        A["best"] = A.name.map(best.name.fillna("Unnamed")).fillna("–")
        A["bestv"] = A.name.map(best[col] * scale)
        ix = np.clip(np.searchsorted(gx, A.x), 0, len(gx) - 1)
        iy = np.clip(np.searchsorted(gy, A.y), 0, len(gy) - 1)
        sz = gz[iy, ix]
        # on the sheet where it exists; where it is blank (few formulas near), at the area's own value instead of
        # dropping to the floor (2026-11-10 fix: knots and threads were diving to the sheet's lowest point)
        own = to_band(A.med.fillna(0).to_numpy()) if not ratio else to_band(np.clip(A.med.fillna(0).to_numpy(), s0, s1))
        A["z"] = np.where(np.isnan(sz), own, to_band(np.nan_to_num(sz))) + 0.04 * stretch * (s1 - s0)
        on = set(A.index[A.cnt > 0])
        lx, ly, lz = [], [], []
        far = 0.12 * max(np.ptp(lay["x"]), np.ptp(lay["y"]))  # threads only between areas that also sit near each other
        for i, j, _ in lm["links"]:
            if i not in on or j not in on or np.hypot(A.x[i] - A.x[j], A.y[i] - A.y[j]) > far:
                continue
            lx += [A.x[i], A.x[j], None]
            ly += [A.y[i], A.y[j], None]
            lz += [A.z[i], A.z[j], None]
        if threads:
            figure.add_trace(go.Scatter3d(x=lx, y=ly, z=lz, mode="lines", hoverinfo="skip",
                                      line=dict(color="rgba(240,196,106,0.12)", width=1.2)))
        A = A[A.cnt > 0]
        alim = float(np.nanpercentile(np.abs(A.med), 98)) or 1.0
        figure.add_trace(go.Scatter3d(
            x=A.x, y=A.y, z=A.z, mode="markers",
            # same scale and range as the sheet, so a knot's colour means what the ground under it means
            # (2026-11-10 fix: knots used a separate zero-centred range and read as random colours)
            marker=dict(size=3 + 0.9 * np.sqrt(A.cnt), color=A.med, colorscale=SHEET_SCALES[scale_name],
                        cmin=s0, cmax=s1,
                        opacity=0.95, line=dict(color=GROUND, width=1)),
            customdata=np.stack([A.name, A.name.map(dict(zip(areas_dir.name, areas_dir.dir))).fillna("")], axis=1),
            hovertemplate="<b>%{customdata[0]}</b><br><span style='color:#8E979F'>%{customdata[1]}</span>"
                          "<extra></extra>"))  # Alex 2026-11-10: knot hover = title (+ which end it buys)
    if labels in ("Themes", "Areas"):  # Alex 2026-11-10: "label areas based on the core theme or just which idea area they are in"
        P = pd.DataFrame(lm["areas"]).assign(x=lay["ax"], y=lay["ay"])
        P = P[P.name.isin(L.area)]
        if labels == "Themes" and lay.get("regions"):  # build_umap.py regions(): nearby areas grouped, top words
            P = pd.DataFrame(lay["regions"]).rename(columns={"label": "name"})
        jx = np.clip(np.searchsorted(gx, P.x), 0, len(gx) - 1)
        jy = np.clip(np.searchsorted(gy, P.y), 0, len(gy) - 1)
        hz = gz[jy, jx]
        top = float(to_band(s1)) if np.isfinite(s1) else 0.0
        pz = np.where(np.isnan(hz), top, to_band(np.nan_to_num(hz))) + 0.12 * stretch * (s1 - s0)
        figure.add_trace(go.Scatter3d(
            x=P.x, y=P.y, z=pz, mode="text", text=P.name, hoverinfo="skip",
            textfont=dict(color="#FFF0C8" if labels == "Themes" else BRONZE_HI, size=12 if labels == "Themes" else 9,
                          family="Bahnschrift, Segoe UI, sans-serif")))
    if dots:
        figure.add_trace(go.Scatter3d(
            x=x, y=y, z=z, mode="markers",
            marker=dict(size=1.6, color=z, colorscale=SHEET_SCALES[scale_name], cmin=s0, cmax=s1, opacity=0.18),
            customdata=np.stack([L.name.fillna("Unnamed"), L.area, L.idea.str.slice(0, 160),
                                 np.where(L.bet.str.startswith("higher"), "buys the highest fifth of the formula",
                                          "buys the lowest fifth of the formula")], axis=1),
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>%{customdata[3]}<br>" + hname
                          + " %{z:.2f}<br><i>%{customdata[2]}…</i><extra></extra>"))
    def nice(lo: float, hi: float, n: int = 4) -> np.ndarray:
        if not (np.isfinite(lo) and np.isfinite(hi)):
            return np.array([])
        raw = (hi - lo) / n or 1.0
        step = min((m * 10 ** np.floor(np.log10(raw)) for m in (1, 2, 2.5, 5, 10)
                    if m * 10 ** np.floor(np.log10(raw)) >= raw))
        return np.arange(np.ceil(lo / step) * step, hi + 1e-9, step)
    sv = nice(s0, s1, 6)
    tickv, tickt = (list(to_band(sv)), [f"{'sheet ' if explode else ''}{v + 0.0:.2f}" for v in sv]) if explode or not dots else ([], [])
    if dots:
        dv = nice(d0, max(d1, *marks) if marks else d1, 5)
        dv = [v for v in dv if all(abs(v - m) > 0.15 for m in marks)]
        tickv, tickt = tickv + list(dv) + list(marks), tickt + [f"{v:g}" for v in dv] + [f"t = {m:g}" for m in marks]
    zr = [min(float(to_band(s0)), d0 if dots else np.inf) - 0.1, max(tickv + [d1, float(to_band(s1)), *marks]) + 0.1]
    ax = dict(showbackground=False, showspikes=False, gridcolor=LINE, zerolinecolor=BRONZE_DIM, color=BRONZE_DIM, title="",
              showticklabels=False)
    figure.update_layout(
        height=900, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor=GROUND, font=dict(color=BRONZE, family='"Helvetica Neue", Helvetica, Arial, sans-serif'), showlegend=False,
        scene=dict(xaxis=ax, yaxis=ax, zaxis=ax | dict(showticklabels=True, title="", range=zr, tickvals=tickv, ticktext=tickt),
                   aspectmode="manual", aspectratio=dict(x=1.4, y=1.4, z=0.8 if dots and explode else 0.55),
                   camera=dict(eye=dict(x=1.35, y=-1.35, z=0.85)), bgcolor=GROUND),
        hoverlabel=dict(bgcolor=CARD, bordercolor=BRONZE, font=dict(color=BRONZE_HI)))
    # One plot at a time (Alex 2026-11-10: "a toggle to selector top down view instead of two plots ... just above
    # the 3d box")
    flat_on = vrow[1].toggle("Top-down select view", value=True, key="land_flat_on",  # default (Alex 2026-11-10)
                        help="Off: the 3D landscape. On: the same map flat from above, where a lasso or box "
                             "lists the formulas inside.")
    if not flat_on:
        click3d(fig=figure.to_json(), height=900, key=f"land_plot_{view}", default=None)
    else:

        # Select to table (Alex 2026-11-10: "a select area to table, instead of click to table"). Plotly has no box or
        # lasso select in 3D, so the same map is drawn flat from above: the sheet as filled contours, the formulas as dots,
        # the areas as knots. A lasso or box on it lists the formulas inside (a knot inside adds all of its area's).
        st.markdown("<p class='muted'>Drag a box to list formulas; double-click to clear.</p>", unsafe_allow_html=True)
        flat = go.Figure()
        flat.add_trace(go.Contour(x=gx, y=gy, z=gz, colorscale=SHEET_SCALES[scale_name], zmin=s0, zmax=s1,
                                  contours=dict(coloring="fill", showlines=True), line=dict(color=FIELD, width=0.6),
                                  opacity=0.85, showscale=True, hoverinfo="skip",
                                  colorbar=dict(title=dict(text=f"{hname}<br>(sheet)", font=dict(color=BRONZE)),
                                                tickfont=dict(color=BRONZE_DIM), thickness=12, len=0.6,
                                                outlinewidth=0)))
        flat.add_trace(go.Scattergl(x=x, y=y, mode="markers", name="formulas",
                                    marker=dict(size=4, color=z, colorscale=SHEET_SCALES[scale_name], cmin=s0, cmax=s1,
                                                line=dict(color=BLACK, width=0.4), opacity=0),
                                    selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=0)),
                                    hoverinfo="skip",  # hidden until a box selects them (Alex 2026-11-10)
                                    customdata=np.stack([L.name.fillna("Unnamed"), L.area,
                                                         np.char.mod("%.2f", np.nan_to_num(z))], axis=1),
                                    hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>" + hname
                                                  + " %{customdata[2]}<extra></extra>"))
        kn = areas_dir[areas_dir.name.isin(L.area)]
        flat.add_trace(go.Scattergl(x=kn.x, y=kn.y, mode="markers", name="areas",
                                    marker=dict(size=4, color="rgba(255,255,255,.55)"),  # small soft dots (Alex 2026-11-10)
                                    customdata=kn[["name"]].to_numpy(),
                                    hovertemplate="<b>%{customdata[0]}</b><extra></extra>"))
        flat.update_layout(height=860, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor=GROUND, plot_bgcolor=GROUND,
                           showlegend=False, dragmode="select", font=dict(color=BRONZE, family='"Helvetica Neue", Helvetica, Arial, sans-serif'),
                           xaxis=dict(visible=False, range=[float(np.min(x)) - .02 * np.ptp(x), float(np.max(x)) + .02 * np.ptp(x)]),
                       yaxis=dict(visible=False, scaleanchor="x", range=[float(np.min(y)) - .02 * np.ptp(y), float(np.max(y)) + .02 * np.ptp(y)]),
                           hoverlabel=dict(bgcolor=CARD, bordercolor=BRONZE, font=dict(color=BRONZE_HI)))
        ev = st.plotly_chart(flat, use_container_width=True, on_select="rerun", selection_mode=("box", "lasso"),
                             key=f"land_flat_{view}", config={"displaylogo": False})
        try:
            pts = ev.selection.points
        except AttributeError:
            pts = []
        pick_rows = sorted({int(q["point_index"]) for q in pts if q.get("curve_number") == 1})
        pick_areas = {kn.name.iloc[int(q["point_index"])] for q in pts if q.get("curve_number") == 2}
        if pick_rows or pick_areas:
            Q = L.iloc[pick_rows]
            if pick_areas:
                Q = pd.concat([Q, L[L.area.isin(pick_areas)]])
            Q = Q[~Q.index.duplicated()].sort_values(col, ascending=False)
            st.markdown(f"<div class='card'><b>{len(Q):,} formulas selected</b> · {Q.area.nunique()} idea areas · "
                        f"median {hname.lower()} {Q[col].median() * scale:.2f}</div>", unsafe_allow_html=True)
            tab = pd.DataFrame({"Name": Q.name.fillna("Unnamed"), "Idea area": Q.area, "Reads as": Q.reads, "Bet": Q.bet,
                                hname: Q[col] * scale, "Training t": Q.t, "Training Sharpe": Q.sharpe})
            tab = tab.loc[:, ~tab.columns.duplicated()]
            st.dataframe(tab, hide_index=True, use_container_width=True, height=min(480, 38 + 35 * len(tab)),
                         column_config={k: st.column_config.NumberColumn(k, format="%.2f") for k in
                                        (hname, "Training t", "Training Sharpe") if k in tab})

    notes = [f"{len(L):,} formulas with a {hname.lower()}.",
             f"Words: TF-IDF on {lm['vocab']:,} terms, cut to 100 dimensions.",
             ("Islands: each area's average word vector goes through UMAP to place the areas; its ideas spread around "
              "that spot by their own words." if mode == "Islands" else
              f"UMAP to two dimensions with each formula's idea area as a label (pull {pull} on a 0 to 1 scale)."),
             "The map ignores results; only the height and colour use them.",
             "Where few dots are near, the sheet is left blank.",
             "Knots, dots and sheet share one colour scale over the sheet's own low-to-high range."]
    if threads:
        notes.append(f"Threads: each area joins its {lm.get('web_k', 3)} most similar areas by words, drawn only where "
                     "the two also sit close on the map.")
    if ratio:
        notes.append("Average ÷ spread uses a spread of at least a quarter of the overall spread, so a few "
                     "look-alike formulas can't blow it up.")
    if explode:
        notes.append(f"Exploded: dots on top in their own units, the sheet underneath, drawn {stretch:g}x taller than "
                     "its value (ticks marked 'sheet' and its colour bar give the real value).")
    with st.expander("Details", expanded=False):  # Alex 2026-11-10: bullet points behind an expander
        st.markdown("\n".join(f"- {n}" for n in notes))
    if overtime and st.session_state.get("ot_play"):  # next frame of the play-through
        import time
        time.sleep(0.8)
        st.rerun()

    # ── does it hold up? (Alex 2026-11-10: "robustly promising in training ... and then actually holds up in the test
    # sample"). Each idea area: training score across its variations against its 2024+ score, Sharpe.
    if unseen:
        # one dot per idea area x side bought, buy-low marked (Alex 2026-11-10: "how does the hold up chart handle buy
        # low factors ... pls fix"); collapsed so it stays out of the way of the formula view
        hold = st.expander("Does it hold up? Training vs 2024+, by idea area and side", expanded=False)
        T = df[df.sharpe.notna() & (df.t >= tcut)].copy()
        T["side"] = np.where(T.bet.str.startswith("higher"), "buys high", "buys low")
        key = [T.area, T.side]

        def side_score(v: pd.Series) -> pd.DataFrame:
            g = v.groupby([T.area.loc[v.index], T.side.loc[v.index]])
            sc = g.mean() / np.maximum(g.std(), 0.25 * float(v.std())) if ratio else g.mean()
            return pd.DataFrame({"score": sc, "n": g.count()})

        H = side_score(T.sharpe).join(side_score(T.unseen_sharpe.dropna()), lsuffix="_tr", rsuffix="_te", how="inner")
        H = H[(H.n_tr >= 3) & (H.n_te >= 3)].reset_index().rename(columns={"level_0": "area", "level_1": "side"})
        H = H.merge(df.groupby("area").family.first().rename("family"), left_on="area", right_index=True, how="left")
        rho = H.score_tr.corr(H.score_te, method="spearman") if len(H) > 5 else float("nan")
        hl = float(np.nanpercentile(np.abs(H.score_te), 97)) or 1.0
        f2 = go.Figure()
        for Hs in (H,):  # one marker style; the side bought is in the tooltip (Alex 2026-11-10)
            f2.add_trace(go.Scatter(
                x=Hs.score_tr, y=Hs.score_te, mode="markers",
                marker=dict(size=9, color=Hs.score_te, colorscale=SCALE,
                            cmin=-hl, cmax=hl, opacity=0.9, line=dict(color=BLACK, width=1)),
                customdata=np.stack([Hs.area, Hs.family.fillna(""), Hs.n_tr, Hs.n_te, Hs.side], axis=1),
                hovertemplate="<b>%{customdata[0]}</b> (%{customdata[4]})<br>%{customdata[1]}<br>training %{x:.2f} "
                              "(%{customdata[2]} formulas)<br>2024+ %{y:.2f} (%{customdata[3]})<extra></extra>"))
        f2.add_vline(x=0, line=dict(color=BRONZE_DIM, width=1, dash="dot"))
        f2.add_hline(y=0, line=dict(color=BRONZE_DIM, width=1, dash="dot"))
        axs = dict(gridcolor=LINE, zerolinecolor=LINE, color=BRONZE_DIM)
        lab = "avg ÷ spread" if ratio else "average"
        f2.update_layout(height=520, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor=GROUND, plot_bgcolor=GROUND,
                         font=dict(color=BRONZE, family='"Helvetica Neue", Helvetica, Arial, sans-serif'),
                         showlegend=False,
                         xaxis=axs | dict(title=f"Training Sharpe, {lab}"), yaxis=axs | dict(title=f"2024+ Sharpe, {lab}"),
                         hoverlabel=dict(bgcolor=CARD, bordercolor=BRONZE, font=dict(color=BRONZE_HI)))
        hold.plotly_chart(f2, use_container_width=True, config={"displaylogo": False})

fam = []  # families, most seeds first (feeds the Family filter)
for f in d["families"]:
    s_ = seeds[seeds.family == f]
    fam.append({"family": f, "seeds": len(s_)})
fam.sort(key=lambda r: (-r["seeds"], r["family"]))

# ── formula list ─────────────────────────────────────────────────────────────
st.subheader("Formulas")
c = st.columns([3, 2, 1.4])
q = c[0].text_input("Search", placeholder="words or variables, e.g. R&D cash flow, or xrd")
opts = ["All families"] + [r["family"] for r in fam]
if st.session_state.get("fam") not in opts:
    st.session_state["fam"] = "All families"
fpick = c[1].selectbox("Family", opts, key="fam")
v = df
if fpick != "All families":
    v = v[v.family == fpick]
if q.strip():
    hay = (v.reads.fillna("") + " " + v.expression + " " + v.name.fillna("") + " " + v.hypothesis.fillna("") + " "
           + v.area.fillna("") + " " + v.family).str.lower()
    for w in q.lower().split():
        v = v[hay.str.contains(w, regex=False)]
        hay = hay[v.index]
v = v.sort_values("t", ascending=False)
st.markdown(f"<p class='muted'>{len(v):,} formulas. Click a row for its idea and exact formula.</p>",
            unsafe_allow_html=True)
show = pd.DataFrame({"Reads as": v.reads, "Bet": v.bet, "Area": v.area, "Family": v.family, "t": v.t,
                     "Sharpe": v.sharpe, "Edge a year": v["mean"] * 100, "Coverage": v.coverage * 100})
fmt = {"t": st.column_config.NumberColumn("t", format="%.2f", help="Non-overlapping t of the 12-month edge, training"),
       "Sharpe": st.column_config.NumberColumn("Sharpe", format="%.2f",
                                               help="Mean / sd of the overlapping 12-month edge, training"),
       "Edge a year": st.column_config.NumberColumn("Edge a year", format="%.1f%%",
                                                    help="Average 12-month return above the equal-weighted S&P 500"),
       "Coverage": st.column_config.NumberColumn("Coverage", format="%.0f%%",
                                                 help="Share of S&P 500 market cap the formula can score"),
       "Reads as": st.column_config.TextColumn("Reads as", width="large")}
if unseen:
    for k, lab in (("unseen_mean", "2024+ edge"), ("unseen_sharpe", "2024+ Sharpe")):
        if k in v:
            show[lab] = v[k] * (100 if k == "unseen_mean" else 1)
    fmt["2024+ edge"] = st.column_config.NumberColumn("2024+ edge", format="%.1f%%")
    fmt["2024+ Sharpe"] = st.column_config.NumberColumn("2024+ Sharpe", format="%.2f")
sel = st.dataframe(show, hide_index=True, use_container_width=True, height=520, column_config=fmt,
                   on_select="rerun", selection_mode="single-row", key="table")
try:
    rows = sel.selection.rows
except AttributeError:
    rows = []
if rows:
    r = v.iloc[rows[0]]
    st.markdown(f"<div class='card'><b>{r['name'] or 'Unnamed'}</b> · {r.family} · {r.area}<br>{r.hypothesis or ''}"
                f"<br><br><b>Reads as</b>: {html.escape(r.reads)}<br><b>Formula</b> ({r.bet}): <code>{r.expression}</code><br>"
                f"<span class='muted'>t {r.t:.2f} · Sharpe {r.sharpe:.2f} · edge a year {r['mean']:.1%} · "
                f"{int(r.months or 0)} training months · drafted in fill round {r['round']}</span></div>",
                unsafe_allow_html=True)

# ── custom study requests: coming soon (Alex 2026-11-06: "for now have it be a coming soon, similar to the other
# side"). Planned: the request is queued, graded on Alex's machine the same way as the seeds, results pushed here.
st.subheader("Request a custom study")
st.markdown("<p class='muted'>Describe an idea or paste a formula.</p>", unsafe_allow_html=True)
st.text_area("Your idea", placeholder="Firms whose R&D spending is covered by operating cash flow, ranked within "
                                      "their industry", key="ask")
st.button("Requests are coming soon", disabled=True)
foot = st.columns([4, 1])
if LOCAL and foot[1].button("Refresh data", use_container_width=True, help="Rebuild the page data from the grade files"):
    subprocess.run([sys.executable, str(EXPORT)], check=True)
    st.rerun()
