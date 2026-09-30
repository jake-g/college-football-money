"""Command line interface.

Typical use during the season::

    python -m cfbmoney fetch            # refresh 2026 results from ESPN
    python -m cfbmoney money            # refresh federal finance filings
    python -m cfbmoney analyze          # correlations + regression
    python -m cfbmoney report           # markdown report and charts
    python -m cfbmoney all              # all of the above

Every subcommand accepts ``--season`` and can be pointed at earlier
seasons to build a historical baseline.
"""

from __future__ import annotations

import argparse
import logging
import pathlib
import sys
from collections.abc import Iterable

import pandas as pd

from . import analyze
from . import build
from . import config
from . import drivers as drivers_module
from . import espn
from . import finance
from . import insights
from . import plots
from . import realignment
from . import report as report_module
from . import travel
from .sources import eada

logger = logging.getLogger('cfbmoney')


def _configure_logging(verbose: bool) -> None:
  """Sets up root logging for the CLI."""
  logging.basicConfig(
    level=logging.DEBUG if verbose else logging.INFO,
    format='%(levelname)s %(name)s: %(message)s',
  )


def _group_ids(scope: str) -> list[int]:
  """Translates a scope flag into ESPN conference group ids.

  Args:
    scope: Either ``power`` or ``fbs``.

  Returns:
    The matching group ids.
  """
  return config.POWER_GROUP_IDS if scope == 'power' else config.FBS_GROUP_IDS


def command_fetch(args: argparse.Namespace) -> int:
  """Downloads teams, schedules and statistics from ESPN."""
  if getattr(args, 'delay', None) is not None:
    config.REQUEST_DELAY_SECONDS = args.delay
  use_cache = not (args.no_cache or getattr(args, 'fresh', False))
  workers = getattr(args, 'workers', 1)
  client = espn.EspnClient(season=args.season, use_cache=use_cache)
  teams = build.build_teams_frame(client.list_teams(_group_ids(args.scope)))
  logger.info('Fetched %d teams', len(teams))

  games = build.build_games_frame(client, teams, max_workers=workers)
  logger.info(
    'Fetched %d team-games (%d completed)',
    len(games),
    int(games['completed'].sum()),
  )
  stats = build.build_stats_frame(client, teams, max_workers=workers)
  season_frame = build.build_team_season_frame(teams, games, stats)

  build.write_frames(
    {
      'teams': teams,
      'games': games,
      'games_unique': build.dedupe_games(games),
      'team_stats': stats,
      'team_season': season_frame,
    },
    args.season,
  )
  return 0


def command_money(args: argparse.Namespace) -> int:
  """Downloads and parses federal EADA athletics filings."""
  years = args.years
  if not years:
    latest = eada.latest_report_year()
    years = [latest - offset for offset in range(args.history)]
  eada.fetch_years(
    years,
    config.FINANCE_DIR / 'raw',
    config.FINANCE_DIR,
    fbs_only=not args.all_divisions,
  )
  return 0


def _load_analysis_table(season: int) -> pd.DataFrame:
  """Builds the merged money and results table for a season."""
  team_season = build.read_frame('team_season', season)
  money = finance.build_money_frame(team_season['school'], season=season)
  merged = analyze.merge_money_and_results(team_season, money)
  matched = merged['football_revenue'].notna().sum()
  logger.info('%d of %d teams matched to finance records', matched, len(merged))
  return merged


def command_analyze(args: argparse.Namespace) -> int:
  """Runs correlations and the regression, and writes the tables."""
  merged = _load_analysis_table(args.season)
  correlations = analyze.correlation_table(merged)
  model = None
  try:
    model = analyze.fit_ols(
      merged,
      outcome=args.outcome,
      predictor=args.predictor,
      conference_effects=not args.no_conference_effects,
    )
  except ValueError as exc:
    logger.error('Regression skipped: %s', exc)

  analyze.write_outputs(merged, correlations, model, args.season)

  if not correlations.empty:
    print('\nTop correlations with on-field performance:')
    print(
      correlations.head(12).to_string(
        index=False,
        float_format=lambda v: f'{v:0.3f}',
      )
    )
  if model:
    print(
      f'\nOLS {model["outcome"]} ~ {model["predictor"]}'
      f'{"" if args.no_conference_effects else " + conference"}: '
      f'n={model["n"]}, R2={model["r_squared"]:.3f}'
    )
    print(
      model['coefficients'].to_string(
        index=False, float_format=lambda v: f'{v:0.4f}'
      )
    )
    print('\nBiggest overperformers versus budget:')
    print(model['residuals'].head(10).to_string(index=False))
  return 0


