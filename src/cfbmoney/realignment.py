"""Conference realignment analysis.

Between the 2023 and 2026 seasons college football rewrote its map.  The
Pac-12 lost ten of its twelve members, the Big Ten and SEC absorbed the
most valuable brands, and the surviving Pac-12 rebuilt itself out of the
Mountain West.  That churn is a natural experiment for the question this
project asks: when a program changes conference, does its money change,
and does winning follow?

Two timing facts shape everything in this module:

* **The realignment happened in two waves.**  The 2024 wave moved the
  Pac-12 brands plus Texas and Oklahoma.  The 2026 wave rebuilt the
  Pac-12 from Mountain West and Sun Belt schools.
* **Federal finance data lags the field by about two years.**  EADA
  report year ``R`` describes academic year ``R-1`` to ``R``, which
  contains football season ``R-1``.  The newest filing available is
  report year 2025, so the newest observable money year is the 2024
  season.  For the 2024 wave that is exactly one post-move budget year.
  For the 2026 wave there is no post-move money at all yet, and this
  module reports that as missing rather than guessing.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# The Pac-12 was a power conference through 2023 and a rebuilt Group of
# Five style league from 2024 on, so tier membership has to be keyed by
# season rather than taken from the static ``is_power`` column.
_ALWAYS_POWER = frozenset({'ACC', 'Big 12', 'Big Ten', 'SEC'})

#: Season in which each realignment wave first took effect.
MOVE_WAVES = (2024, 2025, 2026)

#: Metrics compared before and after a move.
ONFIELD_METRICS = ('point_margin_per_game', 'win_pct')
MONEY_METRICS = ('football_revenue', 'football_expenses')


def conference_tier(conference: str, season: int) -> str:
  """Classifies a conference into a competitive tier for a season.

  Args:
    conference (str): Conference name as reported by ESPN.
    season (int): Football season.

  Returns:
    str: One of ``'power'``, ``'independent'`` or ``'group of five'``.
  """
  if conference in _ALWAYS_POWER:
    return 'power'
  if conference == 'Pac-12':
    return 'power' if season <= 2023 else 'group of five'
  if 'Independent' in str(conference):
    return 'independent'
  return 'group of five'


def conference_timeline(panel: pd.DataFrame) -> pd.DataFrame:
  """Pivots the panel into one row per school and one column per season.

  Args:
    panel (pd.DataFrame): Multi-season panel with ``school``, ``season``
      and ``conference`` columns.

  Returns:
    pd.DataFrame: Conference membership indexed by school.
  """
  required = {'school', 'season', 'conference'}
  missing = required - set(panel.columns)
  if missing:
    raise ValueError(f'Panel is missing columns: {sorted(missing)}')
  return panel.pivot_table(
    index='school',
    columns='season',
    values='conference',
    aggfunc='first',
  )


def detect_moves(panel: pd.DataFrame) -> pd.DataFrame:
  """Finds every school whose conference changed during the panel.

  A school is only counted once, using its first and last observed
  conference, so a school that moved twice is described by its net
  change.  ``move_season`` records the first season in which the
  conference differed from the baseline.

  Args:
    panel (pd.DataFrame): Multi-season panel.

  Returns:
    pd.DataFrame: One row per mover with origin, destination, the season
    the move took effect and the tier change it represented.
  """
  timeline = conference_timeline(panel)
  seasons = sorted(timeline.columns)
  if len(seasons) < 2:
    raise ValueError('Need at least two seasons to detect moves')

  rows = []
  for school, series in timeline.iterrows():
    observed = series.dropna()
    if len(observed) < 2:
      continue
    first_season = observed.index.min()
    last_season = observed.index.max()
    origin = observed.loc[first_season]
    destination = observed.loc[last_season]
    if origin == destination:
      continue
    changed = observed[observed != origin]
    move_season = int(changed.index.min())
    rows.append(
      {
        'school': school,
        'from_conference': origin,
        'to_conference': destination,
        'move_season': move_season,
        'from_tier': conference_tier(origin, int(first_season)),
        'to_tier': conference_tier(destination, int(last_season)),
      }
    )

  moves = pd.DataFrame(rows)
  if moves.empty:
    return moves

  order = {'group of five': 0, 'independent': 1, 'power': 2}
  moves['tier_change'] = [
    _describe_tier_change(order[row.from_tier], order[row.to_tier])
    for row in moves.itertuples()
  ]
  moves['move'] = moves['from_conference'] + ' to ' + moves['to_conference']
  return moves.sort_values(
    ['move_season', 'from_conference', 'school']
  ).reset_index(drop=True)


def _describe_tier_change(before: int, after: int) -> str:
  """Labels a tier transition.

  Args:
    before (int): Ordinal tier before the move.
    after (int): Ordinal tier after the move.

  Returns:
    str: ``'up'``, ``'down'`` or ``'lateral'``.
  """
  if after > before:
    return 'up'
  if after < before:
    return 'down'
  return 'lateral'


def money_observations(panel: pd.DataFrame) -> pd.DataFrame:
  """Collapses the panel to one row per school per finance year.

  The same EADA filing is joined onto several football seasons because
  the filings lag the field.  Averaging money across seasons would
  therefore double count a single filing, so this reduces the panel back
  to genuinely distinct observations and maps each filing to the
  football season it actually describes.

  Args:
    panel (pd.DataFrame): Multi-season panel.

  Returns:
    pd.DataFrame: Distinct finance observations with ``money_season``.
  """
  if 'money_report_year' not in panel.columns:
    raise ValueError('Panel has no money_report_year column')
  present = [m for m in MONEY_METRICS if m in panel.columns]
  frame = panel.dropna(subset=['money_report_year']).copy()
  frame['money_season'] = frame['money_report_year'].astype(int) - 1
  frame = frame.drop_duplicates(subset=['school', 'money_season'])
  return frame[['school', 'money_season', *present]]


def before_after(panel: pd.DataFrame, moves: pd.DataFrame) -> pd.DataFrame:
  """Compares each mover's metrics before and after its move.

  On-field metrics are averaged over the seasons on each side of the
  move.  Money metrics use the deduplicated finance observations, keyed
  by the football season each filing describes, so a school with no
  post-move filing yet gets ``NaN`` rather than a stale value.

  Args:
    panel (pd.DataFrame): Multi-season panel.
    moves (pd.DataFrame): Output of :func:`detect_moves`.

  Returns:
    pd.DataFrame: One row per mover with ``*_before``, ``*_after`` and
    ``*_change`` columns for each metric.
  """
  if moves.empty:
    return moves

  money = money_observations(panel)
  onfield = [m for m in ONFIELD_METRICS if m in panel.columns]
  money_metrics = [m for m in MONEY_METRICS if m in money.columns]

  rows = []
  for move in moves.itertuples():
    record = {
      'school': move.school,
      'move': move.move,
      'move_season': move.move_season,
      'tier_change': move.tier_change,
    }
    team = panel[panel['school'] == move.school]
    pre = team[team['season'] < move.move_season]
    post = team[team['season'] >= move.move_season]
    record['seasons_before'] = int(len(pre))
    record['seasons_after'] = int(len(post))
    for metric in onfield:
      record[f'{metric}_before'] = pre[metric].mean()
      record[f'{metric}_after'] = post[metric].mean()

    team_money = money[money['school'] == move.school]
    money_pre = team_money[team_money['money_season'] < move.move_season]
    money_post = team_money[team_money['money_season'] >= move.move_season]
    record['money_years_after'] = int(len(money_post))
    for metric in money_metrics:
      record[f'{metric}_before'] = money_pre[metric].mean()
      record[f'{metric}_after'] = money_post[metric].mean()
    rows.append(record)

  frame = pd.DataFrame(rows)
  for metric in [*onfield, *money_metrics]:
    before = frame.get(f'{metric}_before')
    after = frame.get(f'{metric}_after')
    if before is None or after is None:
      continue
    frame[f'{metric}_change'] = after - before
    if metric in money_metrics:
      frame[f'{metric}_pct_change'] = np.where(
        before.to_numpy() > 0,
        (after.to_numpy() - before.to_numpy()) / before.to_numpy() * 100.0,
        np.nan,
      )
  return frame


def diaspora(
  panel: pd.DataFrame,
  moves: pd.DataFrame,
  conference: str = 'Pac-12',
  baseline_season: int = 2023,
) -> pd.DataFrame:
  """Splits a conference's schools into leavers, stayers and joiners.

  The Pac-12 breakup is the cleanest case in the data: the schools that
  left, the two that stayed behind, and the schools that later joined
  the rebuilt league all experienced the same shock from different
  sides.

  Args:
    panel (pd.DataFrame): Multi-season panel.
    moves (pd.DataFrame): Output of :func:`detect_moves`.
    conference (str): Conference to analyse.
    baseline_season (int): Season defining original membership.

  Returns:
    pd.DataFrame: Movement rows tagged with a ``role`` column.
  """
  timeline = conference_timeline(panel)
  if baseline_season not in timeline.columns:
    raise ValueError(f'Season {baseline_season} is not in the panel')
  latest = max(timeline.columns)

  original = set(timeline.index[timeline[baseline_season] == conference])
  current = set(timeline.index[timeline[latest] == conference])

  roles = {}
  for school in original & current:
    roles[school] = 'stayed'
  for school in original - current:
    roles[school] = 'left'
  for school in current - original:
    roles[school] = 'joined'
  if not roles:
    return pd.DataFrame()

  changes = before_after(panel, moves)
  stayed = sorted(original & current)
  if stayed:
    # Schools that never moved are absent from ``moves`` but are the
    # control group, so synthesise rows for them using the season the
    # league actually broke apart.
    breakup = _breakup_season(moves, conference)
    synthetic = pd.DataFrame(
      {
        'school': stayed,
        'from_conference': conference,
        'to_conference': conference,
        'move_season': breakup,
        'move': f'{conference} (stayed)',
        'tier_change': 'stranded',
        'from_tier': conference_tier(conference, baseline_season),
        'to_tier': conference_tier(conference, latest),
      }
    )
    changes = pd.concat(
      [changes, before_after(panel, synthetic)], ignore_index=True
    )

  changes = changes[changes['school'].isin(roles)].copy()
  changes['role'] = changes['school'].map(roles)
  order = {'left': 0, 'stayed': 1, 'joined': 2}
  return changes.sort_values(
    ['role', 'school'],
    key=lambda col: col.map(order) if col.name == 'role' else col,
  ).reset_index(drop=True)


def _breakup_season(moves: pd.DataFrame, conference: str) -> int:
  """Finds the season a conference first lost members.

  Args:
    moves (pd.DataFrame): Output of :func:`detect_moves`.
    conference (str): Conference that lost members.

  Returns:
    int: Season of the first departure, or the earliest wave.
  """
  departures = moves[moves['from_conference'] == conference]
  if departures.empty:
    return MOVE_WAVES[0]
  return int(departures['move_season'].min())


def _change_columns(changes: pd.DataFrame) -> list[str]:
  """Returns the numeric before/after delta columns.

  ``tier_change`` also ends in ``_change`` but holds text, so the filter
  has to check dtype rather than the name alone.

  Args:
    changes (pd.DataFrame): Output of :func:`before_after`.

  Returns:
    list[str]: Numeric delta column names.
  """
  return [
    column
    for column in changes.columns
    if column.endswith(('_change', '_pct_change'))
    and pd.api.types.is_numeric_dtype(changes[column])
  ]


def summarize_by_move(changes: pd.DataFrame) -> pd.DataFrame:
  """Aggregates before and after changes by origin and destination.

  Args:
    changes (pd.DataFrame): Output of :func:`before_after`.

  Returns:
    pd.DataFrame: Median change per move grouped by route.
  """
  if changes.empty:
    return changes
  value_columns = _change_columns(changes)
  grouped = (
    changes.groupby('move')
    .agg(
      schools=('school', 'count'),
      move_season=('move_season', 'min'),
      **{col: (col, 'median') for col in value_columns},
    )
    .reset_index()
  )
  return grouped.sort_values('move_season').reset_index(drop=True)


def tier_summary(changes: pd.DataFrame) -> pd.DataFrame:
  """Aggregates changes by whether the move was up, down or lateral.

  Args:
    changes (pd.DataFrame): Output of :func:`before_after`.

  Returns:
    pd.DataFrame: Median change per tier transition.
  """
  if changes.empty:
    return changes
  value_columns = _change_columns(changes)
  return (
    changes.groupby('tier_change')
    .agg(
      schools=('school', 'count'),
      **{col: (col, 'median') for col in value_columns},
    )
    .reset_index()
  )
