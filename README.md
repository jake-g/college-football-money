# college-football-money: Money vs winning in college football (2023–2026)

Pairs **live 2026 results** for every FBS program with **real athletics
finance data** to ask two different questions that often get conflated:

- Does **spending** — on coaches, staff, recruiting, running the team —
  buy wins?
- Does **revenue** just follow winning around?

No API keys required. Both data sources are public.

📊 **[Read the current report →](reports/money_vs_wins_2026.md)**

## Money in vs money out

This distinction drives the whole project:

| | What it is | Direction of causation |
| --- | --- | --- |
| **Revenue** (money IN) | Tickets, donations, media rights, playoff payouts | Partly a *reward* for winning — reverse causation |
| **Spending** (money OUT) | Coach and staff salaries, recruiting, operations | Closer to an *input* the program controls |

They are heavily collinear (log revenue vs log spending correlates
around 0.9), so neither fully escapes the other. The report shows both
side by side and ranks every metric by how much variance it actually
explains.

Spending is broken out several ways so "spend more" can be tested at
different granularities:

| Metric | Meaning |
| --- | --- |
| `football_expenses` | Everything the football program spends |
| `football_spend_per_player` | The same, divided by roster size |
| `football_nonoperating_spend` | Total minus game-day operations, i.e. mostly salaries, recruiting and overhead |
| `football_operating_expenses` | Game day: travel, lodging, meals, equipment, officials |
| `recruiting_expenses_men` | Recruiting spend |
| `avg_head_coach_salary_men` | Official average head coach salary |
| `head_coach_pay` | The actual head coach's total pay, where a citation exists |

> [!IMPORTANT]
> The one number that is *not* public is the big one: 2026 revenue-share
> and NIL payments to players. The House settlement cap (~$20.5M in
> 2025-26, ~$21.3M in 2026-27) is known; each school's football
> allocation is not. That gap is documented rather than guessed at.

## Data sources

