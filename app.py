"""12-month edges: the idea-map seeds on the S&P 500, long-only (Alex 2026-11-06: "let's actually just go for a 12 m
edge version ... get the 12m data up with a dashboard").

Every formula Haiku drafted from the idea map (241 areas in 31 families, guided by Opus examples), graded free on
training years only: each month, buy the top fifth of S&P 500 stocks by the formula (equal weight, financials out),
hold 12 months, subtract the equal-weighted S&P 500. A seed is a formula whose t (non-overlapping, grade.py t_test) is
at least 1. No grow step (Alex 2026-11-06). Hosted like the event-study page (sharadar/event_site): it reads only
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
import statistics
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

HERE = Path(__file__).resolve().parent
DATA = HERE / "data" / "dash12.json.gz"
EXPORT = HERE / "export.py"
LOCAL = (HERE.parent / "playbook" / "horserace" / "im_dash_data.py").exists()  # inside the repo, not on the host

GROUND, CARD, FIELD = "#1F2327", "#262B30", "#191C1F"  # Blackbird LR palette (app.py)
LINE, BRONZE, BRONZE_HI, BRONZE_DIM = "#3A4148", "#D4A955", "#F0C46A", "#8E979F"
RAMP = ["#4A535C", "#5E6670", "#7A7F7F", "#97906F", "#B59E5E", "#D4AA52", "#ECBD5C", "#F6CF7A"]
COLS = 6

st.set_page_config(page_title="12-month edges", layout="wide")
st.markdown(f"""<style>
.stApp, [data-testid="stHeader"] {{background:{GROUND};}}
.stApp, .stApp p, .stApp span, .stApp label, .stApp li, .stApp div {{color:{BRONZE};
  font-family:Bahnschrift, "DIN Alternate", "Segoe UI", sans-serif;}}
.muted {{color:{BRONZE_DIM} !important; font-size:0.92rem;}}
.card {{background:{CARD}; border:1px solid {LINE}; border-radius:6px; padding:12px 16px; margin:6px 0 12px 0;}}
.card b {{color:{BRONZE_HI};}}
</style>""", unsafe_allow_html=True)


def secret(k: str):
    try:
        return st.secrets.get(k) or os.environ.get(k.upper())
    except Exception:  # noqa: BLE001  (no secrets file locally)
        return os.environ.get(k.upper())


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


if not DATA.exists() and LOCAL:
    subprocess.run([sys.executable, str(EXPORT)], check=True)
d = load(DATA.stat().st_mtime)
df = pd.DataFrame(d["rows"])

st.title("12-month edges")
st.markdown(f"<p class='muted'>S&P 500, long-only. Each month a formula picks the top fifth of stocks (equal weight, "
            f"financials out) and holds them 12 months; its edge is the return above the equal-weighted S&P 500. "
            f"Training years only ({d['train']}). A <b>seed</b> is a formula with t of at least 1.</p>",
            unsafe_allow_html=True)
top = st.columns([3, 1])
with top[0]:
    if d["not_graded_yet"]:
        st.markdown(f"<p class='muted'>Grading still running: {len(df):,} formulas graded, {d['not_graded_yet']:,} to "
                    f"go{'. Press Refresh later to pull in the rest' if LOCAL else ''}.</p>", unsafe_allow_html=True)
if LOCAL:
    with top[1]:
        if st.button("Refresh data", use_container_width=True):
            subprocess.run([sys.executable, str(EXPORT)], check=True)
            st.rerun()

seeds = df[df.seed]
m = st.columns(4)
m[0].metric("Seeds", f"{len(seeds):,}")
m[1].metric("Formulas graded", f"{len(df):,}")
m[2].metric("Families with a seed", f"{seeds.family.nunique()} of {len(d['families'])}")
m[3].metric("Median seed t", f"{seeds.t.median():.2f}" if len(seeds) else "–")

# ── family grid ──────────────────────────────────────────────────────────────
st.subheader("Families")
st.markdown("<p class='muted'>One tile per family, most seeds first. Colour: share of the family's formulas that are "
            "seeds. Click a tile to list its seeds. t is the median t of its seeds.</p>", unsafe_allow_html=True)
fam = []
for f in d["families"]:
    s, a = seeds[seeds.family == f], df[df.family == f]
    fam.append({"family": f, "seeds": len(s), "graded": len(a), "share": len(s) / len(a) if len(a) else 0.0,
                "med_t": statistics.median(s.t) if len(s) else None, "areas": d["areas"][f]})
fam.sort(key=lambda r: (-r["seeds"], r["family"]))
smax = max(r["share"] for r in fam) or 1


def tint(share: float) -> str:
    return RAMP[min(len(RAMP) - 1, int(share / smax * (len(RAMP) - 1) + 0.5))]


def pick(f: str) -> None:
    st.session_state["fam"] = f


css = []
for i, r in enumerate(fam):
    on = st.session_state.get("fam") == r["family"]
    edge = f"3px solid {BRONZE_HI}" if on else f"1px solid {LINE}"
    css.append(f".st-key-tile{i} button, .st-key-tile{i} button:hover, .st-key-tile{i} button:focus, "
               f".st-key-tile{i} button:active {{background:{tint(r['share'])} !important; border:{edge} !important; "
               f"height:92px; width:100%;}} .st-key-tile{i} button p {{color:{FIELD} !important; line-height:1.25;}}"
               f" .st-key-tile{i} button:hover {{filter:brightness(1.12);}}")
st.markdown("<style>" + " ".join(css) + "</style>", unsafe_allow_html=True)
for k in range(0, len(fam), COLS):
    cols = st.columns(COLS)
    for j, r in enumerate(fam[k:k + COLS]):
        med = f" · t {r['med_t']:.2f}" if r["med_t"] is not None else ""
        cols[j].button(f"**{r['family']}**  \n{r['seeds']} seeds of {r['graded']}{med}", key=f"tile{k + j}",
                       help=f"{r['areas']} areas, {r['graded']} formulas graded, {r['seeds']} seeds ({r['share']:.0%}); "
                            "median t of its seeds", on_click=pick, args=(r["family"],), use_container_width=True)

# ── seed list ────────────────────────────────────────────────────────────────
st.subheader("Seeds")
c = st.columns([3, 2, 1.4])
q = c[0].text_input("Search", placeholder="words or variables, e.g. R&D cash flow, or xrd")
opts = ["All families"] + [r["family"] for r in fam]
if st.session_state.get("fam") not in opts:
    st.session_state["fam"] = "All families"
fpick = c[1].selectbox("Family", opts, key="fam")
below = c[2].checkbox("Include t below 1", value=False, help="Show every graded formula, not only the seeds.")
unseen = False
if d.get("unseen"):
    unseen = st.toggle("Reveal 2024+ results", value=False,
                       help="Edge and Sharpe for formations from 2024-01 to 2025-09 (21 months, after training). "
                            "Shown only: seeds were picked on training years, and the list stays sorted by training t.")
else:
    st.markdown("<p class='muted'>2024+ results are not opened yet.</p>", unsafe_allow_html=True)

v = df if below else seeds
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
st.markdown("<p class='muted'>Describe a factor idea, or paste a formula. We grade it the same way as the seeds "
            "(S&P 500, top fifth held 12 months against the equal-weighted S&P 500, training years) and post the "
            "result here.</p>", unsafe_allow_html=True)
st.text_area("Your idea", placeholder="Firms whose R&D spending is covered by operating cash flow, ranked within "
                                      "their industry", key="ask")
st.button("Requests are coming soon", disabled=True)
st.caption("History only, not investment advice.")
