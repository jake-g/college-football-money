# Changelog

All notable changes to this project are documented here. Versions use
`X.Y.Z` where `X = 0` for the 2026–27 season, `Y` is the official CFB
season week (`0` for preseason, `2`–`7` for Weeks 2–7), and `Z` is used
for small point fixes (`0` otherwise).

## [0.7.0] - 2026-10-19

### Added
- `current_residual` in `drivers.residual_persistence` so the persistent
  over/under-performer table surfaces each program's in-progress `2026 to date`
  margin versus budget alongside its 2023–25 history.
- Median football spending (`football_expenses`) in `analyze.conference_summary`
  and the report's conference summary table to match the conference boxplot.
- Bounding-box and data-point collision avoidance with subtle leader lines in
  `plots._annotate_points` and `plots.pythagorean_chart`.
- Historical min–max range band (`2023–25`), distinct line styles, and direct
  value labels across `season_trajectory_chart`, `budget_tiers_chart`,
  `schedule_split_chart`, `box_score_markers_chart`, `travel_penalty_chart`,
  and `conference_money_box`.

### Changed
- Folded the conference-fixed-effect OLS section into "Within the league:
  out-spending your peers" and tightened redundant prose across the report.
- Standardized table formatting (`Win%` percentages in coach pay, explicit
  quintile labels in budget tiers, `Group` column header in Pythagorean luck,
  and clarified realignment windows).
- Week 7 datasets, figures, report, and README regenerated.

### Fixed
- `sharex=True` clipping bug on `revenue_vs_spending_panel` where `sharex`
  applied the spending panel's narrower x-limits to the revenue panel and
  clipped six $100M+ revenue programs (`Texas`, `Michigan`, `Ohio State`,
  `Alabama`, `Georgia`, `Penn State`).
- Early-season momentum comparison in `report._momentum_lines` when the
  in-progress season's `R²` has not yet surpassed completed seasons.

## [0.6.0] - 2026-10-12

### Added
- `gameday` module built on the game log rather than the season table:
  Pythagorean expectation and luck, the richer team's win rate in one-score
  games vs blowouts, within-team home-field advantage, and home attendance
  (summary, lagged regression against budget, same-week year-over-year
  change), with four matching charts and tests.
- `insights.budget_tiers` for a dose-response view by budget quintile.
- Report: a "Budget tiers" section in part 2 and a new part, "Luck, close
  games and crowds", with a matching summary group. Verdict sentences are
  computed from the data.

### Changed
- `command_report` split into `_history_inputs`, `_trend_inputs`,
  `_gameday_inputs` and `_realignment_inputs` stage helpers.
- Report header uses the latest week with completed games instead of ESPN's
  upcoming week, so it matches every same-week table.
- `season_money` / `played_games` helpers in `trends` promoted to public.
- README refreshed for game-day analyses and current numbers; the
  hard-coded "four weeks old" warning is gone.
- Week 6 datasets, figures and report regenerated.

### Fixed
- NIL alert rendered stray `> ` characters mid-sentence.
- Tiny p-values are floored at `<0.01`.

## [0.5.0] - 2026-10-05

### Added
- Same-week season comparison: each season is replayed week by week so 2026
  is judged against 2023-25 at the same point.
- Upset rate with Fisher exact test.
- In-season forecast fitted on same-week FBS-only margins.

### Changed
- Replaced the win%-based 2026 over/under-performer table with the
  same-week comparison.
- Week 5 datasets, figures and report regenerated.

## [0.4.0] - 2026-09-29

### Added
- `insights.py` and `drivers.py` modules: schedule-split, within-league and
  team-driver analyses with charts.
- Road-gap t-test and a new report part on what separates good teams from
  bad.
- Service-academy time zones and a home-margin control for movers.

### Changed
- Conference games are derived from both teams' conferences, since ESPN
  omits the flag.
- Report restructured into a grouped summary, contents and numbered parts;
  figure count trimmed from 17 to 10.
- Week 4 datasets, figures and report regenerated.

### Fixed
- `nargs='+'` CLI flags swallowing the subcommand.

### Removed
- Duplicate `football_margin_usd` alias.

## [0.3.0] - 2026-09-20

### Added
- Weekly `refresh` CLI command with concurrent ESPN fetching and HTTP
  connection pooling.

### Changed
- Data-integrity pass across finance metrics and charts; EADA 2023-2025
  CSVs and the panel regenerated.
- Week 3 datasets, figures and report regenerated.

## [0.2.0] - 2026-09-14

Initial release (Week 2 of the 2026 season).

### Added
- ESPN API client, game and team dataset builders, school-name crosswalk.
- EADA federal finance ingestion, coach salaries and NIL cap data.
- Econometric modeling: correlations, OLS and a multi-season panel.
- Visualization suite for money vs performance, multi-season panels and
  residuals.
- Conference realignment module with Pac-12 breakup financial analysis.
- Travel and time-zone circadian burden analysis for realignment travel.
- CLI, automated figure pruning and markdown report generator.
- README, metric glossary and research notes.

[0.7.0]: https://github.com/jake-g/college-football-money/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/jake-g/college-football-money/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/jake-g/college-football-money/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/jake-g/college-football-money/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/jake-g/college-football-money/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/jake-g/college-football-money/releases/tag/v0.2.0