def _prune_stale_figures(keep: Iterable[pathlib.Path]) -> list[str]:
  """Deletes PNGs in the figures directory that this run did not write.

  Chart filenames are derived from metric names, so renaming a metric or
  dropping a chart would otherwise leave an orphan PNG behind that the
  report no longer links to.

  Args:
    keep (Iterable[pathlib.Path]): Figures produced by the current run.

  Returns:
    list[str]: Names of the removed files, sorted.
  """
  if not config.FIGURES_DIR.exists():
    return []
  wanted = {path.resolve() for path in keep}
  removed = []
  for existing in config.FIGURES_DIR.glob('*.png'):
    if existing.resolve() not in wanted:
      existing.unlink()
      removed.append(existing.name)
  return sorted(removed)


def command_report(args: argparse.Namespace) -> int:
  """Generates charts and the markdown report."""
  merged = insights.add_relative_spend(_load_analysis_table(args.season))
  correlations = analyze.correlation_table(merged)
  overlap = analyze.collinearity(merged)
  model = None
  try:
    model = analyze.fit_ols(
      merged, outcome=args.outcome, predictor=args.predictor
    )
  except ValueError as exc:
    logger.error('Regression skipped: %s', exc)

  analyze.write_outputs(merged, correlations, model, args.season)

  # One figure per idea.  The revenue-vs-spending panel already shows
  # both single-season scatters side by side, and win% duplicates the
  # point-margin view, so the individual scatters are not repeated.
  figures = []
  panel_figure = plots.revenue_vs_spending_panel(
    merged, 'point_margin_per_game', args.season
  )
  if panel_figure:
    figures.append(panel_figure)

  relative_summary = insights.relative_spend_summary(merged)
  relative_high, relative_low = insights.relative_spend_extremes(
    merged, sorted(config.POWER_CONFERENCES)
  )
  decomposition = insights.spending_decomposition(merged)
  decomposition.to_csv(
    config.PROCESSED_DIR / f'spending_decomposition_{args.season}.csv',
    index=False,
  )

  # Completed prior seasons give the small-sample 2026 numbers context.
  seasons = args.seasons or [args.season - offset for offset in range(4)]
  season_trend = None
  relative_by_season = None
  drivers = None
  schedule = None
  realignment_changes = None
  pac12_diaspora = None
  travel_by_shift = None
  travel_within_team = None
  realignment_travel = None
  try:
    panel = analyze.build_panel(sorted(seasons))
    season_trend = analyze.correlation_by_season(panel)
    history = plots.multi_season_scatter(
      panel, 'football_expenses', 'point_margin_per_game'
    )
    if history:
      figures.append(history)
    # Replaces the single-season relative chart: 2026 is the last panel.
    relative_panel = insights.add_relative_spend(panel)
    relative_by_season = insights.relative_spend_by_season(relative_panel)
    relative_history = plots.relative_spend_by_season(relative_panel)
    if relative_history:
      figures.append(relative_history)

    # Beyond the budget: momentum, repeatable over-performance and the
    # box-score markers of a good team.
    momentum_table, momentum = drivers_module.momentum_vs_money(
      panel, args.season
    )
    residuals = drivers_module.budget_residuals(panel)
    residual_lag, over, under = drivers_module.residual_persistence(
      residuals, args.season
    )
    residuals.to_csv(config.PROCESSED_DIR / 'budget_residuals.csv', index=False)
    markers = drivers_module.box_score_markers(panel, args.season)
    markers_chart = plots.box_score_markers_chart(markers)
    if markers_chart:
      figures.append(markers_chart)
    drivers = {
      'momentum_table': momentum_table,
      'momentum': momentum,
      'residual_lag': residual_lag,
      'over': over,
      'under': under,
      'markers': markers,
      'schedule_strength': drivers_module.schedule_strength(panel, args.season),
      'budget_change': drivers_module.budget_change_effect(panel, args.season),
    }

    games_by_season = {}
    for season in sorted(seasons):
      try:
        games_by_season[season] = build.read_frame('games', season)
      except FileNotFoundError:
        logger.debug('No games frame for %d', season)
    schedule = insights.schedule_split(panel, games_by_season)
    if not schedule.empty:
      schedule.to_csv(config.PROCESSED_DIR / 'schedule_split.csv', index=False)
      split_chart = plots.schedule_split_chart(schedule)
      if split_chart:
        figures.append(split_chart)

    # Realignment needs the same panel, so it rides along here.
    moves = realignment.detect_moves(panel)
    if not moves.empty:
      realignment_changes = realignment.before_after(panel, moves)
      pac12_diaspora = realignment.diaspora(panel, moves)
      realignment_changes.to_csv(
        config.PROCESSED_DIR / 'realignment_changes.csv', index=False
      )
      if not pac12_diaspora.empty:
        pac12_diaspora.to_csv(
          config.PROCESSED_DIR / 'pac12_diaspora.csv', index=False
        )
        chart = plots.pac12_diaspora_chart(pac12_diaspora)
        if chart:
          figures.append(chart)
      scatter = plots.realignment_scatter(realignment_changes)
      if scatter:
        figures.append(scatter)

    # Travel burden: does flying east cost points?
    offsets = travel.school_offsets(
      panel[panel['season'] == args.season][['school', 'state']]
    )
    if games_by_season and offsets:
      annotated = travel.add_travel_columns(
        pd.concat(games_by_season.values(), ignore_index=True), offsets
      )
      travel_by_shift = travel.performance_by_shift(annotated)
      travel_within_team = travel.within_team_travel_effect(annotated)
      if not moves.empty:
        realignment_travel = travel.realignment_travel_change(annotated, moves)
      travel.travel_burden(annotated).to_csv(
        config.PROCESSED_DIR / 'travel_burden.csv', index=False
      )
      travel_chart = plots.travel_penalty_chart(
        travel_by_shift if travel_by_shift is not None else pd.DataFrame(),
        travel_within_team,
      )
      if travel_chart:
        figures.append(travel_chart)
  except (ValueError, FileNotFoundError) as exc:
    logger.warning('Multi-season section skipped: %s', exc)

  box = plots.conference_money_box(merged, season=args.season)
  if box:
    figures.append(box)
  if model:
    bars = plots.residual_bars(model['residuals'], args.season)
    if bars:
      figures.append(bars)

  week = None
  try:
    week = espn.EspnClient(season=args.season).current_week()
  except espn.EspnError:
    logger.warning('Could not determine the current week')

  text = report_module.build_report(
    merged,
    correlations,
    model,
    analyze.conference_summary(merged),
    args.season,
    week,
    figures,
    figure_prefix='figures/',
    revenue_spending_overlap=overlap,
    season_trend=season_trend,
    realignment_changes=realignment_changes,
    pac12_diaspora=pac12_diaspora,
    travel_by_shift=travel_by_shift,
    travel_within_team=travel_within_team,
    realignment_travel=realignment_travel,
    schedule_split=schedule,
    relative_summary=relative_summary,
    relative_by_season=relative_by_season,
    drivers=drivers,
    relative_extremes=(relative_high, relative_low),
    decomposition=decomposition,
  )
  path = report_module.write_report(text, args.season)

  removed = _prune_stale_figures(pathlib.Path(p) for p in figures)
  if removed:
    logger.info(
      'Removed %d stale figure(s): %s', len(removed), ', '.join(removed)
    )
  print(f'Report written to {path}')
  return 0


