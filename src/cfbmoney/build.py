"""Turns raw ESPN payloads into tidy pandas frames.

Three tables come out of here:

``teams``    one row per FBS team (identity + conference).
``games``    one row per team-game (long format, so each game appears
             twice - once from each team's perspective).
``team_season``  one row per team with record, scoring and efficiency
             statistics aggregated over the season to date.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

import pandas as pd

from . import config
from . import espn as espn_module

logger = logging.getLogger(__name__)

# Season statistics pulled out of ESPN's category tree.  Keys are
# ``<category>.<stat name>`` and values are the output column names.
STAT_FIELDS: dict[str, str] = {
  'passing.netPassingYardsPerGame': 'pass_yards_per_game',
  'passing.completionPct': 'completion_pct',
  'passing.interceptions': 'interceptions_thrown',
  'passing.QBRating': 'passer_rating',
  'rushing.rushingYardsPerGame': 'rush_yards_per_game',
  'rushing.yardsPerRushAttempt': 'yards_per_carry',
  'general.totalYardsPerGame': 'total_yards_per_game',
  'general.thirdDownConvPct': 'third_down_pct',
  'general.turnOverDifferential': 'turnover_differential',
  'general.fumblesLost': 'fumbles_lost',
  'scoring.totalPointsPerGame': 'points_per_game',
  'defensive.totalTackles': 'total_tackles',
  'defensive.sacks': 'sacks',
  'defensive.tacklesForLoss': 'tackles_for_loss',
  'defensiveInterceptions.interceptions': 'interceptions_caught',
}


def build_teams_frame(teams: list[dict[str, Any]]) -> pd.DataFrame:
  """Creates the team directory frame.

  Args:
    teams: Records produced by :meth:`espn.EspnClient.list_teams`.

  Returns:
    A frame indexed by position with one row per team.
  """
  frame = pd.DataFrame(teams)
  frame = frame.dropna(subset=['school']).drop_duplicates('team_id')
  return frame.sort_values(['conference', 'school']).reset_index(drop=True)


def _competitor_score(competitor: dict[str, Any]) -> float | None:
  """Extracts a numeric score from an ESPN competitor block."""
  score = competitor.get('score')
  if isinstance(score, dict):
    value = score.get('value')
    if value is not None:
      return float(value)
    display = score.get('displayValue')
    if display not in (None, ''):
      try:
        return float(display)
      except ValueError:
        return None
  if isinstance(score, int | float):
    return float(score)
  return None


def build_games_frame(
  client: espn_module.EspnClient,
  teams_frame: pd.DataFrame,
) -> pd.DataFrame:
  """Fetches every team's schedule and flattens it to team-games.

  Args:
    client: A configured ESPN client.
    teams_frame: Output of :func:`build_teams_frame`.

  Returns:
    One row per team-game with result, scores and context columns.
  """
  rows: list[dict[str, Any]] = []
  for record in teams_frame.to_dict('records'):
    team_id = record['team_id']
    try:
      payload = client.get_team_schedule(team_id)
    except espn_module.EspnError as exc:
      logger.warning('No schedule for %s: %s', record['school'], exc)
      continue

    for event in payload.get('events', []):
      competitions = event.get('competitions') or []
      if not competitions:
        continue
      competition = competitions[0]
      competitors = competition.get('competitors') or []
      me = next(
        (c for c in competitors if str(c.get('id')) == str(team_id)),
        None,
      )
      other = next(
        (c for c in competitors if str(c.get('id')) != str(team_id)),
        None,
      )
      if me is None or other is None:
        continue

      status = competition.get('status', {}).get('type', {}).get('name', '')
      completed = status == 'STATUS_FINAL'
      points_for = _competitor_score(me)
      points_against = _competitor_score(other)
      winner = me.get('winner')
      if winner is None and completed and points_for is not None:
        winner = points_for > (points_against or 0)

      rows.append(
        {
          'season': client.season,
          'game_id': competition.get('id') or event.get('id'),
          'date': event.get('date'),
          'week': (event.get('week') or {}).get('number'),
          'team_id': team_id,
          'school': record['school'],
          'conference': record['conference'],
          'opponent_id': other.get('id'),
          'opponent': other.get('team', {}).get('location'),
          'home_away': me.get('homeAway'),
          'neutral_site': bool(competition.get('neutralSite')),
          'conference_game': bool(competition.get('conferenceCompetition')),
          'completed': completed,
          'status': status,
          'points_for': points_for,
          'points_against': points_against,
          'won': bool(winner) if completed else None,
          'attendance': competition.get('attendance'),
          'venue': (competition.get('venue') or {}).get('fullName'),
        }
      )

  frame = pd.DataFrame(rows)
  if frame.empty:
    return frame
  frame['date'] = pd.to_datetime(frame['date'], errors='coerce', utc=True)
  return frame.sort_values(['school', 'date']).reset_index(drop=True)


def flatten_team_stats(payload: dict[str, Any]) -> dict[str, float]:
  """Flattens ESPN's nested season statistics payload.

  Args:
    payload: Response from
      :meth:`espn.EspnClient.get_team_season_stats`.

  Returns:
    A mapping of output column name to numeric value for the subset of
    statistics listed in :data:`STAT_FIELDS`.
  """
  out: dict[str, float] = {}
  categories = (payload.get('splits') or {}).get('categories') or []
  for category in categories:
    cat_name = category.get('name')
    for stat in category.get('stats') or []:
      key = f'{cat_name}.{stat.get("name")}'
      column = STAT_FIELDS.get(key)
      if column is None:
        continue
      value = stat.get('value')
      if value is None:
        try:
          value = float(str(stat.get('displayValue', '')).replace(',', ''))
        except ValueError:
          continue
      out[column] = float(value)
  return out


def build_stats_frame(
  client: espn_module.EspnClient,
  teams_frame: pd.DataFrame,
) -> pd.DataFrame:
  """Fetches season statistics for every team.

  Args:
    client: A configured ESPN client.
    teams_frame: Output of :func:`build_teams_frame`.

  Returns:
    One row per team with the statistics in :data:`STAT_FIELDS`.
  """
  rows: list[dict[str, Any]] = []
  for record in teams_frame.to_dict('records'):
    try:
      payload = client.get_team_season_stats(record['team_id'])
    except espn_module.EspnError as exc:
      logger.warning('No stats for %s: %s', record['school'], exc)
      continue
    stats = flatten_team_stats(payload)
    if not stats:
      continue
    stats.update(
      {
        'team_id': record['team_id'],
        'school': record['school'],
      }
    )
    rows.append(stats)
  return pd.DataFrame(rows)


def _opponent_strength(games: pd.DataFrame) -> pd.DataFrame:
  """Computes a simple opponent win-percentage strength of schedule.

  Args:
    games: The team-game frame.

  Returns:
    A frame with ``school`` and ``opponent_win_pct`` columns.
  """
  completed = games[games['completed'] & games['won'].notna()]
  if completed.empty:
    return pd.DataFrame(columns=['school', 'opponent_win_pct'])
  record = (
    completed.groupby('school')['won']
    .mean()
    .rename('team_win_pct')
    .reset_index()
  )
  merged = completed.merge(
    record,
    left_on='opponent',
    right_on='school',
    how='left',
    suffixes=('', '_opp'),
  )
  strength = (
    merged.groupby('school')['team_win_pct']
    .mean()
    .rename('opponent_win_pct')
    .reset_index()
  )
  return strength


def build_team_season_frame(
  teams_frame: pd.DataFrame,
  games: pd.DataFrame,
  stats: pd.DataFrame,
) -> pd.DataFrame:
  """Aggregates games and statistics into one row per team.

  Args:
    teams_frame: Team directory.
    games: Team-game frame.
    stats: Season statistics frame.

  Returns:
    The season summary frame.
  """
  if games.empty:
    raise ValueError('No games available; fetch the season first.')

  played = games[games['completed'] & games['won'].notna()].copy()
  grouped = played.groupby('school')
  summary = pd.DataFrame(
    {
      'games_played': grouped.size(),
      'wins': grouped['won'].sum(),
      'points_for': grouped['points_for'].sum(),
      'points_against': grouped['points_against'].sum(),
    }
  ).reset_index()
  summary['wins'] = summary['wins'].astype(int)
  summary['losses'] = summary['games_played'] - summary['wins']
  summary['win_pct'] = summary['wins'] / summary['games_played']
  summary['points_per_game'] = summary['points_for'] / summary['games_played']
  summary['points_allowed_per_game'] = (
    summary['points_against'] / summary['games_played']
  )
  summary['point_margin_per_game'] = (
    summary['points_per_game'] - summary['points_allowed_per_game']
  )

  scheduled = (
    games.groupby('school').size().rename('games_scheduled').reset_index()
  )

  frame = teams_frame.merge(summary, on='school', how='left')
  frame = frame.merge(scheduled, on='school', how='left')
  frame = frame.merge(_opponent_strength(games), on='school', how='left')
  if not stats.empty:
    stat_columns = [
      c for c in stats.columns if c not in ('team_id', 'points_per_game')
    ]
    frame = frame.merge(stats[stat_columns], on='school', how='left')
  frame['season'] = games['season'].iloc[0]
  return frame.sort_values(
    ['win_pct', 'point_margin_per_game'], ascending=False
  ).reset_index(drop=True)


def dedupe_games(games: pd.DataFrame) -> pd.DataFrame:
  """Collapses the long team-game frame to one row per game.

  Args:
    games: Team-game frame.

  Returns:
    A frame with one row per unique ``game_id``.
  """
  if games.empty:
    return games
  return games.drop_duplicates('game_id').reset_index(drop=True)


def write_frames(frames: dict[str, pd.DataFrame], season: int) -> None:
  """Writes frames to ``data/processed`` as CSV files.

  Args:
    frames: Mapping of logical table name to frame.
    season: Season year, used in the filenames.
  """
  config.ensure_directories()
  for name, frame in frames.items():
    path = config.PROCESSED_DIR / f'{name}_{season}.csv'
    frame.to_csv(path, index=False)
    logger.info('Wrote %s rows to %s', len(frame), path)


def read_frame(name: str, season: int) -> pd.DataFrame:
  """Reads a previously written processed frame.

  Args:
    name: Logical table name, e.g. ``team_season``.
    season: Season year.

  Returns:
    The frame.

  Raises:
    FileNotFoundError: If the table has not been built yet.
  """
  path = config.PROCESSED_DIR / f'{name}_{season}.csv'
  if not path.exists():
    raise FileNotFoundError(
      f'{path} is missing; run "python -m cfbmoney fetch" first.'
    )
  return pd.read_csv(path)


def iter_headline(schools: Iterable[str]) -> list[str]:
  """Returns the configured headline programs present in ``schools``."""
  available = set(schools)
  return [s for s in config.HEADLINE_PROGRAMS if s in available]
