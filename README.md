# Money vs winning in college football (2026 season)

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
| `make clean-cache` | Drops the ESPN cache, keeps all outputs |

Without make, everything is a plain CLI:

```bash
export PYTHONPATH=src
python -m cfbmoney money
python -m cfbmoney --season 2026 fetch
python -m cfbmoney --season 2026 --predictor football_expenses report
python -m cfbmoney --seasons 2023 2024 2025 2026 panel
```

Useful flags: `--season`, `--scope power|fbs`, `--predictor`,
`--outcome`, `--no-conference-effects`.

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
- A **solid** line is fitted to real data. A **dotted** line is an
  extrapolation or a projection — a guess, not a measurement.
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
- **Early-season noise.** Through week 3 a team has played two or three
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
  espn.py         cached ESPN API client
  names.py        school-name crosswalk (ESPN <-> federal filings)
  build.py        raw payloads -> tidy frames
  finance.py      loads and joins the money files
  analyze.py      correlations, OLS, residuals, multi-season panel
  realignment.py  conference moves, before/after, Pac-12 breakup
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
| `residual` | Actual minus regression-predicted margin | Over- and under-performance versus budget |
| `tz_shift` | Venue UTC offset minus home UTC offset | Travel burden; positive is eastward |
| `*_before` / `*_after` / `*_change` | Means either side of a conference move | Realignment before/after |

### What has been explored

| Question | Result |
| --- | --- |
| Does football revenue correlate with winning? | Yes. r ≈ 0.46 with point margin |
| Does spending correlate better than revenue? | No, essentially identically (r ≈ 0.46) |
| Can the two be separated? | No. `log(revenue)` and `log(spending)` correlate ~0.9 |
| Is the relationship stable over time? | Yes. r = 0.42 / 0.48 / 0.43 / 0.46 for 2023-2026 |
| Does money still matter *within* a conference? | Much less. The coefficient loses significance with conference fixed effects |
| What is the strongest single correlate? | `dept_total_revenue` (r ≈ 0.50) |
| Does spending per player predict results? | Weakly, and it is dominated by roster-size accounting |
| Who gained from the Pac-12 breakup? | Leavers gained a median +7% revenue; the two left behind lost ~31% |
| Did a richer conference buy better football? | Not in year one. r ≈ 0.21 across 13 movers |
| Does eastward travel hurt? | Yes, about −2.1 points of margin on trips of 2+ zones, controlling for team quality |

### Considerations and known limitations

> [!WARNING]
> **The 2026 season is three weeks old.** Every 2026 number is
> directional. Completed seasons (2023-2025) carry the real weight.

*   **Finance lags the field by two years.** EADA report year 2025 covers
    the 2024 season. This is framed as a feature — spending precedes
    results — but it means 2026 money is genuinely 2024 money, and any
    school that moved conference in 2026 has no post-move filing yet.
*   **Correlation is not causation, and the confounder is obvious.**
    Winning programs earn more *because* they win. The regression with
    conference fixed effects is the closest thing here to a control, and
    it substantially weakens the money effect.
*   **Conference explains most of the raw correlation.** Media-rights
    money is distributed by league, so "rich" and "Big Ten/SEC" are
    nearly the same statement.
*   **The biggest spending lever is invisible.** Direct payments to
    players under the House settlement are not public per school.
*   **EADA is self-reported.** Private institutions in particular often
    report figures that balance rather than reflect true cash flow.
*   **Coach pay is incomplete.** Private schools are exempt from
    public-records law, so that correlation runs on a small, biased
    sample.
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
the API is not hammered. Use `--no-cache` to force a refresh.

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

### 3. Head coach compensation

*   **Sources:** ESPN, CBS Sports, USA Today coaching salary reporting
    and local newspapers, with a `source_url` on every populated row.
*   **File:** `data/finance/coach_pay_2026.csv`
*   **Coverage:** 10 of 66 rows verified. The remaining rows are marked
    `unverified` with a blank salary.

Private institutions (USC, Notre Dame, Stanford, Miami, Duke and others)
are exempt from state public-records law, so their contract terms are
generally unavailable. Mid-cycle coaching changes further complicate
attributing a 2026 salary to the right person.

### 4. Revenue share and NIL

*   **Sources:** *House v. NCAA* settlement reporting; 247Sports Team
    Talent Composite.
*   **File:** `data/finance/nil_revshare_2026.csv`
*   **Cap:** ~$20.5M per school in 2025-26, escalating ~4% to ~$21.32M
    in 2026-27.

> [!IMPORTANT]
> The per-school split of that cap between football and other sports,
> and actual roster payroll, are not disclosed by any school. These
> columns are intentionally empty. This is the single largest known gap
> in the analysis, and it sits directly on top of the question the
> project is asking.

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