def command_panel(args: argparse.Namespace) -> int:
  """Pools several seasons and tracks the correlation over time."""
  seasons = args.seasons or [args.season - offset for offset in range(3)]
  panel = analyze.build_panel(sorted(seasons))
  by_season = analyze.correlation_by_season(panel)
  if by_season.empty:
    logger.error('No season had enough matched teams for a correlation')
    return 1
  path = config.PROCESSED_DIR / 'correlation_by_season.csv'
  by_season.to_csv(path, index=False)
  figure = plots.money_vs_wins_history(panel)
  print('\nlog10(football revenue) vs win pct, by season:')
  print(by_season.to_string(index=False, float_format=lambda v: f'{v:0.3f}'))
  if figure:
    print(f'\nChart: {figure}')
  return 0


def command_refresh(args: argparse.Namespace) -> int:
  """Refreshes live data from ESPN and rebuilds the report."""
  status = command_fetch(args)
  if status:
    return status
  return command_report(args)


def command_all(args: argparse.Namespace) -> int:
  """Runs fetch, money and report in order.

  ``report`` writes every table ``analyze`` does, so running both would
  compute and write the same outputs twice.
  """
  for step in (command_fetch, command_money, command_report):
    status = step(args)
    if status:
      return status
  return 0


def build_parser() -> argparse.ArgumentParser:
  """Builds the argument parser."""
  parser = argparse.ArgumentParser(
    prog='cfbmoney', description=__doc__.splitlines()[0]
  )
  parser.add_argument('--verbose', action='store_true')
  parser.add_argument(
    '--season',
    type=int,
    default=config.DEFAULT_SEASON,
    help='Football season year (default: %(default)s)',
  )
  parser.add_argument(
    '--scope',
    choices=('power', 'fbs'),
    default='fbs',
    help='Which teams to fetch (default: %(default)s)',
  )
  parser.add_argument('--no-cache', action='store_true')
  parser.add_argument(
    '--fresh',
    action='store_true',
    help='Bypass cache to fetch latest scores and stats',
  )
  parser.add_argument(
    '--workers',
    type=int,
    default=8,
    help=(
      'Number of worker threads for parallel fetching (default: %(default)s)'
    ),
  )
  parser.add_argument(
    '--delay',
    type=float,
    default=None,
    help='Seconds to pause between uncached HTTP requests (overrides default)',
  )
  parser.add_argument(
    '--outcome',
    default='win_pct',
    help='Performance column for the regression',
  )
  parser.add_argument(
    '--predictor',
    default='football_revenue',
    help='Money column for the regression',
  )
  parser.add_argument('--no-conference-effects', action='store_true')
  parser.add_argument(
    '--years',
    type=int,
    nargs='+',
    default=None,
    help='EADA report years for the "money" command',
  )
  parser.add_argument(
    '--history',
    type=int,
    default=3,
    help='How many recent EADA years to download (default: %(default)s)',
  )
  parser.add_argument('--all-divisions', action='store_true')
  parser.add_argument(
    '--seasons',
    type=int,
    nargs='+',
    default=None,
    help='Seasons to pool for the "panel" command',
  )

  subparsers = parser.add_subparsers(dest='command', required=True)
  for name, handler, help_text in (
    ('fetch', command_fetch, 'Download results and stats from ESPN'),
    ('money', command_money, 'Download federal EADA finance filings'),
    ('analyze', command_analyze, 'Correlations and regression'),
    ('report', command_report, 'Charts and markdown report'),
    ('panel', command_panel, 'Pool seasons and trend the correlation'),
    ('refresh', command_refresh, 'Fetch latest data and rebuild report'),
    ('all', command_all, 'Run the whole pipeline'),
  ):
    subparser = subparsers.add_parser(name, help=help_text)
    subparser.set_defaults(handler=handler)
  return parser


