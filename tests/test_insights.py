"""Tests for the between-league / within-league insights."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from cfbmoney import build
from cfbmoney import insights


def _games() -> pd.DataFrame:
  """Builds a tiny long-format schedule with every game type.

  Returns:
    pd.DataFrame: Team-game rows for one season.
  """
  rows = [
    # Conference game: Rich A beats Poor A (both SEC).
    ('Rich A', 'SEC', 'Poor A', 30, 10),
    ('Poor A', 'SEC', 'Rich A', 10, 30),
    # Non-conference FBS: Rich A beats Mid B (MAC).
    ('Rich A', 'SEC', 'Mid B', 40, 7),
    ('Mid B', 'MAC', 'Rich A', 7, 40),
    # Conference game in the MAC: the poorer team wins.
    ('Mid B', 'MAC', 'Mid C', 14, 21),
    ('Mid C', 'MAC', 'Mid B', 21, 14),
    # FCS opponent never appears as a school.
    ('Poor A', 'SEC', 'Tiny FCS', 45, 3),
  ]
  frame = pd.DataFrame(
    rows,
    columns=[
      'school',
      'conference',
      'opponent',
      'points_for',
      'points_against',
    ],
  )
  frame['season'] = 2025
  frame['completed'] = True
  frame['won'] = frame['points_for'] > frame['points_against']
  return frame


def _panel() -> pd.DataFrame:
  """Builds the matching money table.

  Returns:
    pd.DataFrame: One row per school.
  """
  return pd.DataFrame(
    {
      'season': 2025,
      'school': ['Rich A', 'Poor A', 'Mid B', 'Mid C'],
      'conference': ['SEC', 'SEC', 'MAC', 'MAC'],
      'football_expenses': [9e7, 4e7, 1.5e7, 1.0e7],
      'point_margin_per_game': [26.5, 11.0, -20.0, 7.0],
    }
  )


def test_tag_conference_games_classifies_every_game_type():
  """Conference, non-conference FBS and FCS games are told apart."""
  tagged = build.tag_conference_games(_games())
  kinds = dict(
    zip(
      zip(tagged['school'], tagged['opponent'], strict=True),
      tagged['game_type'],
      strict=True,
    )
  )
  assert kinds[('Rich A', 'Poor A')] == 'conference'
  assert kinds[('Rich A', 'Mid B')] == 'nonconf_fbs'
  assert kinds[('Poor A', 'Tiny FCS')] == 'nonconf_fcs'
  assert tagged['conference_game'].sum() == 4


def test_independents_never_play_conference_games():
  """Two independents meeting is not a conference game."""
  games = pd.DataFrame(
    {
      'school': ['Notre Dame', 'UConn'],
      'opponent': ['UConn', 'Notre Dame'],
      'conference': ['FBS Independents'] * 2,
    }
  )
  tagged = build.tag_conference_games(games)
  assert not tagged['conference_game'].any()


def test_relative_spend_is_ratio_to_conference_median():
  """Spend is expressed as a multiple of the league median."""
  out = insights.add_relative_spend(_panel())
  sec = out[out['conference'] == 'SEC'].set_index('school')
  assert np.isclose(sec.loc['Rich A', 'relative_spend'], 9e7 / 6.5e7)


def test_schedule_split_counts_richer_team_wins():
  """The richer side won the SEC game and lost the MAC one."""
  split = insights.schedule_split(_panel(), {2025: _games()})
  row = split.iloc[0]
  assert row['conference_games'] == 2
  assert row['nonconf_fbs_games'] == 1
  assert row['conference_richer_win'] == 0.5
  assert row['nonconf_fbs_richer_win'] == 1.0
  assert row['fcs_games'] == 1


def test_spending_decomposition_flags_redundant_lines():
  """A line that is just a rescaled budget adds no signal."""
  rng = np.random.default_rng(1)
  budget = 10 ** rng.uniform(7, 8.2, 80)
  frame = pd.DataFrame(
    {
      'football_expenses': budget,
      'mens_coaching_payroll': budget * 0.3 * rng.uniform(0.95, 1.05, 80),
      'point_margin_per_game': np.log10(budget) * 10
      - 75
      + rng.normal(0, 3, 80),
    }
  )
  table = insights.spending_decomposition(
    frame, components=['mens_coaching_payroll']
  )
  row = table.iloc[0]
  assert row['corr_with_budget'] > 0.95
  assert abs(row['added_t']) < 2.5


def test_relative_spend_by_season_normalises_within_each_season():
  """Each season gets its own league medians and correlation row."""
  rows = []
  for season in (2024, 2025):
    for conf, base in (('A', 10e6), ('B', 40e6)):
      for i in range(8):
        rows.append(
          {
            'season': season,
            'school': f'{conf}{i}',
            'conference': conf,
            'football_expenses': base * (1 + 0.1 * i),
            'point_margin_per_game': float(i),
          }
        )
  panel = insights.add_relative_spend(pd.DataFrame(rows))
  first = panel[(panel['season'] == 2024) & (panel['conference'] == 'A')]
  assert first['relative_spend'].median() == pytest.approx(1.0)
  summary = insights.relative_spend_by_season(panel)
  assert list(summary['season']) == [2024, 2025]
  assert (summary['r_within'] > 0.9).all()
