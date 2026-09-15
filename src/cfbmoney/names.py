"""School name normalisation and the ESPN <-> federal-filings crosswalk.

ESPN calls the school "Ole Miss"; the Department of Education calls it
"University of Mississippi"; ESPN says "Miami" for the Florida program
and "Miami (OH)" for the Ohio one, while EADA says "University of
Miami" and "Miami University-Oxford".  Everything in this project joins
on a canonical key produced by :func:`normalize_school`, with an
explicit override table for the cases plain normalisation gets wrong.

Fuzzy matching is deliberately *not* used.  An earlier version fell back
to progressive prefix trimming and happily merged Georgia Tech's budget
into Georgia, Virginia Tech's into Virginia and Miami (OH)'s into Miami.
Unmatched is better than silently wrong, so unknown names now return
``None`` and are reported.

Note: the three service academies (Air Force, Army, Navy) do not appear
in EADA at all.  They do not participate in Title IV federal student
aid, so the disclosure requirement does not reach them.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

# ESPN 'location' name -> exact institution name as it appears in the
# EADA filings.  Only schools that plain normalisation cannot match are
# listed; every name here was verified against the published data.
EADA_NAME_BY_ESPN: dict[str, str] = {
  'App State': 'Appalachian State University',
  'Arizona State': 'Arizona State University Campus Immersion',
  'BYU': 'Brigham Young University',
  'Bowling Green': 'Bowling Green State University-Main Campus',
  'California': 'University of California-Berkeley',
  'Charlotte': 'University of North Carolina at Charlotte',
  'Colorado': 'University of Colorado Boulder',
  'Colorado State': 'Colorado State University-Fort Collins',
  'Fresno State': 'California State University-Fresno',
  'Georgia Tech': 'Georgia Institute of Technology-Main Campus',
  "Hawai'i": 'University of Hawaii at Manoa',
  'Illinois': 'University of Illinois Urbana-Champaign',
  'Indiana': 'Indiana University-Bloomington',
  'Kent State': 'Kent State University at Kent',
  'LSU': ('Louisiana State University and Agricultural & Mechanical College'),
  'Louisiana': 'University of Louisiana at Lafayette',
  'Maryland': 'University of Maryland-College Park',
  'Massachusetts': 'University of Massachusetts-Amherst',
  'Miami': 'University of Miami',
  'Miami (OH)': 'Miami University-Oxford',
  'Michigan': 'University of Michigan-Ann Arbor',
  'Middle Tennessee': 'Middle Tennessee State University',
  'Minnesota': 'University of Minnesota-Twin Cities',
  'Missouri': 'University of Missouri-Columbia',
  'Missouri State': 'Missouri State University-Springfield',
  'NC State': 'North Carolina State University at Raleigh',
  'Nebraska': 'University of Nebraska-Lincoln',
  'Nevada': 'University of Nevada-Reno',
  'North Carolina': 'University of North Carolina at Chapel Hill',
  'North Dakota State': 'North Dakota State University-Main Campus',
  'Oklahoma': 'University of Oklahoma-Norman Campus',
  'Ole Miss': 'University of Mississippi',
  'Penn State': 'Pennsylvania State University-Main Campus',
  'Pitt': 'University of Pittsburgh-Pittsburgh Campus',
  'Pittsburgh': 'University of Pittsburgh-Pittsburgh Campus',
  'Rutgers': 'Rutgers University-New Brunswick',
  'SMU': 'Southern Methodist University',
  'Sacramento State': 'California State University-Sacramento',
  'Sam Houston': 'Sam Houston State University',
  'South Carolina': 'University of South Carolina-Columbia',
  'Southern Miss': 'University of Southern Mississippi',
  'TCU': 'Texas Christian University',
  'Tennessee': 'The University of Tennessee-Knoxville',
  'Texas': 'The University of Texas at Austin',
  'Texas A&M': 'Texas A&M University-College Station',
  'Tulane': 'Tulane University of Louisiana',
  'UAB': 'University of Alabama at Birmingham',
  'UCF': 'University of Central Florida',
  'UCLA': 'University of California-Los Angeles',
  'UConn': 'University of Connecticut',
  'UL Monroe': 'University of Louisiana at Monroe',
  'UNLV': 'University of Nevada-Las Vegas',
  'USC': 'University of Southern California',
  'UTEP': 'The University of Texas at El Paso',
  'UTSA': 'The University of Texas at San Antonio',
  'Virginia Tech': 'Virginia Polytechnic Institute and State University',
  'Washington': 'University of Washington-Seattle Campus',
  'Wisconsin': 'University of Wisconsin-Madison',
  'Alabama': 'The University of Alabama',
  'Akron': 'University of Akron Main Campus',
  'Buffalo': 'University at Buffalo',
  'Cincinnati': 'University of Cincinnati-Main Campus',
  'Ohio': 'Ohio University-Main Campus',
  'Ohio State': 'Ohio State University-Main Campus',
  'Virginia': 'University of Virginia-Main Campus',
  'Delaware': 'University of Delaware',
  'New Mexico': 'University of New Mexico-Main Campus',
  'New Mexico State': 'New Mexico State University-Main Campus',
  'Purdue': 'Purdue University-Main Campus',
  'Iowa State': 'Iowa State University',
  'Kansas State': (
    'Kansas State University of Agriculture and Applied Science'
  ),
}

# Schools that legitimately have no EADA record, with the reason.
EADA_EXEMPT = {
  'Air Force': 'service academy, not a Title IV participant',
  'Army': 'service academy, not a Title IV participant',
  'Navy': 'service academy, not a Title IV participant',
}

# Generic words removed before generating the canonical key.  Note that
# 'state', 'tech' and 'college' are meaningful in college football
# ("Boston College", "College Station") and are deliberately kept.
_STOPWORDS = frozenset(
  {
    'university',
    'universities',
    'the',
    'of',
    'at',
    'main',
    'campus',
    'system',
    'and',
  }
)

_PUNCTUATION = re.compile(r'[^a-z0-9 ]+')
_WHITESPACE = re.compile(r'\s+')


def normalize_school(name: str | None) -> str:
  """Reduces a school name to a canonical join key.

  The key is lowercase, ASCII, punctuation-free and stripped of generic
  words such as "University" and "Main Campus".

  Args:
    name: A school name from any source.

  Returns:
    The canonical key, or an empty string when ``name`` is falsy.
  """
  if not name:
    return ''
  text = unicodedata.normalize('NFKD', str(name))
  text = text.encode('ascii', 'ignore').decode('ascii').lower()
  text = text.replace('&', ' and ')
  text = text.replace('-', ' ')
  text = _PUNCTUATION.sub(' ', text)
  tokens = [t for t in text.split() if t and t not in _STOPWORDS]
  return _WHITESPACE.sub(' ', ' '.join(tokens)).strip()


def build_lookup(espn_schools: Iterable[str]) -> dict[str, str]:
  """Builds a canonical-key to ESPN-school lookup table.

  Two keys are registered for every team: the normalised form of its own
  ESPN name, and the normalised form of its official institution name
  from :data:`EADA_NAME_BY_ESPN` when one is listed.

  Args:
    espn_schools: ESPN ``location`` names for every team in scope.

  Returns:
    A mapping from canonical key to ESPN school name.
  """
  lookup: dict[str, str] = {}
  for school in espn_schools:
    official = EADA_NAME_BY_ESPN.get(school)
    if official:
      lookup[normalize_school(official)] = school
    lookup.setdefault(normalize_school(school), school)
  return lookup


def resolve(name: str | None, lookup: dict[str, str]) -> str | None:
  """Resolves a school name against a lookup built by :func:`build_lookup`.

  Args:
    name: The incoming school name from a finance file.
    lookup: Mapping produced by :func:`build_lookup`.

  Returns:
    The ESPN school name, or ``None`` when there is no exact match.
    No fuzzy fallback is attempted on purpose.
  """
  key = normalize_school(name)
  if not key:
    return None
  return lookup.get(key)


def to_espn_school(name: str | None) -> str | None:
  """Maps an official institution name onto its ESPN spelling.

  Args:
    name: An institution name as spelled in a finance source.

  Returns:
    The ESPN spelling when the pair is in :data:`EADA_NAME_BY_ESPN`,
    otherwise ``None``.
  """
  key = normalize_school(name)
  if not key:
    return None
  for espn_name, official in EADA_NAME_BY_ESPN.items():
    if normalize_school(official) == key:
      return espn_name
  return None
