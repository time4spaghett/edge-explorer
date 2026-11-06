# 12-month edges

S&P 500, long-only. Every formula drafted from the idea map (241 areas in 31 families), graded on training years:
each month buy the top fifth of stocks by the formula (equal weight, financials out), hold 12 months, subtract the
equal-weighted S&P 500. A seed has t of at least 1. 2024+ results are hidden until the viewer reveals them; they are
shown only, never used to pick. History only, not investment advice.

| file | what it does |
|---|---|
| `app.py` | The page (theme in `.streamlit/config.toml`). |
| `export.py` | Run locally: rebuilds and writes `data/dash12.json.gz`. |
| `publish.py` | Copies the page and data into the deploy repo and pushes it. |
| `requirements.txt` | What the host installs. |

Host secrets (`.streamlit/secrets.toml`): `password` (no password means no gate).
