"""Tests for the markdown report renderer."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from cfbmoney import report


@pytest.fixture
def merged() -> pd.DataFrame:
  """Builds a minimal analysis table.

  Returns:
    pd.DataFrame: Synthetic merged frame.
  """
  return pd.DataFrame(
    {
      'school': ['Rich U', 'Poor U'],
      'conference': ['SEC', 'MAC'],
      'football_revenue': [1.5e8, 1.2e7],
      'football_expenses': [9.0e7, 9.0e6],
      'dept_total_revenue': [2.5e8, 4.0e7],
      'wins': [3, 0],
      'losses': [0, 3],
      'win_pct': [1.0, 0.0],
      'points_per_game': [45.0, 12.0],
      'point_margin_per_game': [25.0, -20.0],
      'games_played': [3, 3],
      'money_report_year': [2025, 2025],
    }
  )


def test_report_has_a_title_and_sample_size_warning(merged):
  """An in-progress season must be flagged loudly at the top."""
  text = report.build_report(
    merged, pd.DataFrame(), None, pd.DataFrame(), 2026, 3
  )
  assert text.startswith('# Money vs winning')
  assert '[!WARNING]' in text
  assert 'week 3' in text


def test_report_notes_the_finance_lag(merged):
  """Readers must be told the money is two years older than the games."""
  text = report.build_report(
    merged, pd.DataFrame(), None, pd.DataFrame(), 2026, 3
  )
  assert '[!NOTE]' in text
  assert '2025 filings' in text or 'report year' in text.lower()


def test_realignment_section_marks_unfiled_money():
  """Movers without a post-move filing say so instead of showing 0%."""
  changes = pd.DataFrame(
    {
      'school': ['Mover', 'Recent Mover'],
      'move': ['Pac-12 to Big Ten', 'Mountain West to Pac-12'],
      'move_season': [2024, 2026],
      'tier_change': ['lateral', 'lateral'],
      'football_revenue_pct_change': [12.5, np.nan],
      'point_margin_per_game_change': [3.0, -1.0],
    }
  )
  lines = report._realignment_section(changes, pd.DataFrame())
  text = '\n'.join(lines)
  assert '+12.5%' in text
  assert 'not yet filed' in text
  assert '2 schools changed conference' in text


def test_realignment_section_contrasts_leavers_and_stayers():
  """The headline Pac-12 comparison is spelled out for the reader."""
  changes = pd.DataFrame(
    {
      'school': ['Leaver', 'Stayer'],
      'move': ['Pac-12 to Big Ten', 'Pac-12 (stayed)'],
      'move_season': [2024, 2024],
      'tier_change': ['lateral', 'stranded'],
      'football_revenue_pct_change': [20.0, -30.0],
      'point_margin_per_game_change': [1.0, -2.0],
    }
  )
  diaspora = changes.copy()
  diaspora['role'] = ['left', 'stayed']
  diaspora['football_revenue_before'] = [1.0e8, 5.0e7]
  diaspora['football_revenue_after'] = [1.2e8, 3.5e7]
  text = '\n'.join(report._realignment_section(changes, diaspora))
  assert '+20.0%' in text
  assert '-30.0%' in text
  assert 'stayed behind' in text


def test_empty_realignment_degrades_gracefully():
  """No detected moves is a valid state, not a crash."""
  lines = report._realignment_section(pd.DataFrame(), pd.DataFrame())
  assert 'No conference changes' in '\n'.join(lines)


def test_figures_are_embedded_with_relative_paths(merged):
  """GitHub needs paths relative to the markdown file, not absolute."""
  text = report.build_report(
    merged,
    pd.DataFrame(),
    None,
    pd.DataFrame(),
    2026,
    3,
    figures=['/abs/path/reports/figures/chart.png'],
    figure_prefix='figures/',
  )
  assert '](figures/chart.png)' in text
  assert '/abs/path' not in text


def test_markdown_tables_are_well_formed(merged):
  """Every table row must have the same column count as its header."""
  text = report.build_report(
    merged, pd.DataFrame(), None, pd.DataFrame(), 2026, 3
  )
  header_columns = None
  for line in text.splitlines():
    stripped = line.strip()
    if not stripped.startswith('|'):
      header_columns = None
      continue
    count = stripped.count('|')
    if header_columns is None:
      header_columns = count
    else:
      assert count == header_columns, f'ragged table row: {stripped}'


def test_nil_revshare_section_renders_cap_and_disclaimer(merged):
  """NIL section must document the House cap and undisclosed per-school splits."""
  lines = report._nil_revshare_section(merged, pd.DataFrame())
  text = '\n'.join(lines)
  assert 'House v. NCAA' in text
  assert 'Revenue-share cap' in text
  assert 'not disclosed' in text


def test_realignment_section_includes_financial_mechanics():
  """Realignment section includes settlement, media deals, and travel costs."""
  changes = pd.DataFrame(
    {
      'school': ['Oregon'],
      'move': ['Pac-12 to Big Ten'],
      'move_season': [2024],
      'football_revenue_pct_change': [9.5],
      'point_margin_per_game_change': [-13.2],
    }
  )
  diaspora = pd.DataFrame(
    {
      'school': ['Oregon', 'Washington State'],
      'role': ['left', 'stayed'],
      'football_revenue_before': [1.09e8, 5.7e7],
      'football_revenue_after': [1.19e8, 3.8e7],
      'football_revenue_pct_change': [9.5, -31.9],
      'point_margin_per_game_change': [-13.2, -7.1],
    }
  )
  lines = report._realignment_section(changes, diaspora)
  text = '\n'.join(lines)
  assert 'WSU/OSU Settlement' in text
  assert '$65M Withheld' in text
  assert 'B1G Media Deal' in text
  assert 'Increased Travel Costs' in text
  assert 'research_notes_2026.md' not in text


def test_critique_section_includes_evaluations():
  """Critique section includes what held up and what looks shaky."""
  lines = report._critique_section(pd.DataFrame(), None)
  text = '\n'.join(lines)
  assert 'What held up' in text
  assert 'What is looking shaky' in text
  assert 'Program infrastructure over star coach' in text
