"""Tests for chart generation.

These do not inspect pixels; they check that figures are actually
written, that reference programs get labelled, and that the axis
conventions the charts rely on are not silently broken.
"""

from __future__ import annotations

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use('Agg')

import matplotlib.pyplot as plt  # noqa: E402

from cfbmoney import config  # noqa: E402
from cfbmoney import plots  # noqa: E402


@pytest.fixture
def frame() -> pd.DataFrame:
  """Builds a small but realistic cross-section.

  Returns:
    pd.DataFrame: Synthetic single-season analysis table.
  """
  rng = np.random.default_rng(0)
  schools = [*config.REFERENCE_PROGRAMS, 'Tiny State', 'Middling Tech']
  spend = np.linspace(5e6, 1.2e8, len(schools))
  return pd.DataFrame(
    {
      'school': schools,
      'conference': ['Big Ten'] * len(schools),
      'football_expenses': spend,
      'football_revenue': spend * 1.4,
      'point_margin_per_game': np.log10(spend) * 6
      - 45
      + rng.normal(0, 1, len(schools)),
      'win_pct': np.linspace(0.1, 0.9, len(schools)),
      'season': 2026,
    }
  )


@pytest.fixture(autouse=True)
def _figures_dir(tmp_path, monkeypatch):
  """Redirects figure output into a temporary directory."""
  monkeypatch.setattr(config, 'FIGURES_DIR', tmp_path)
  return tmp_path


def test_scatter_writes_a_file(frame, _figures_dir):
  """The main scatter renders and returns its path."""
  path = plots.scatter_money_vs_performance(
    frame, 'football_expenses', 'point_margin_per_game', 2026
  )
  assert path is not None
  assert (
    _figures_dir / 'football_expenses_vs_point_margin_per_game_2026.png'
  ).exists()


def test_reference_programs_are_always_labelled(frame):
  """Named programs stay on the chart even if they are not outliers."""
  figure, axes = plt.subplots()
  labelled = plots._annotate_points(
    axes, frame, 'football_expenses', 'point_margin_per_game', scale_x=1e6
  )
  plt.close(figure)
  for school in config.REFERENCE_PROGRAMS:
    assert school in labelled


def test_explicit_annotation_list_is_respected(frame):
  """Passing schools explicitly overrides the automatic choice."""
  figure, axes = plt.subplots()
  labelled = plots._annotate_points(
    axes,
    frame,
    'football_expenses',
    'point_margin_per_game',
    annotate=['Tiny State'],
    scale_x=1e6,
  )
  plt.close(figure)
  assert labelled == ['Tiny State']


def test_annotation_survives_missing_values(frame):
  """Rows with NaN on either axis cannot crash the labeller."""
  frame = frame.copy()
  frame.loc[0, 'football_expenses'] = np.nan
  figure, axes = plt.subplots()
  labelled = plots._annotate_points(
    axes, frame, 'football_expenses', 'point_margin_per_game', scale_x=1e6
  )
  plt.close(figure)
  assert frame.loc[0, 'school'] not in labelled


def test_trend_helper_expects_log_inputs():
  """Guards the bug where raw percentages blew the axis up to 1e41.

  ``_trend_with_projection`` plots ``10 ** x`` because every money chart
  uses a log axis.  Any caller passing linear values must draw its own
  fit instead.
  """
  figure, axes = plt.subplots()
  log_x = np.log10(np.array([10.0, 20.0, 40.0, 80.0]))
  plots._trend_with_projection(
    axes, log_x, np.array([1.0, 2.0, 3.0, 4.0]), False
  )
  line = axes.get_lines()[0]
  # Plotted back in linear space, so within the original 10-80 range.
  assert line.get_xdata().max() <= 80.0 + 1e-9
  plt.close(figure)


def test_multi_season_scatter_covers_each_season(_figures_dir):
  """One panel per season is produced from a panel frame."""
  rows = []
  for season in (2023, 2024, 2025, 2026):
    for index, school in enumerate(config.REFERENCE_PROGRAMS):
      rows.append(
        {
          'school': school,
          'season': season,
          'conference': 'Big Ten',
          'football_expenses': 1e7 * (index + 1),
          'point_margin_per_game': index - 3.0,
        }
      )
  path = plots.multi_season_scatter(
    pd.DataFrame(rows), 'football_expenses', 'point_margin_per_game'
  )
  assert path is not None


def test_diaspora_chart_skips_when_money_is_missing(_figures_dir):
  """Schools with no post-move filing must not produce an empty chart."""
  diaspora = pd.DataFrame(
    {
      'school': ['A', 'B'],
      'role': ['joined', 'joined'],
      'football_revenue_pct_change': [np.nan, np.nan],
    }
  )
  assert plots.pac12_diaspora_chart(diaspora) is None


def test_realignment_scatter_needs_enough_points(_figures_dir):
  """Two schools are not a trend."""
  changes = pd.DataFrame(
    {
      'school': ['A', 'B'],
      'football_revenue_pct_change': [1.0, 2.0],
      'point_margin_per_game_change': [1.0, 2.0],
    }
  )
  assert plots.realignment_scatter(changes) is None
