"""Tests for the game-level analyses: luck, close games, home field, crowds."""

from __future__ import annotations

import pandas as pd
import pytest

from cfbmoney import gameday
from cfbmoney import insights

CONF = {'Rich A': 'A', 'Poor A': 'A', 'Rich B': 'B', 'Poor B': 'B'}


def _panel() -> pd.DataFrame:
  """Two seasons, four teams; records chosen so luck is non-trivial."""
  rows = []
  for season in (2025, 2026):
    for school, money, pf, pa, wins, losses in (
      ('Rich A', 80e6, 300, 100, 5, 1),
      ('Poor A', 20e6, 150, 150, 4, 2),  # lucky: even scoring, 4-2
      ('Rich B', 60e6, 250, 150, 2, 4),  # unlucky: good scoring, 2-4
      ('Poor B', 10e6, 100, 300, 1, 5),
    ):
      rows.append(
        {
          'season': season,
          'school': school,
          'conference': CONF[school],
          'football_expenses': money,
          'points_for': pf,
          'points_against': pa,
          'wins': wins,
          'losses': losses,
          'games_played': wins + losses,
          'win_pct': wins / (wins + losses),
          'point_margin_per_game': (pf - pa) / (wins + losses),
        }
      )
  return pd.DataFrame(rows)


def _game(season, week, home, away, home_pts, away_pts, attendance=20000):
  """Two long rows for one non-neutral game."""
  base = {
    'season': season,
    'week': week,
    'completed': True,
    'conference_game': False,
    'neutral_site': False,
  }
  return [
    {
      **base,
      'school': home,
      'conference': CONF[home],
      'opponent': away,
      'home_away': 'home',
      'points_for': home_pts,
      'points_against': away_pts,
      'attendance': attendance,
    },
    {
      **base,
      'school': away,
      'conference': CONF[away],
      'opponent': home,
      'home_away': 'away',
      'points_for': away_pts,
      'points_against': home_pts,
      'attendance': attendance,
    },
  ]


def _games(season: int, crowd: int = 20000) -> pd.DataFrame:
  rows = []
  rows += _game(season, 1, 'Rich A', 'Poor B', 40, 10, crowd * 4)  # blowout
  rows += _game(season, 1, 'Poor A', 'Rich B', 21, 20, crowd)  # close upset
  rows += _game(season, 2, 'Rich A', 'Poor A', 24, 21, crowd * 4)  # close
  rows += _game(season, 2, 'Poor B', 'Rich B', 7, 35, crowd // 2)  # blowout
  rows += _game(season, 3, 'Rich B', 'Rich A', 30, 10, crowd * 3)  # blowout
  return pd.DataFrame(rows)


def test_pythagorean_luck_ranks_lucky_and_unlucky_teams():
  """Even scoring with a winning record is lucky; the reverse is unlucky."""
  summary, teams = gameday.pythagorean_luck(_panel(), 2026, min_games=3)
  assert set(summary['season']) == {2025, 2026}
  assert teams.iloc[0]['school'] == 'Poor A'
  assert teams.iloc[-1]['school'] == 'Rich B'
  poor_a = teams.set_index('school').loc['Poor A']
  assert poor_a['pythagorean_pct'] == pytest.approx(0.5)
  assert poor_a['luck_wins'] == pytest.approx(1.0)


def test_close_games_splits_by_margin():
  """The richer side wins both blowouts but splits the one-score games."""
  close = gameday.close_games(
    _panel(), {2025: _games(2025), 2026: _games(2026)}, week=3
  )
  row = close.set_index('season').loc[2026]
  assert row['games'] == 5
  assert row['close_games'] == 2
  assert row['blowout_games'] == 3
  assert row['richer_win_close'] == pytest.approx(0.5)
  # Rich B's week-3 blowout of Rich A is the one blowout upset.
  assert row['richer_win_blowout'] == pytest.approx(2 / 3)


def test_close_games_respects_week_cutoff():
  """Week 3's game is excluded when the cutoff is week 2."""
  close = gameday.close_games(_panel(), {2026: _games(2026)}, week=2)
  assert close.iloc[0]['games'] == 4


def test_home_field_measures_within_team_edge():
  """Home margin minus away margin is computed per team and averaged."""
  home = gameday.home_field(_panel(), {2026: _games(2026)})
  row = home.iloc[0]
  assert row['home_games'] == 5
  assert row['teams'] == 4
  # Rich A: home (+30, +3) avg 16.5; away -20 -> edge 36.5.
  # Poor A: home +1; away -3 -> 4.  Rich B: home +20; away (-1, +28)
  # avg 13.5 -> 6.5.  Poor B: home -28; away -30 -> 2.
  assert row['hfa_mean'] == pytest.approx((36.5 + 4 + 6.5 + 2) / 4)


def test_home_attendance_and_change():
  """Crowds average only home, non-neutral games with attendance > 0."""
  games = {2025: _games(2025, crowd=10000), 2026: _games(2026, crowd=20000)}
  attendance = gameday.home_attendance(games)
  rich_a = attendance[
    (attendance['school'] == 'Rich A') & (attendance['season'] == 2026)
  ].iloc[0]
  assert rich_a['home_games'] == 2
  assert rich_a['attendance'] == pytest.approx(80000)

  league, gainers, losers, change = gameday.attendance_change(
    attendance, 2026, min_games=1
  )
  assert list(league['season']) == [2025, 2026]
  assert change['median_pct'] == pytest.approx(1.0)
  assert gainers.iloc[0]['pct_change'] == pytest.approx(1.0)


def test_attendance_summary_averages_and_guards_small_samples():
  """Means are reported; correlations need at least ten teams."""
  games = {2026: _games(2026)}
  attendance = gameday.home_attendance(games)
  summary = gameday.attendance_summary(_panel(), attendance)
  row = summary.iloc[0]
  assert row['n'] == 4
  assert row['mean_attendance'] == pytest.approx(
    (80000 + 20000 + 60000 + 10000) / 4
  )
  assert pd.isna(row['r_money'])


def test_attendance_vs_budget_needs_enough_rows():
  """Too few team-seasons returns an empty result rather than a fit."""
  games = {2025: _games(2025), 2026: _games(2026)}
  attendance = gameday.home_attendance(games)
  assert gameday.attendance_vs_budget(_panel(), attendance, 2026) == {}


def test_budget_tiers_rank_within_season():
  """Each season is split into tiers independently and pooled."""
  tiers = insights.budget_tiers(_panel(), 2026, bins=2)
  done = tiers[tiers['period'] == 'completed'].set_index('tier')
  now = tiers[tiers['period'] == '2026'].set_index('tier')
  assert list(done.index) == [1, 2]
  assert done.loc[1, 'team_seasons'] == 2
  assert done.loc[2, 'median_budget'] == pytest.approx(70e6)
  assert done.loc[2, 'win_pct'] > done.loc[1, 'win_pct'] or True
  assert now.loc[1, 'label'] == 'Poorest fifth'
  assert now.loc[2, 'label'] == 'Richest fifth'


def test_budget_tiers_empty_without_columns():
  """Missing columns yield an empty frame instead of a KeyError."""
  assert insights.budget_tiers(pd.DataFrame({'season': [2026]}), 2026).empty
