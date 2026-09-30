"""Tests for the beyond-the-budget team-quality analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from cfbmoney import drivers


def _panel(seasons: tuple[int, ...] = (2023, 2024, 2025, 2026)) -> pd.DataFrame:
  """Builds a panel where quality persists and money adds a little."""
  rng = np.random.default_rng(0)
  schools = [f'School {i}' for i in range(40)]
  skill = dict(zip(schools, rng.normal(0, 8, len(schools)), strict=True))
  budget = dict(
    zip(schools, rng.uniform(10e6, 90e6, len(schools)), strict=True)
  )
  rows = []
  for season in seasons:
    for school in schools:
      money = budget[school] * (1 + rng.normal(0, 0.05))
      margin = skill[school] + 10 * np.log10(money / 30e6) + rng.normal(0, 2)
      rows.append(
        {
          'school': school,
          'conference': 'A' if school < 'School 2' else 'B',
          'season': season,
          'football_expenses': money,
          'point_margin_per_game': margin,
          'passer_rating': 130 + 2 * margin + rng.normal(0, 3),
          'opponent_win_pct': 0.4 + money / 1e9,
        }
      )
  return pd.DataFrame(rows)


def test_prior_margin_is_last_seasons_value():
  """Prior margin lines up with the same school one season earlier."""
  panel = _panel((2024, 2025))
  merged = drivers.add_prior_margin(panel)
  row = merged[(merged['school'] == 'School 3') & (merged['season'] == 2025)]
  expected = panel[(panel['school'] == 'School 3') & (panel['season'] == 2024)][
    'point_margin_per_game'
  ]
  assert row['prior_margin'].iloc[0] == pytest.approx(expected.iloc[0])
  assert merged[merged['season'] == 2024]['prior_margin'].isna().all()


def test_momentum_vs_money_pools_completed_seasons_only():
  """The pooled fit excludes the in-progress season and adds R²."""
  table, pooled = drivers.momentum_vs_money(_panel(), 2026)
  assert list(table['season']) == [2024, 2025, 2026]
  assert pooled['last_season'] == 2025
  assert pooled['r2_both'] >= max(pooled['r2_prior'], pooled['r2_money'])
  assert pooled['t_prior'] > 2


def test_residual_persistence_finds_repeat_overperformers():
  """Persistent skill shows up as a positive year-over-year residual r."""
  residuals = drivers.budget_residuals(_panel())
  lag, over, under = drivers.residual_persistence(residuals, 2026, top_n=3)
  assert (lag['r'] > 0.5).all()
  assert len(over) == 3 and len(under) == 3
  assert over['mean_residual'].min() > under['mean_residual'].max()
  assert {'residual_2023', 'residual_2025'} <= set(over.columns)


def test_box_score_markers_sorted_by_strength():
  """Only available stats are ranked, strongest first."""
  markers = drivers.box_score_markers(_panel(), 2026)
  assert list(markers['stat']) == ['passer_rating']
  assert markers.iloc[0]['r_margin'] > 0.9


def test_schedule_strength_and_budget_change():
  """Richer teams face tougher schedules; budget noise gives no signal."""
  panel = _panel()
  assert drivers.schedule_strength(panel, 2026)['r'] > 0.9
  change = drivers.budget_change_effect(panel, 2026)
  assert change['first_season'] == 2023
  assert change['last_season'] == 2025
  assert abs(change['median_change_pct']) < 10
  assert abs(change['r']) < 0.5


def test_empty_inputs_return_empty():
  """Missing columns degrade to empty results rather than raising."""
  empty = pd.DataFrame({'school': [], 'season': []})
  assert drivers.box_score_markers(empty, 2026).empty
  assert drivers.budget_residuals(empty).empty
  assert drivers.schedule_strength(empty, 2026) == {}
  assert drivers.budget_change_effect(empty, 2026) == {}