def _normalize_cli_args(argv: list[str]) -> list[str]:
  """Ensures subcommands following multi-argument options parse cleanly.

  When flags with ``nargs='+'`` (such as ``--seasons`` or ``--years``)
  appear before a subcommand, standard argparse consumes the subcommand
  name into the list of values unless ``--`` separates them.  This
  helper inserts ``--`` before the subcommand if omitted.

  Args:
    argv: Raw argument strings.

  Returns:
    Normalized argument list.
  """
  subcommands = {
    'fetch',
    'money',
    'analyze',
    'report',
    'panel',
    'refresh',
    'all',
  }
  for i, arg in enumerate(argv):
    if arg in subcommands and i > 0 and argv[i - 1] != '--':
      preceding = argv[:i]
      for flag in ('--seasons', '--years'):
        if flag in preceding:
          flag_idx = preceding.index(flag)
          if '--' not in preceding[flag_idx:i]:
            return argv[:i] + ['--'] + argv[i:]
  return argv


def main(argv: list[str] | None = None) -> int:
  """CLI entry point.

  Args:
    argv: Optional argument vector.

  Returns:
    Process exit status.
  """
  raw_args = list(argv if argv is not None else sys.argv[1:])
  parser = build_parser()
  args = parser.parse_args(_normalize_cli_args(raw_args))
  _configure_logging(args.verbose)
  try:
    return args.handler(args)
  except (FileNotFoundError, ValueError, espn.EspnError, eada.EadaError) as exc:
    logger.error('%s', exc)
    return 1


if __name__ == '__main__':
  sys.exit(main())
