"""Tests for the travel and time-zone analysis."""

from __future__ import annotations

import pandas as pd
import pytest

from cfbmoney import travel


@pytest.fixture
def offsets() -> dict[str, int]:
  """Returns a west-coast, mountain and east-coast school.

  Returns:
    dict[str, int]: School to UTC offset.
  """
  return travel.school_offsets(
    pd.DataFrame(
      {
        'school': ['Coast West', 'Middle', 'Coast East', 'UTEP'],
        'state': ['CA', 'CO', 'NJ', 'TX'],
      }
    )
  )


def test_split_state_schools_are_overridden(offsets):
  """UTEP is in Texas but on Mountain time."""
  assert offsets['UTEP'] == -7
  assert travel.STATE_UTC_OFFSET['TX'] == -6


def test_eastward_travel_is_a_positive_shift(offsets):
  """A California team playing in New Jersey crosses three zones east."""
  games = pd.DataFrame(
    {
      'school': ['Coast West'],
      'opponent': ['Coast East'],
      'home_away': ['away'],
      'neutral_site': [False],
    }
  )
  annotated = travel.add_travel_columns(games, offsets)
  assert annotated.loc[0, 'tz_shift'] == 3


def test_home_games_have_no_shift(offsets):
  """Playing at home is a zero shift regardless of the opponent."""
  games = pd.DataFrame(
    {
      'school': ['Coast West'],
      'opponent': ['Coast East'],
      'home_away': ['home'],
      'neutral_site': [False],
    }
  )
  annotated = travel.add_travel_columns(games, offsets)
  assert annotated.loc[0, 'tz_shift'] == 0


def test_neutral_sites_are_excluded(offsets):
  """The feed cannot locate neutral games, so they are dropped."""
  games = pd.DataFrame(
    {
      'school': ['Coast West'],
      'opponent': ['Coast East'],
      'home_away': ['away'],
      'neutral_site': [True],
    }
  )
  annotated = travel.add_travel_columns(games, offsets)
  assert pd.isna(annotated.loc[0, 'tz_shift'])


def test_performance_by_shift_excludes_home_games_by_default(offsets):
  """Home games would otherwise dominate the same-zone bucket."""
  games = pd.DataFrame(
    {
      'season': [2024, 2024],
      'school': ['Coast West', 'Coast West'],
      'opponent': ['Coast East', 'Coast East'],
      'home_away': ['home', 'away'],
      'neutral_site': [False, False],
      'completed': [True, True],
      'points_for': [50.0, 10.0],
      'points_against': [0.0, 40.0],
      'won': [True, False],
    }
  )
  annotated = travel.add_travel_columns(games, offsets)
  away = travel.performance_by_shift(annotated)
  assert list(away['shift']) == [3]
  both = travel.performance_by_shift(annotated, away_only=False)
  assert set(both['shift']) == {0, 3}


def test_within_team_effect_compares_a_team_against_itself(offsets):
  """The penalty is the team's own long-trip margin minus its own rest."""
  games = pd.DataFrame(
    {
      'season': [2024, 2024],
      'school': ['Coast West', 'Coast West'],
      'opponent': ['Coast East', 'Middle'],
      'home_away': ['away', 'away'],
      'neutral_site': [False, False],
      'completed': [True, True],
      'points_for': [10.0, 30.0],
      'points_against': [40.0, 20.0],
      'won': [False, True],
    }
  )
  annotated = travel.add_travel_columns(games, offsets)
  effect = travel.within_team_travel_effect(annotated)
  # Long trip margin -30, other away margin +10, so the penalty is -40.
  assert effect['penalty'] == pytest.approx(-40.0)
  assert effect['teams'] == 1.0


def test_travel_burden_counts_long_trips(offsets):
  """Long eastward trips are counted per school-season."""
  games = pd.DataFrame(
    {
      'season': [2024, 2024],
      'school': ['Coast West', 'Coast West'],
      'opponent': ['Coast East', 'Middle'],
      'home_away': ['away', 'away'],
      'neutral_site': [False, False],
    }
  )
  annotated = travel.add_travel_columns(games, offsets)
  burden = travel.travel_burden(annotated)
  assert burden.loc[0, 'long_eastward_trips'] == 1
  assert burden.loc[0, 'max_tz_shift'] == 3


def test_unknown_states_are_reported_not_guessed():
  """A state with no mapping is skipped rather than defaulted."""
  offsets = travel.school_offsets(
    pd.DataFrame({'school': ['Elsewhere'], 'state': ['ZZ']})
  )
  assert 'Elsewhere' not in offsets
