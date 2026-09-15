"""Tests for the conference realignment analysis."""

from __future__ import annotations

import pandas as pd

from cfbmoney import realignment


def _panel() -> pd.DataFrame:
  """Builds a small panel covering a mover and a stayer.

  ``mover`` leaves the Pac-12 for the Big Ten in 2024 while ``stayer``
  remains.  Money is attached the way the real pipeline attaches it: one
  filing per report year, repeated across the seasons it is joined to.

  Returns:
    pd.DataFrame: Synthetic panel.
  """
  rows = []
  for season, report_year in ((2023, 2024), (2024, 2025), (2025, 2025)):
    rows.append(
      {
        'school': 'Mover',
        'season': season,
        'conference': 'Pac-12' if season == 2023 else 'Big Ten',
        'money_report_year': report_year,
        'football_revenue': 100.0 if report_year == 2024 else 150.0,
        'football_expenses': 80.0 if report_year == 2024 else 90.0,
        'point_margin_per_game': 0.0 if season == 2023 else 10.0,
        'win_pct': 0.5,
      }
    )
    rows.append(
      {
        'school': 'Stayer',
        'season': season,
        'conference': 'Pac-12',
        'money_report_year': report_year,
        'football_revenue': 100.0 if report_year == 2024 else 50.0,
        'football_expenses': 80.0 if report_year == 2024 else 40.0,
        'point_margin_per_game': 0.0,
        'win_pct': 0.5,
      }
    )
  return pd.DataFrame(rows)


def test_detect_moves_finds_only_the_mover():
  """Only schools whose conference actually changed are returned."""
  moves = realignment.detect_moves(_panel())
  assert list(moves['school']) == ['Mover']
  assert moves.iloc[0]['move_season'] == 2024
  assert moves.iloc[0]['from_conference'] == 'Pac-12'
  assert moves.iloc[0]['to_conference'] == 'Big Ten'


def test_pac12_was_a_power_conference_only_through_2023():
  """Tier membership is season aware."""
  assert realignment.conference_tier('Pac-12', 2023) == 'power'
  assert realignment.conference_tier('Pac-12', 2026) == 'group of five'
  assert realignment.conference_tier('SEC', 2026) == 'power'


def test_repeated_filings_are_not_double_counted():
  """A filing joined to two seasons is one money observation."""
  money = realignment.money_observations(_panel())
  mover = money[money['school'] == 'Mover']
  # Report years 2024 and 2025 describe seasons 2023 and 2024.
  assert sorted(mover['money_season']) == [2023, 2024]


def test_before_after_uses_money_season_not_football_season():
  """Money deltas are computed from distinct filings only."""
  panel = _panel()
  changes = realignment.before_after(panel, realignment.detect_moves(panel))
  row = changes.iloc[0]
  assert row['football_revenue_before'] == 100.0
  assert row['football_revenue_after'] == 150.0
  assert row['football_revenue_pct_change'] == 50.0


def test_diaspora_splits_leavers_from_stayers():
  """The school that stayed is kept as a control group row."""
  panel = _panel()
  result = realignment.diaspora(
    panel, realignment.detect_moves(panel), baseline_season=2023
  )
  roles = dict(zip(result['school'], result['role'], strict=True))
  assert roles == {'Mover': 'left', 'Stayer': 'stayed'}
  stayer = result[result['school'] == 'Stayer'].iloc[0]
  # The stayer lost revenue without moving.
  assert stayer['football_revenue_pct_change'] == -50.0


def test_summaries_ignore_the_textual_tier_change_column():
  """``tier_change`` holds text and must not be aggregated."""
  panel = _panel()
  changes = realignment.before_after(panel, realignment.detect_moves(panel))
  tiers = realignment.tier_summary(changes)
  assert not tiers.empty
  by_move = realignment.summarize_by_move(changes)
  assert not by_move.empty
