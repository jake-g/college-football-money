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
from . import espn
from . import finance
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
  client = espn.EspnClient(season=args.season, use_cache=not args.no_cache)
  teams = build.build_teams_frame(client.list_teams(_group_ids(args.scope)))
  logger.info('Fetched %d teams', len(teams))

  games = build.build_games_frame(client, teams)
  logger.info(
    'Fetched %d team-games (%d completed)',
    len(games),
    int(games['completed'].sum()),
  )
  stats = build.build_stats_frame(client, teams)
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
  merged = _load_analysis_table(args.season)
  correlations = analyze.correlation_table(merged)
  comparison = analyze.revenue_vs_spending(merged)
  overlap = analyze.collinearity(merged)
  model = None
  try:
    model = analyze.fit_ols(
      merged, outcome=args.outcome, predictor=args.predictor
    )
  except ValueError as exc:
    logger.error('Regression skipped: %s', exc)

  figures = []
  panel_figure = plots.revenue_vs_spending_panel(
    merged, 'point_margin_per_game', args.season
  )
  if panel_figure:
    figures.append(panel_figure)

  for money_column in (
    'football_expenses',
    'football_revenue',
    'football_spend_per_player',
  ):
    if money_column in merged.columns:
      for outcome in ('point_margin_per_game', 'win_pct'):
        path = plots.scatter_money_vs_performance(
          merged, money_column, outcome, args.season
        )
        if path:
          figures.append(path)

  # Completed prior seasons give the small-sample 2026 numbers context.
  seasons = args.seasons or [args.season - offset for offset in range(4)]
  season_trend = None
  realignment_changes = None
  pac12_diaspora = None
  travel_by_shift = None
  travel_within_team = None
  realignment_travel = None
  try:
    panel = analyze.build_panel(sorted(seasons))
    season_trend = analyze.correlation_by_season(panel)
    for money_column in ('football_expenses', 'football_revenue'):
      history = plots.multi_season_scatter(
        panel, money_column, 'point_margin_per_game'
      )
      if history:
        figures.append(history)
    # Per-player spend across seasons shows how the arms race compounds.
    for outcome in ('win_pct', 'point_margin_per_game'):
      per_player = plots.multi_season_scatter(
        panel, 'football_spend_per_player', outcome
      )
      if per_player:
        figures.append(per_player)
    trend = plots.money_vs_wins_history(panel)
    if trend:
      figures.append(trend)

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
    all_games = []
    for season in sorted(seasons):
      try:
        all_games.append(build.read_frame('games', season))
      except FileNotFoundError:
        logger.debug('No games frame for %d', season)
    if all_games and offsets:
      annotated = travel.add_travel_columns(
        pd.concat(all_games, ignore_index=True), offsets
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
    comparison=comparison,
    revenue_spending_overlap=overlap,
    season_trend=season_trend,
    realignment_changes=realignment_changes,
    pac12_diaspora=pac12_diaspora,
    travel_by_shift=travel_by_shift,
    travel_within_team=travel_within_team,
    realignment_travel=realignment_travel,
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


def command_all(args: argparse.Namespace) -> int:
  """Runs fetch, money, analyze and report in order."""
  for step in (command_fetch, command_money, command_analyze, command_report):
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
    ('all', command_all, 'Run the whole pipeline'),
  ):
    subparser = subparsers.add_parser(name, help=help_text)
    subparser.set_defaults(handler=handler)
  return parser


def main(argv: list[str] | None = None) -> int:
  """CLI entry point.

  Args:
    argv: Optional argument vector.

  Returns:
    Process exit status.
  """
  parser = build_parser()
  args = parser.parse_args(argv)
  _configure_logging(args.verbose)
  try:
    return args.handler(args)
  except (FileNotFoundError, ValueError, espn.EspnError, eada.EadaError) as exc:
    logger.error('%s', exc)
    return 1


if __name__ == '__main__':
  sys.exit(main())