| What | Where | Notes |
| --- | --- | --- |
| Schedules, scores, W/L, team stats | ESPN public JSON API | Live, all 138 FBS teams and their opponents |
| Football revenue & expenses, department finances, coach salaries, recruiting spend | US Dept. of Education [EADA filings](https://ope.ed.gov/athletics/) | Mandatory federal disclosure, ~128 FBS schools per year, published on a ~1 year lag |
| Head coach total pay | Hand-compiled with a citation on every row | Only verified rows carry a number; the rest are blank and flagged `unverified` |
| Revenue-share cap, roster payroll, 247 team talent | House settlement reporting / 247Sports | Cap is public, per-school allocations mostly are not |

Service academies (Air Force, Army, Navy) have no EADA record at all —
they do not participate in Title IV federal student aid, so the
disclosure requirement does not reach them.

Full provenance, exact API endpoints, field mappings and a confidence
table are in [Sources, references and APIs](#sources-references-and-apis)
at the end of this file.

## Quick start

```bash
make setup     # virtualenv, dependencies, git hooks
make data      # federal finances + the 2026 season
make report    # charts + reports/money_vs_wins_2026.md
```

`make help` lists everything. The most useful targets:

| Target | What it does |
| --- | --- |
| `make setup` | Creates `.venv`, installs deps, installs pre-commit hooks |
| `make data` | `make money` + `make fetch` |
| `make history` | Pulls 2023-2025 so the trend charts have completed seasons |
| `make analyze` | Correlations and regression to stdout |
| `make report` | Rebuilds every figure and the markdown report |
| `make panel` | Pools seasons and trends the correlation |
| `make refresh` | Weekly in-season update: new results, new report |
| `make check` | Lint + tests, i.e. what CI would run |
| `make clean` | Drops the ESPN cache and Python caches, keeps all outputs |

Without make, everything is a plain CLI:

```bash
export PYTHONPATH=src
python -m cfbmoney money
python -m cfbmoney --season 2026 --workers 8 fetch
python -m cfbmoney --season 2026 --predictor football_expenses report
python -m cfbmoney --season 2026 --workers 8 --predictor football_expenses refresh
python -m cfbmoney --seasons 2023 2024 2025 2026 panel
```

Useful flags: `--season`, `--seasons`, `--scope power|fbs`, `--predictor`,
`--outcome`, `--no-conference-effects`, `--workers`, `--fresh`
(`--no-cache`), `--delay`.

## What comes out

```
data/processed/
  teams_2026.csv              one row per FBS team
  games_2026.csv              one row per team-game (long)
  games_unique_2026.csv       one row per game
  team_stats_2026.csv         ESPN season statistics per team
  team_season_2026.csv        record, scoring, opponent strength
  analysis_table_2026.csv     the merged money + results table
  correlations_2026.csv       every money x performance correlation
  model_coefficients_2026.csv OLS terms with standard errors
  residuals_2026.csv          actual minus spending-predicted, per team
  panel.csv                   all seasons stacked
reports/
  money_vs_wins_2026.md       the written report
  figures/*.png               scatters, quadrant charts, trends
```

## Reading the charts

- Money is always on a **log x-axis**; the spread is enormous.
- Trend lines are fitted strictly over the **observed data range** — no
  synthetic projections or future-season extrapolations are drawn by default.
- The **red quadrant** is high spending with a negative point margin:
  paying a lot to lose. The **green quadrant** is the bargain zone.

## How the analysis works

1. **Correlations.** Pearson and Spearman between each money metric and
   each performance metric, with n and p-values.
2. **Regression.** `performance ~ log10(money) + conference`. The
   conference dummies matter: without them you mostly rediscover that
   the SEC and Big Ten are rich *and* good. With them, the money
   coefficient answers the narrower question of whether the bigger
   budget wins *inside* a league.
3. **Residuals.** Actual minus what the budget predicts. Positive means
   punching above their wallet.

## Reading the numbers honestly

- **Reverse causation is real** on the revenue side, and only partly
  avoided on the spending side.
- **The finance lag is a feature.** EADA report year 2025 covers
  academic year 2024-25 — money spent *before* the 2026 season.
- **Private schools report differently.** Several book revenue exactly
  equal to expenses, which flattens their apparent margin.
- **Early-season noise.** Through week 4 a team has played two to four
  games. That is why the report also runs the same analysis on 2023,
  2024 and 2025.

## Development

```bash
make format   # ruff format + autofix
make lint     # check without writing
make test     # pytest
make check    # both
```

Style follows the Google Python Style Guide: two-space indents, 80
character lines, Google docstrings. `ruff` enforces it and pre-commit
runs it on every commit.

### Data policy in git

Re-downloadable artefacts are ignored: the ESPN response cache
(`data/raw/`) and the ~12 MB federal zip archives
(`data/finance/raw/`). Everything that represents *output* — tidy
finance CSVs, processed tables, reports and figures — is committed so it
renders on GitHub.

## Layout

```
src/cfbmoney/
  config.py       paths, conference ids, season defaults
  espn.py         cached ESPN API client (with HTTP connection pooling)
  names.py        school-name crosswalk (ESPN <-> federal filings)
  build.py        raw payloads -> tidy frames (concurrent fetching)
  finance.py      loads and joins the money files
  analyze.py      correlations, OLS, residuals, multi-season panel
  realignment.py  conference moves, before/after, Pac-12 breakup
  travel.py       time-zone shifts, within-team travel penalty
  plots.py        matplotlib figures
  report.py       markdown report renderer
  cli.py          command line interface
  sources/
    eada.py       downloads + parses the federal EADA archives
```

## Metrics, derived stats and considerations

### Raw metrics

| Metric | Source | Meaning |
| --- | --- | --- |
| `football_revenue` | EADA `REV_MEN` (football row) | All revenue attributed to football |
| `football_expenses` | EADA `EXP_MEN` (football row) | All spending attributed to football |
| `dept_total_revenue` / `dept_total_expenses` | EADA `GRND_TOTAL_*` | Whole athletics department |
| `football_participants` | EADA | Roster size used for per-player figures |
| `avg_head_coach_salary_men` | EADA | Average across all men's sports, not football alone |
| `recruiting_expenses_men` | EADA | Men's recruiting spend |
| `head_coach_pay` / `head_coach_buyout` | Public contract & FOIA disclosures | Verified head coach total compensation and buyout |
| `talent_composite` | 247Sports | Team Talent Composite rating |
| `wins`, `losses`, `points_for`, `points_against` | ESPN | Results |
| `conference`, `state`, `venue`, `home_away` | ESPN / EADA | Context for grouping and travel |

### Derived statistics

| Derived stat | How it is computed | Why |
| --- | --- | --- |
| `point_margin_per_game` | `(points_for - points_against) / games_played` | Less noisy than W/L in a short season |
| `win_pct` | `wins / games_played` | Headline outcome, but coarse early on |
| `football_spend_per_player` | `football_expenses / football_participants` | Normalises for roster size |
| `football_net` / `football_margin_usd` | `football_revenue - football_expenses` | Whether football funds the department |
| `football_share_of_dept` | `football_revenue / dept_total_revenue` | How football-dependent a school is |
| `spend_to_revenue_ratio` | `football_expenses / football_revenue` | Reinvestment rate |
| `football_nonoperating_spend` | `football_expenses - operating expenses` | Captures salaries and facilities rather than game-day costs |
| `log_*` | `log10(value)` | Money is brutally right-skewed; logs linearise it |
| `residual` | Actual minus regression-predicted performance | Over- and under-performance versus budget |
| `tz_shift` | Venue UTC offset minus home UTC offset | Travel burden; positive is eastward |
| `*_before` / `*_after` / `*_change` | Means either side of a conference move | Realignment before/after |

### What has been explored

| Question | Result |
| --- | --- |
| Does football revenue correlate with winning? | Yes. `r = +0.592` with point margin (`R² = 0.350`) and `r = +0.537` with win% through Week 4 |
| Does spending correlate better than revenue? | Nearly identically: `football_expenses` correlates `r = +0.570` (`R² = 0.325`) with point margin |
| Can the two be separated? | No. `log(revenue)` and `log(spending)` correlate `r = +0.89` across the 123 FBS schools |
| Is the relationship stable over time? | Completed seasons sit around `r = +0.30` to `+0.40` (`+0.367` in 2023, `+0.397` in 2024, `+0.298` in 2025); 2026 in-progress sits at `r = +0.537` |
| Does money still matter *within* a conference? | Yes, within-league `log10(football_expenses)` adds `+24.6` win% points per 10x budget (`p = 0.011`) after absorbing conference fixed effects |
| What is the strongest single correlate? | `dept_total_revenue` (`r = +0.601`, `R² = 0.361`), followed by `dept_total_expenses` (`r = +0.595`) |
| Does head coach pay drive results by itself? | Much less than program infrastructure (`r = +0.34`, `p = 0.014` across 52 verified public-school contracts) |
| Does 247Sports talent composite predict scoring? | Yes. `r = +0.517` (`p = 0.023`) with points scored per game across the 19 tracked elite rosters |
| Who gained from the Pac-12 breakup? | Leavers gained a median `+4.0%` revenue in year one (due to partial Big Ten shares for Oregon/UW); the two left behind (WSU/OSU) lost `-31.6%` |
| Does eastward travel hurt? | Yes, `-1.0` points of within-team margin penalty on trips of 2+ zones east across 61 team-seasons (`-6.8` vs `-5.7`) |

### Considerations and known limitations

> [!WARNING]
> **The 2026 season is four weeks old (2–4 games played per team).** Every 2026 number is
> directional. Completed seasons (2023–2025) carry the full-season weight.

*   **Finance lags the field by two years.** EADA report year 2025 covers
    the 2024 season. This is framed as a feature — spending precedes
    results — but it means 2026 money is genuinely 2024 money, and any
    school that moved conference in 2026 has no post-move filing yet.
*   **Correlation is not causation, and the confounder is obvious.**
    Winning programs earn more *because* they win. The regression with
    conference fixed effects is the closest thing here to a control, and
    it substantially narrows the money effect.
*   **Conference explains a large share of the raw correlation.** Media-rights
    money is distributed by league, so "rich" and "Big Ten/SEC" are
    closely coupled.
*   **The biggest spending lever is invisible.** Direct payments to
    players under the House settlement are not public per school.
*   **EADA is self-reported.** Private institutions in particular often
    report figures that balance rather than reflect true cash flow.
*   **Coach pay is incomplete for private schools.** Private schools are exempt from
    public-records law, so their salaries are left blank (`unverified`) rather than imputed.
*   **Time zones are approximated from state.** Four FBS schools in
    split-timezone states are overridden by hand; neutral-site games are
    excluded entirely.
*   **Travel effects are confounded by scheduling.** Long eastward trips
    are disproportionately Group of Five teams taking guarantee games at
    blue bloods, which is why the within-team comparison is reported
    rather than the raw league-wide split.
*   **Service academies have no federal filing** and are excluded from
    all money analysis rather than imputed.

## Sources, references and APIs

Everything in this project comes from a public source. Nothing is
modelled, imputed or invented: where a number is not public it is left
blank and flagged.

### 1. ESPN public JSON API

No key, no authentication, no published rate limit. Two hosts are used:

| Purpose | Endpoint |
| --- | --- |
| Teams, schedules, scores, stats | `https://site.api.espn.com/apis/site/v2/sports/football/college-football` |
| Conference membership by group | `https://sports.core.api.espn.com/v2/sports/football/leagues/college-football` |

Conference group IDs: `1` ACC, `4` Big 12, `5` Big Ten, `8` SEC, `9`
Pac-12, `12` C-USA, `15` MAC, `17` Mountain West, `18` Independents,
`37` Sun Belt, `151` American, `80` all FBS.

> [!WARNING]
> ESPN's edge returns **HTTP 403** for custom *and* browser-spoofed
> `User-Agent` strings. The client deliberately sends the default
> `python-requests/x.y.z` agent. Setting a "realistic" Chrome UA breaks
> every request.

Responses are cached to `data/raw/` with a TTL so reruns are cheap and
the API is not hammered. Use `--fresh` (`--no-cache`) to force a refresh.

### 2. US Department of Education — EADA

The Equity in Athletics Disclosure Act requires every co-educational
institution receiving Title IV federal student aid to file annual
athletics revenue and expense data. This is the backbone of the money
side of the analysis.

*   **Portal:** <https://ope.ed.gov/athletics/>
*   **API:** the Angular front end is backed by an undocumented REST
    API — `/api/dataFiles/fileList` lists available years and
    `/api/dataFiles/file?fileName=...` returns a ZIP.
*   **Parser:** `src/cfbmoney/sources/eada.py`
    (`python -m cfbmoney.sources.eada --fbs-only`). Archives cached in
    `data/finance/raw/`.
*   **Coverage:** report years 2023-2025 on disk; the API goes back to
    2000-01, so a longer panel is available on request.
*   **Vintage:** report year *N* covers academic year *N-1* to *N*, so
    report year 2025 contains the **2024** football season.

Field mapping, verified against the real archives:

| Field | File | Meaning |
| --- | --- | --- |
| `SPORTSCODE == 7` | `schools.xlsx` | Filter for football |
| `REV_MEN` / `EXP_MEN` | `schools.xlsx` | Football revenue / expenses |
| `GRND_TOTAL_REVENUE` / `GRND_TOTAL_EXPENSE` | `instLevel.xlsx` | Whole-department totals |
| `HDCOACH_SALARY_MEN` / `ASCOACH_SALARY_MEN` | `instLevel.xlsx` | Average salary across *all men's sports* |
| `MEN_TOTAL_HEADCOACH` / `MEN_TOTAL_ASSTCOACH` | `schools.xlsx` | Football coach headcounts |

> [!CAUTION]
> The `IL_*` fields are **not** reliable department totals and must not
> be used for total athletics revenue. An early pass of this project
> used `IL_REVENUE_MENALL` and produced nonsense (a school showing less
> total men's revenue than its football revenue alone).

> [!NOTE]
> `HDCOACH_SALARY_MEN` averages across every men's sport, so it is a
> floor on football coaching pay, not the football payroll.

Service academies (Air Force, Army, Navy) do not participate in Title IV
and therefore have **no EADA record at all**. They are tracked
explicitly in `names.EADA_EXEMPT` rather than silently dropped.

### 3. Head coach compensation & buyouts

*   **Sources:** USA Today coaching salary database, FOIA contract
    releases, ESPN, CBS Sports, and state open-records disclosures, with
    a `source_url` on every verified row.
*   **File:** `data/finance/coach_pay_2026.csv`
*   **Coverage:** **52 of 66 rows verified** (`high` or `medium`
    confidence) with total annual compensation and contract buyout
    obligations (e.g., Kirby Smart at $13.28M / $118M buyout; Ryan Day
    at $12.5M / $70.5M buyout; Steve Sarkisian at $10.6M / $54.3M buyout).
    The remaining 14 rows (primarily private universities such as USC,
    Notre Dame, Stanford, Miami, TCU, Baylor, SMU, and Vanderbilt) are
    marked `unverified` with blank salaries rather than interpolated.

### 4. Revenue share, NIL and realignment economics

*   **Sources:** *House v. NCAA* settlement reporting, 247Sports Team
    Talent Composite, UC Board of Regents filings, and conference media
    rights disclosures.
*   **File:** `data/finance/nil_revshare_2026.csv`
*   **Cap:** ~$20.5M per school in 2025-26, escalating ~4% to ~$21.32M
    in 2026-27 (~75% or ~$16M rule-of-thumb football share, though
    per-school splits are undisclosed and kept blank in the CSV).
*   **Realignment financial benchmarks:**
    *   **WSU/OSU Settlement:** $65M total ($6.5M per school) withheld
        from the 10 departing Pac-12 schools.
    *   **Media-Rights Hierarchy:** Big Ten ~$1.1B–$1.2B/yr (~$65M–$75M
        full share), Big 12 ~$380M/yr (~$31M/school), ACC ~$240M–$400M/yr.
    *   **Tiered Big Ten Entry:** USC and UCLA entered at full shares
        (~$65M+), while Oregon and Washington entered at a $30M partial
        share escalating +$1M/year until 2030.
    *   **Travel Cost Inflation:** UCLA projected **$4.6M to $5.8M** in
        additional annual travel and logistics costs in its official UC
        Board of Regents filing.

### 5. Knight-Newhouse College Athletics Database

*   **URL:** <https://knightnewhousedata.org/>
*   **Status:** no public machine-readable API or bulk CSV export was
    found. EADA is used instead as the source for department-level
    athletics revenue.

### Confidence table

| Source / metric | Confidence | Notes |
| --- | --- | --- |
| ESPN results and stats | High | Live official scoring data |
| EADA financials, public schools | High | Audited institutional reporting |
| EADA financials, private schools | Medium | Often reflects accounting balance rather than true cash flow |
| Head coach pay, verified rows | High | Explicit contract reporting, cited per row |
| Head coach pay, unverified rows | None | Left blank deliberately |
| Revenue-share cap | High | Derived from the settlement escalator |
| 247Sports talent composite | High | Published rankings |
| Per-school NIL / rev-share allocation | Unavailable | Not public anywhere |

### Licence

Released under the [MIT License](LICENSE). The underlying data belongs
to its respective publishers; EADA filings are US Government works in
the public domain.
