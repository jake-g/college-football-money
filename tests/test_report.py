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
  """NIL section documents the House cap and undisclosed school splits."""
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


def test_key_findings_are_computed_from_inputs():
  """Findings quote the numbers they are given, not canned text."""
  split = pd.DataFrame(
    {
      'season': [2025, 2026],
      'nonconf_fbs_richer_win': [0.75, 0.8],
      'conference_richer_win': [0.6, 0.55],
    }
  )
  lines = report._key_findings(
    pd.DataFrame(),
    pd.DataFrame(),
    split,
    {'r_within': 0.31},
    None,
    None,
    None,
    2026,
  )
  text = '\n'.join(lines)
  assert '## Summary' in text
  assert '75.0%' in text
  assert '60.0%' in text
  assert '+0.31' in text


def test_key_findings_empty_without_inputs():
  """No inputs means no findings section rather than filler."""
  assert (
    report._key_findings(
      pd.DataFrame(), pd.DataFrame(), None, None, None, None, None, 2026
    )
    == []
  )


def test_correlation_matrix_has_one_row_per_metric():
  """The compact matrix collapses metric/outcome pairs into rows."""
  correlations = pd.DataFrame(
    {
      'money_metric': ['football_expenses'] * 2 + ['football_revenue'] * 2,
      'performance_metric': ['point_margin_per_game', 'win_pct'] * 2,
      'n': [100] * 4,
      'pearson_r': [0.6, 0.5, 0.55, 0.45],
      'pearson_p': [0.0001] * 4,
    }
  )
  text = '\n'.join(report._correlation_matrix(correlations))
  assert text.count('| Football expenses |') == 1
  assert text.count('| Football revenue |') == 1
  assert '+0.60***' in text


def test_figures_are_inlined_and_leftovers_kept(merged):
  """Known figures sit in their section; unknown ones are not dropped."""
  text = report.build_report(
    merged,
    pd.DataFrame(),
    None,
    pd.DataFrame(),
    2026,
    3,
    figures=['/x/revenue_vs_spending_2026.png', '/x/mystery.png'],
    figure_prefix='figures/',
    revenue_spending_overlap=0.9,
  )
  spending = text.index('## Spending versus revenue')
  assert text.index('revenue_vs_spending_2026.png') > spending
  assert '## Other figures' in text
  assert 'figures/mystery.png' in text


def test_report_is_organised_into_numbered_parts(merged):
  """Parts get a contents entry and sections are nested beneath them."""
  markers = pd.DataFrame(
    {
      'stat': ['passer_rating'],
      'label': ['Passer rating (offense)'],
      'n': [300],
      'r_margin': [0.7],
      'r_money': [0.3],
    }
  )
  text = report.build_report(
    merged,
    pd.DataFrame(),
    None,
    pd.DataFrame(),
    2026,
    3,
    revenue_spending_overlap=0.9,
    drivers={'markers': markers},
  )
  assert '## Contents' in text
  assert '(#2-what-separates-good-teams-from-bad)' in text
  assert '## 2. What separates good teams from bad' in text
  assert '### On-field markers of a good team' in text
  assert '**Quarterback play is the clearest on-field marker.**' in text
  assert text.index('## Summary') < text.index('## Contents')


def test_slug_matches_github_anchors():
  """Anchors drop punctuation and hyphenate spaces."""
  assert report._slug('1. Does money buy wins?') == '1-does-money-buy-wins'
  assert (
    report._slug('4. Roster economics: NIL and revenue sharing')
    == '4-roster-economics-nil-and-revenue-sharing'
  )
