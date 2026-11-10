# AGENTS.md

Guidance for AI agents (and humans) working in this repo. Read fully before
touching the report or analysis code.

## What this project is

A weekly, in-season research report on whether money buys wins in college
football. Live ESPN results for every FBS team are joined to federal EADA
athletics-finance filings. Output is `reports/money_vs_wins_2026.md` plus
figures, regenerated every week of the 2026 season.

## Owner preferences (apply to every edit)

### Report writing
- **Clear and concise.** Short sections, no filler, no restating a table in
  prose.
- **Prefer tables, charts and captions over paragraphs.** If a finding can be
  a table row or a figure, make it one. One-sentence takeaway under each.
- **Prefer bullets over paragraphs.** Paragraphs are at most two or three
  sentences.
- **Do not riddle prose with numbers.** A bullet or sentence carries one or
  two key numbers; the rest live in the table beside it.
- **Every verdict is computed, never hardcoded.** Words like "suggestive",
  "significant", "unusual", "in line with" must come from a test or a
  threshold in code so they stay true as the data moves.
- **Same-week comparisons.** Any 2026 number compared with past seasons must
  be compared at the same week, not with their finals.
- **Say what changed.** Each weekly update should state which earlier
  hypotheses held, which moved, and what is new, briefly.
- Good GitHub markdown: `> [!NOTE]`-style alerts sparingly, aligned table
  columns, figures embedded next to the text that discusses them.

### Charts
- Money on a log x-axis; fits over the observed range only.
- Label the headline programs (`config.HEADLINE_PROGRAMS`) and the extremes.
  Add popular programs (`config.POPULAR_PROGRAMS`) only where they fit
  without touching anything (smaller, grey). Never crowd a chart.
- In-progress season always visually distinct (red, thick) with a
  historical min-max band for completed seasons.

### Code
- Google Python Style Guide: **2-space indents, 80 columns, single quotes,
  Google docstrings, type hints**. `ruff` enforces it (`make format`,
  `make lint`).
- **Zero magic numbers**: Heuristic thresholds, plot label collision boxes,
  and significance cutoffs must be declared as uppercase module constants
  (in `config.py` or module top), never buried raw in calculation loops.
- **Stdlib-only `__init__.py`**: Keep package root `__init__.py` purely for
  `__version__` without importing heavy scientific dependencies (`pandas`,
  `scipy`, `matplotlib`) to preserve fast CLI startup.
- Analysis lives in `src/cfbmoney/*.py` modules by theme (`trends`,
  `gameday`, `insights`, `drivers`, ...). Rendering lives in `report.py` and
  `plots.py` only. CLI wiring lives in `cli.py` stage helpers
  (`_trend_inputs`, `_gameday_inputs`, ...).
- Processed outputs that a reader might want go to `data/processed/*.csv`.

### Testing
- **100% synthetic unit test isolation**: Unit tests must never load cached
  network files or live EADA datasets from disk. All tests in `tests/` must
  construct minimal synthetic `pd.DataFrame` fixtures with neutral mock team
  names so test suites run in under 2 seconds offline and never break on roster
  or schedule drift.
- Every new analysis gets a unit test on a tiny synthetic frame, and every
  new report section gets a test verifying it accurately quotes its inputs.

### Documentation & formatting hygiene
- **Changelog lineage preservation**: `CHANGELOG.md` is strictly append-only
  across releases; never prune, overwrite, or truncate past week entries.
- **Clean Markdown**: Use `and` instead of `&` in section headings. Keep table
  cells clean and readable without unescaped special characters or raw LaTeX.

### Versioning & Git Commits
- Tags are `v0.<week>.0` where `<week>` is the CFB week the data covers.
  Weeks with no release are skipped. Bump `pyproject.toml` and
  `src/cfbmoney/__init__.py` together.
- Commit conventions:
  - Subject line: `Week <N>: <high-level summary>` (under 50 characters).
  - Body: 2–4 concise bullet points detailing data shifts, newly added
    analyses/sections, and docs updated.
  - Tag format: `v0.<N>.0` matching `pyproject.toml`.
  - When direct `git commit` is restricted by sandbox rules, write a runnable
    handoff script to `scratch/commit.sh` for convenient one-command execution.

## Weekly update procedure

Run every Sunday or Monday after the weekend's games.

1. **Refresh data and regenerate everything**
   ```bash
   make refresh          # ESPN fetch (cached) + analysis + figures + report
   ```
   Check the log: `N of 138 teams matched to finance records` should be
   135 (Air Force, Army, Navy have no EADA filing). The report header shows
   the week; confirm it advanced.

2. **Diff the report against last week**
   ```bash
   git diff reports/money_vs_wins_2026.md | grep '^[-+]' | grep -v '^[-+]| '
   ```
   Read the prose lines (not table rows). For each, ask:
   - Did a verdict flip (significant ↔ not, above ↔ below)? Is the sentence
     still true? If a sentence can go stale, make it data-driven in
     `report.py`.
   - Did any sentence disappear or appear? Usually a branch that was never
     exercised; add the missing branch.
   - Do the week-7 / week-9 / ... claims in the summary still hold?

3. **Review every figure** (`reports/figures/*.png`). Look for clipped
   points, overlapping labels, legends covering data, stale titles.

4. **Reason about the new data** and write it down before coding:
   - Which earlier hypotheses held, which moved, and why.
   - One or two new, testable hypotheses suited to this point of the season
     (e.g. early: schedule mismatches; mid: conference play; late: depth,
     playoff field, bowl eligibility, coaching changes).
   - Pick the one or two that add the most and can be shown as a table or
     chart. Prune anything the new week makes redundant.

5. **Implement**
   - Analysis function in the themed module, with a docstring and a test.
   - Wire into the matching `cli.py` stage; write a CSV if useful.
   - Render in `report.py`: a `##` section inside the right part, plus a
     summary bullet only if it is one of the week's headline findings.
   - Chart in `plots.py` if the finding is visual; embed it next to its
     section via `_figure(pool, '<stem>', ...)`.

6. **Verify**
   ```bash
   make format && make check     # ruff + pytest, all green
   make report                   # regenerate with the new sections
   ```
   Re-read the summary and the new sections once more for length and
   number density.

7. **Update docs**
   - `README.md`: "What has been explored" table (numbers + new rows),
     the week in its intro line, `data/processed` listing, layout entry for
     any new module, versioning week range.
   - `CHANGELOG.md`: new `[0.<week>.0]` entry (Added / Changed / Fixed),
     compare link at the bottom, week range in the header note.
   - Bump version in `pyproject.toml` and `src/cfbmoney/__init__.py`.

8. **Commit and tag** (the agent may be blocked from `git commit`; if so,
   stage and hand the commands to the owner)
   ```bash
   git add -A
   git commit -m "Week <N>: <one-line summary of what is new>"
   git tag -a v0.<N>.0 -m "Week <N>: <summary>"
   ```

## Things that bite

- ESPN returns 403 for custom User-Agent strings; keep the default.
- EADA lags two years; 2026 money is report year 2025. Do not "fix" this.
- `week_by_week`/same-week helpers include postseason weeks for completed
  seasons; regular-season cut-offs use `trends.REGULAR_SEASON_WEEKS`.
- Conference games are derived from both teams' conferences (ESPN omits
  the flag); FCS games are excluded from money comparisons.
- p-values: use `_fmt_p` in tables (`<0.01`) and `_p_text` in prose
  (`p < 0.01`), never `p = <0.01`.
