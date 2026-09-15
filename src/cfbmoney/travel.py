"""Travel and time-zone burden analysis.

Conference realignment did not just move money, it moved *miles*. When
USC and UCLA joined the Big Ten they swapped a conference that fit
inside two time zones for one that spans three, and Washington State and
Oregon State were left rebuilding a schedule from scratch. A natural
question follows: do teams play worse when they travel east across time
zones?

The mechanism is real and well documented in other sports. An athlete
travelling east loses hours; a 9am Pacific body clock has to perform at
what feels like 6am. This module measures that burden from the schedule
and tests whether it shows up in the score.

Time zones are derived from each school's state, with explicit overrides
for the handful of FBS programs that sit on the wrong side of a
split-state boundary (El Paso, Boise, Knoxville, Bowling Green KY).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

#: Standard-time UTC offsets by US state.  Football is played during
#: daylight saving time, but the *difference* between two zones is what
#: matters here and that is unchanged, with one exception noted below.
STATE_UTC_OFFSET: dict[str, int] = {
  # Pacific
  'CA': -8,
  'WA': -8,
  'OR': -8,
  'NV': -8,
  # Mountain
  'AZ': -7,
  'CO': -7,
  'UT': -7,
  'NM': -7,
  'WY': -7,
  'MT': -7,
  # Central
  'TX': -6,
  'OK': -6,
  'KS': -6,
  'NE': -6,
  'SD': -6,
  'ND': -6,
  'MN': -6,
  'IA': -6,
  'MO': -6,
  'AR': -6,
  'LA': -6,
  'MS': -6,
  'AL': -6,
  'WI': -6,
  'IL': -6,
  'TN': -6,
  # Eastern
  'MI': -5,
  'IN': -5,
  'OH': -5,
  'KY': -5,
  'GA': -5,
  'FL': -5,
  'SC': -5,
  'NC': -5,
  'VA': -5,
  'WV': -5,
  'MD': -5,
  'DE': -5,
  'PA': -5,
  'NJ': -5,
  'NY': -5,
  'CT': -5,
  'RI': -5,
  'MA': -5,
  'VT': -5,
  'NH': -5,
  'ME': -5,
  'DC': -5,
  # Outside the contiguous zones
  'HI': -10,
  'AK': -9,
}

#: Schools whose campus is in a different zone from most of their state.
SCHOOL_UTC_OFFSET: dict[str, int] = {
  'UTEP': -7,  # El Paso is Mountain; the rest of Texas is Central.
  'Boise State': -7,  # Southern Idaho is Mountain.
  'Tennessee': -5,  # Knoxville is Eastern; Nashville and Memphis are not.
  'Western Kentucky': -6,  # Bowling Green is Central.
}

#: Labels for how far east or west a team travelled.
SHIFT_LABELS = {
  -3: '3 zones west',
  -2: '2 zones west',
  -1: '1 zone west',
  0: 'same zone',
  1: '1 zone east',
  2: '2 zones east',
  3: '3 zones east',
}


def school_offsets(frame: pd.DataFrame) -> dict[str, int]:
  """Maps each school to its UTC offset.

  Args:
    frame (pd.DataFrame): Frame with ``school`` and ``state`` columns.

  Returns:
    dict[str, int]: School to standard-time UTC offset.
  """
  if not {'school', 'state'}.issubset(frame.columns):
    raise ValueError('Frame needs school and state columns')
  offsets = {}
  unknown = set()
  for row in frame.dropna(subset=['state']).itertuples():
    if row.school in SCHOOL_UTC_OFFSET:
      offsets[row.school] = SCHOOL_UTC_OFFSET[row.school]
      continue
    offset = STATE_UTC_OFFSET.get(str(row.state).strip().upper())
    if offset is None:
      unknown.add(str(row.state))
      continue
    offsets[row.school] = offset
  if unknown:
    logger.warning('No time zone for states: %s', sorted(unknown))
  return offsets


def add_travel_columns(
  games: pd.DataFrame,
  offsets: dict[str, int],
) -> pd.DataFrame:
  """Annotates each team-game with its time-zone shift.

  Home games have a shift of zero by construction. Neutral-site games are
  excluded because the schedule feed does not say where they were played
  in a way that can be mapped to a zone.

  Args:
    games (pd.DataFrame): Long team-game frame.
    offsets (dict[str, int]): School to UTC offset.

  Returns:
    pd.DataFrame: Games with ``home_offset``, ``venue_offset`` and
    ``tz_shift`` columns.  Positive ``tz_shift`` means travelling east.
  """
  required = {'school', 'opponent', 'home_away'}
  missing = required - set(games.columns)
  if missing:
    raise ValueError(f'Games frame is missing: {sorted(missing)}')

  frame = games.copy()
  frame['home_offset'] = frame['school'].map(offsets)
  opponent_offset = frame['opponent'].map(offsets)
  is_away = frame['home_away'].eq('away')
  frame['venue_offset'] = np.where(
    is_away, opponent_offset, frame['home_offset']
  )
  if 'neutral_site' in frame.columns:
    frame.loc[
      frame['neutral_site'].fillna(False).astype(bool), 'venue_offset'
    ] = np.nan
  frame['tz_shift'] = frame['venue_offset'] - frame['home_offset']
  return frame


def travel_burden(games: pd.DataFrame) -> pd.DataFrame:
  """Summarises how far each team travels per season.

  Args:
    games (pd.DataFrame): Output of :func:`add_travel_columns`.

  Returns:
    pd.DataFrame: One row per school-season with trip counts.
  """
  away = games[games['home_away'].eq('away')].dropna(subset=['tz_shift'])
  if away.empty:
    return pd.DataFrame()
  grouped = away.groupby(['season', 'school'], as_index=False).agg(
    away_games=('tz_shift', 'size'),
    mean_tz_shift=('tz_shift', 'mean'),
    eastward_trips=('tz_shift', lambda s: int((s > 0).sum())),
    long_eastward_trips=('tz_shift', lambda s: int((s >= 2).sum())),
    max_tz_shift=('tz_shift', 'max'),
  )
  return grouped.sort_values(
    ['season', 'long_eastward_trips'], ascending=[True, False]
  ).reset_index(drop=True)


def performance_by_shift(
  games: pd.DataFrame,
  away_only: bool = True,
) -> pd.DataFrame:
  """Aggregates completed-game results by time-zone shift.

  Home games are a zero shift by construction, so including them would
  put every home game in the "same zone" bucket and the chart would
  measure home-field advantage rather than travel.  ``away_only``
  defaults to ``True`` so the comparison is like for like: every row is
  a road trip, and the only thing varying is how far it was.

  Args:
    games (pd.DataFrame): Output of :func:`add_travel_columns`.
    away_only (bool): Restrict to away games.

  Returns:
    pd.DataFrame: Mean margin and win rate for each shift bucket.
  """
  played = games.copy()
  if away_only:
    played = played[played['home_away'].eq('away')]
  played = played[played['completed'].fillna(False).astype(bool)].copy()
  played = played.dropna(subset=['tz_shift', 'points_for', 'points_against'])
  if played.empty:
    return pd.DataFrame()
  played['margin'] = played['points_for'] - played['points_against']
  played['shift'] = played['tz_shift'].astype(int)
  summary = played.groupby('shift', as_index=False).agg(
    games=('margin', 'size'),
    mean_margin=('margin', 'mean'),
    win_rate=('won', 'mean'),
    points_for=('points_for', 'mean'),
    points_against=('points_against', 'mean'),
  )
  summary['label'] = summary['shift'].map(SHIFT_LABELS)
  return summary.sort_values('shift').reset_index(drop=True)


def away_game_penalty(games: pd.DataFrame) -> pd.DataFrame:
  """Isolates the travel effect within away games only.

  Home games are always a zero shift, so pooling them would confound
  travel distance with home-field advantage. This restricts to away
  games and asks whether *further* travel is worse than *nearby* travel.

  Args:
    games (pd.DataFrame): Output of :func:`add_travel_columns`.

  Returns:
    pd.DataFrame: Away-game results bucketed by eastward shift.
  """
  away = games[games['home_away'].eq('away')].copy()
  away = away[away['completed'].fillna(False).astype(bool)]
  away = away.dropna(subset=['tz_shift', 'points_for', 'points_against'])
  if away.empty:
    return pd.DataFrame()
  away['margin'] = away['points_for'] - away['points_against']
  away['bucket'] = np.select(
    [
      away['tz_shift'] <= -1,
      away['tz_shift'] == 0,
      away['tz_shift'] == 1,
      away['tz_shift'] >= 2,
    ],
    ['travelled west', 'same zone', '1 zone east', '2+ zones east'],
    default='unknown',
  )
  order = ['travelled west', 'same zone', '1 zone east', '2+ zones east']
  summary = away.groupby('bucket', as_index=False).agg(
    games=('margin', 'size'),
    mean_margin=('margin', 'mean'),
    win_rate=('won', 'mean'),
  )
  summary['bucket'] = pd.Categorical(
    summary['bucket'], categories=order, ordered=True
  )
  return summary.sort_values('bucket').dropna(subset=['bucket'])


def realignment_travel_change(
  games: pd.DataFrame,
  movers: pd.DataFrame,
) -> pd.DataFrame:
  """Compares travel burden before and after each conference move.

  Args:
    games (pd.DataFrame): Output of :func:`add_travel_columns`.
    movers (pd.DataFrame): Output of ``realignment.detect_moves``.

  Returns:
    pd.DataFrame: Travel and results before and after the move.
  """
  if movers.empty:
    return pd.DataFrame()
  away = games[games['home_away'].eq('away')].dropna(subset=['tz_shift'])
  played = away[away['completed'].fillna(False).astype(bool)].copy()
  played['margin'] = played['points_for'] - played['points_against']

  rows = []
  for move in movers.itertuples():
    team = played[played['school'] == move.school]
    if team.empty:
      continue
    pre = team[team['season'] < move.move_season]
    post = team[team['season'] >= move.move_season]
    if pre.empty or post.empty:
      continue
    rows.append(
      {
        'school': move.school,
        'move': move.move,
        'move_season': move.move_season,
        'mean_tz_shift_before': pre['tz_shift'].mean(),
        'mean_tz_shift_after': post['tz_shift'].mean(),
        'long_trips_before': int((pre['tz_shift'] >= 2).sum()),
        'long_trips_after': int((post['tz_shift'] >= 2).sum()),
        'away_margin_before': pre['margin'].mean(),
        'away_margin_after': post['margin'].mean(),
      }
    )
  frame = pd.DataFrame(rows)
  if frame.empty:
    return frame
  frame['tz_shift_change'] = (
    frame['mean_tz_shift_after'] - frame['mean_tz_shift_before']
  )
  frame['away_margin_change'] = (
    frame['away_margin_after'] - frame['away_margin_before']
  )
  return frame.sort_values('tz_shift_change', ascending=False).reset_index(
    drop=True
  )


def within_team_travel_effect(games: pd.DataFrame) -> dict[str, float]:
  """Measures the long-trip penalty holding team quality constant.

  Comparing long eastward trips against all other away games across the
  whole league confounds travel with quality: the teams that fly two
  zones east are disproportionately Group of Five programs taking a
  paycheque game at a blue blood. This pairs each team against *itself*,
  comparing its own away margin on long eastward trips with its own away
  margin on every other away game, then averages those differences.

  Args:
    games (pd.DataFrame): Output of :func:`add_travel_columns`.

  Returns:
    dict[str, float]: ``teams`` compared, mean ``penalty`` in points and
    the two component averages.
  """
  away = games[games['home_away'].eq('away')].dropna(subset=['tz_shift'])
  played = away[away['completed'].fillna(False).astype(bool)].copy()
  if played.empty:
    return {}
  played['margin'] = played['points_for'] - played['points_against']
  played['long_east'] = played['tz_shift'] >= 2

  differences = []
  long_means = []
  other_means = []
  for (_, _), group in played.groupby(['season', 'school']):
    long_trips = group[group['long_east']]
    other = group[~group['long_east']]
    if long_trips.empty or other.empty:
      continue
    long_mean = float(long_trips['margin'].mean())
    other_mean = float(other['margin'].mean())
    differences.append(long_mean - other_mean)
    long_means.append(long_mean)
    other_means.append(other_mean)

  if not differences:
    return {}
  return {
    'teams': float(len(differences)),
    'penalty': float(np.mean(differences)),
    'long_trip_margin': float(np.mean(long_means)),
    'other_away_margin': float(np.mean(other_means)),
  }
