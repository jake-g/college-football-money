"""Tests for school-name normalisation.

Run with::

    PYTHONPATH=src python -m pytest tests -q
"""

from __future__ import annotations

from cfbmoney import names


def test_normalize_strips_generic_words():
  assert names.normalize_school('Ohio State University-Main Campus') == (
    'ohio state'
  )
  assert names.normalize_school('The University of Alabama') == 'alabama'
  assert names.normalize_school('University of Notre Dame') == 'notre dame'


def test_normalize_handles_ampersands_and_accents():
  assert names.normalize_school('Texas A & M University-College Station') == (
    'texas a m college station'
  )
  assert names.normalize_school('Hawai\u2018i') == 'hawaii'


def test_alias_resolution_for_awkward_schools():
  lookup = names.build_lookup(['Ole Miss', 'USC', 'Pitt', 'NC State'])
  assert names.resolve('University of Mississippi', lookup) == 'Ole Miss'
  assert names.resolve('University of Southern California', lookup) == 'USC'
  assert (
    names.resolve('University of Pittsburgh-Pittsburgh Campus', lookup)
    == 'Pitt'
  )
  assert (
    names.resolve('North Carolina State University at Raleigh', lookup)
    == 'NC State'
  )


def test_similar_schools_never_collide():
  """Georgia Tech must not absorb Georgia's budget, and so on."""
  lookup = names.build_lookup(
    [
      'Georgia',
      'Georgia Tech',
      'Virginia',
      'Virginia Tech',
      'Miami',
      'Miami (OH)',
      'California',
      'Fresno State',
      'Louisiana',
      'UL Monroe',
    ]
  )
  pairs = {
    'University of Georgia': 'Georgia',
    'Georgia Institute of Technology-Main Campus': 'Georgia Tech',
    'University of Virginia-Main Campus': 'Virginia',
    'Virginia Polytechnic Institute and State University': 'Virginia Tech',
    'University of Miami': 'Miami',
    'Miami University-Oxford': 'Miami (OH)',
    'University of California-Berkeley': 'California',
    'California State University-Fresno': 'Fresno State',
    'University of Louisiana at Lafayette': 'Louisiana',
    'University of Louisiana at Monroe': 'UL Monroe',
  }
  for official, espn_name in pairs.items():
    assert names.resolve(official, lookup) == espn_name, official


def test_identity_resolution():
  lookup = names.build_lookup(['Oregon', 'Michigan'])
  assert names.resolve('University of Oregon', lookup) == 'Oregon'
  assert names.resolve('Michigan', lookup) == 'Michigan'


def test_unknown_school_returns_none():
  lookup = names.build_lookup(['Oregon'])
  assert names.resolve('Hogwarts School of Witchcraft', lookup) is None
  assert names.resolve('', lookup) is None
  assert names.resolve(None, lookup) is None


def test_service_academies_are_flagged_exempt():
  assert set(names.EADA_EXEMPT) == {'Air Force', 'Army', 'Navy'}
