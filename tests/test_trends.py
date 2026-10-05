"""Tests for the in-season same-week trend analysis."""

from __future__ import annotations

import pandas as pd
import pytest

from cfbmoney import trends


def _panel() -> pd.DataFrame:
  """Two seasons, four FBS teams, two per conference."""
  rows = []
  for season in (2025, 2026):
    for school, conf, money, prior in (
      ('Rich A', 'A', 80e6, 10.0),
      ('Poor A', 'A', 20e6, -10.0),
      ('Rich B', 'B', 60e6, 5.0),
      ('Poor B', 'B', 10e6, -5.0),
    ):
      rows.append(
        {
          'season': season,
          'school': school,
          'conference': conf,
          'football_expenses': money,
          'point_margin_per_game': prior,
        }
      )
  return pd.DataFrame(rows)


def _game(season, week, home, away, home_pts, away_pts, conf):
  """Returns the two long rows for one game."""
  base = {
    'season': season,
    'week': week,
    'completed': True,
    'conference_game': False,
  }
  return [
    {
      **base,
      'school': home,
      'conference': conf[home],
      'opponent': away,
      'points_for': home_pts,
      'points_against': away_pts,
    },
    {
      **base,
      'school': away,
      'conference': conf[away],
      'opponent': home,
      'points_for': away_pts,
      'points_against': home_pts,
    },
  ]


CONF = {'Rich A': 'A', 'Poor A': 'A', 'Rich B': 'B', 'Poor B': 'B'}


def _games(season: int, upset: bool) -> pd.DataFrame:
  """Week 1 non-conference, week 2 conference; optional upset."""
  rows = []
  rows += _game(season, 1, 'Rich A', 'Poor B', 40, 10, CONF)
  if upset:
    rows += _game(season, 1, 'Rich B', 'Poor A', 10, 20, CONF)
  else:
    rows += _game(season, 1, 'Rich B', 'Poor A', 30, 20, CONF)
  rows += _game(season, 2, 'Rich A', 'Poor A', 35, 14, CONF)
  rows += _game(season, 2, 'Rich B', 'Poor B', 21, 17, CONF)
  return pd.DataFrame(rows)


def test_upsets_count_poorer_side_wins_only():
  """Only wins by a team with half the budget or less are upsets."""
  games = {2025: _games(2025, upset=True), 2026: _games(2026, upset=False)}
  summary, details = trends.upsets(_panel(), games, week=2)
  by_season = summary.set_index('season')
  # Mismatches: Rich A-Poor B (8x), Rich B-Poor A (3x), Rich A-Poor A (4x),
  # Rich B-Poor B (6x).
  assert by_season.loc[2025, 'mismatches'] == 4
  assert by_season.loc[2025, 'upsets'] == 1
  assert by_season.loc[2026, 'upsets'] == 0
  assert details.iloc[0]['winner'] == 'Poor A'
  assert details.iloc[0]['ratio'] == pytest.approx(3.0)


def test_upsets_respect_the_week_cutoff():
  """Games after the cutoff week are ignored."""
  games = {2025: _games(2025, upset=False)}
  summary, _ = trends.upsets(_panel(), games, week=1)
  assert summary.iloc[0]['mismatches'] == 2


def test_margin_to_date_excludes_later_weeks():
  """Margin to date averages only games through the cutoff."""
  frame = trends.margin_to_date({2025: _games(2025, upset=False)}, week=1)
  rich_a = frame[frame['school'] == 'Rich A'].iloc[0]
  assert rich_a['fbs_margin'] == pytest.approx(30.0)
  assert rich_a['fbs_games'] == 1


def test_same_week_comparison_and_projection_inputs():
  """Each season is read at the same week, with finals for past years."""
  weekly = pd.DataFrame(
    {
      'season': [2025, 2025, 2025, 2026, 2026],
      'week': [1, 2, 3, 1, 2],
      'r_margin': [0.4, 0.6, 0.45, 0.5, 0.55],
      'conf_share': [0.1, 0.3, 0.6, 0.1, 0.3],
      'richer_win_conf': [0.5, 0.6, 0.62, 0.7, 0.65],
      'conf_games': [2, 10, 30, 3, 12],
    }
  )
  table = trends.same_week_comparison(weekly, 2026, 2).set_index('season')
  assert table.loc[2025, 'r_at_week'] == pytest.approx(0.6)
  assert table.loc[2025, 'r_final'] == pytest.approx(0.45)
  assert pd.isna(table.loc[2026, 'r_final'])


def test_upset_rate_test_flags_large_drops():
  """A big drop against a large pooled baseline is significant."""
  summary = pd.DataFrame(
    {
      'season': [2024, 2025, 2026],
      'mismatches': [100, 100, 100],
      'upsets': [15, 15, 2],
      'upset_rate': [0.15, 0.15, 0.02],
    }
  )
  result = trends.upset_rate_test(summary, 2026)
  assert result['rate'] == pytest.approx(0.02)
  assert result['past_rate'] == pytest.approx(0.15)
  assert result['p'] < 0.01
