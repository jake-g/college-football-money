"""Tests for frame building and the analysis maths."""

from __future__ import annotations

import numpy as np
import pandas as pd

from cfbmoney import analyze
from cfbmoney import build


def test_flatten_team_stats_picks_mapped_fields():
  payload = {
    'splits': {
      'categories': [
        {
          'name': 'passing',
          'stats': [
            {'name': 'completionPct', 'value': 62.7},
            {'name': 'ignored', 'value': 1},
          ],
        },
        {
          'name': 'scoring',
          'stats': [
            {'name': 'totalPointsPerGame', 'displayValue': '34.5'},
          ],
        },
      ]
    }
  }
  flat = build.flatten_team_stats(payload)
  assert flat['completion_pct'] == 62.7
  assert flat['points_per_game'] == 34.5
  assert 'ignored' not in flat


def _toy_season() -> pd.DataFrame:
  teams = pd.DataFrame(
    {
      'team_id': ['1', '2', '3'],
      'school': ['Rich U', 'Mid U', 'Poor U'],
      'conference': ['Big Ten', 'Big Ten', 'MAC'],
    }
  )
  games = pd.DataFrame(
    {
      'season': [2026] * 6,
      'game_id': ['a', 'a', 'b', 'b', 'c', 'c'],
      'school': ['Rich U', 'Mid U', 'Rich U', 'Poor U', 'Mid U', 'Poor U'],
      'opponent': ['Mid U', 'Rich U', 'Poor U', 'Rich U', 'Poor U', 'Mid U'],
      'completed': [True] * 6,
      'won': [True, False, True, False, True, False],
      'points_for': [30, 10, 40, 7, 21, 14],
      'points_against': [10, 30, 7, 40, 14, 21],
    }
  )
  return build.build_team_season_frame(teams, games, pd.DataFrame())


def test_team_season_records_and_margins():
  season = _toy_season()
  rich = season[season['school'] == 'Rich U'].iloc[0]
  assert rich['wins'] == 2
  assert rich['losses'] == 0
  assert rich['win_pct'] == 1.0
  assert rich['point_margin_per_game'] == (30 + 40 - 10 - 7) / 2


def test_dedupe_games_halves_the_long_frame():
  games = pd.DataFrame(
    {
      'game_id': ['a', 'a', 'b', 'b'],
      'school': ['X', 'Y', 'X', 'Z'],
    }
  )
  assert len(build.dedupe_games(games)) == 2


def test_correlation_table_finds_a_planted_relationship():
  rng = np.random.default_rng(7)
  revenue = np.linspace(5e6, 2e8, 60)
  win_pct = 0.2 + 0.3 * np.log10(revenue / 5e6) + rng.normal(0, 0.02, 60)
  frame = pd.DataFrame(
    {
      'school': [f'Team {i}' for i in range(60)],
      'conference': ['SEC'] * 30 + ['MAC'] * 30,
      'football_revenue': revenue,
      'win_pct': win_pct,
    }
  )
  table = analyze.correlation_table(
    frame,
    money_metrics=['football_revenue'],
    performance_metrics=['win_pct'],
  )
  row = table.iloc[0]
  assert row['n'] == 60
  assert row['pearson_r'] > 0.9
  assert row['pearson_p'] < 0.001


def test_fit_ols_returns_residuals_summing_to_zero():
  rng = np.random.default_rng(11)
  revenue = np.linspace(5e6, 2e8, 40)
  frame = pd.DataFrame(
    {
      'school': [f'Team {i}' for i in range(40)],
      'conference': ['SEC'] * 20 + ['MAC'] * 20,
      'football_revenue': revenue,
      'win_pct': 0.5 + rng.normal(0, 0.1, 40),
    }
  )
  model = analyze.fit_ols(frame)
  assert model['n'] == 40
  assert abs(model['residuals']['residual'].sum()) < 1e-9
  assert set(model['coefficients']['term']) >= {
    'intercept',
    'log10(football_revenue)',
  }


def _money_frame() -> pd.DataFrame:
  """Builds a frame where spending predicts margin and revenue tracks it.

  Returns:
    pd.DataFrame: Synthetic analysis table.
  """
  rng = np.random.default_rng(7)
  spend = np.linspace(5e6, 1.2e8, 60)
  revenue = spend * 1.5 + rng.normal(0, 1e6, 60)
  margin = np.log10(spend) * 8 - 60 + rng.normal(0, 1.5, 60)
  return pd.DataFrame(
    {
      'school': [f'School {i}' for i in range(60)],
      'conference': ['SEC', 'Big Ten', 'MAC'] * 20,
      'football_expenses': spend,
      'football_revenue': revenue,
      'point_margin_per_game': margin,
      'win_pct': np.clip((margin + 30) / 60, 0, 1),
    }
  )


def test_revenue_vs_spending_ranks_both_directions():
  """Both money-in and money-out metrics are compared side by side."""
  comparison = analyze.revenue_vs_spending(_money_frame())
  assert not comparison.empty
  assert set(comparison['money_flow']) == {'in', 'out'}


def test_collinearity_detects_that_revenue_tracks_spending():
  """Revenue and spending are near-duplicates, which the report says."""
  overlap = analyze.collinearity(_money_frame())
  assert overlap is not None
  assert overlap > 0.9


def test_spending_efficiency_flags_over_and_under_performers():
  """Residual ranking returns both tails, centred on zero."""
  frame = _money_frame()
  model = analyze.fit_ols(
    frame, outcome='point_margin_per_game', predictor='football_expenses'
  )
  residuals = model['residuals']
  assert len(residuals) == len(frame)
  assert abs(residuals['residual'].sum()) < 1e-6
  assert residuals['residual'].iloc[0] > 0


def test_conference_summary_groups_every_conference():
  """One row per conference, with no team lost along the way."""
  frame = _money_frame()
  summary = analyze.conference_summary(frame)
  assert len(summary) == frame['conference'].nunique()
  assert summary['teams'].sum() == len(frame)


def test_correlation_table_is_sorted_by_strength():
  """The strongest relationship must come first for the report."""
  table = analyze.correlation_table(_money_frame())
  strengths = table['pearson_r'].abs().tolist()
  assert strengths == sorted(strengths, reverse=True)
