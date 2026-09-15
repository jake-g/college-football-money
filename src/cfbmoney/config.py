"""Static configuration for the college football money-vs-wins project.

Holds filesystem layout, ESPN group identifiers and the set of leagues we
care about.  Nothing in here performs I/O.
"""

from __future__ import annotations

import os
import pathlib

# --- Filesystem layout -------------------------------------------------

PACKAGE_DIR = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
RAW_DIR = DATA_DIR / 'raw'
ESPN_CACHE_DIR = RAW_DIR / 'espn'
FINANCE_DIR = DATA_DIR / 'finance'
PROCESSED_DIR = DATA_DIR / 'processed'
REPORTS_DIR = PROJECT_ROOT / 'reports'
FIGURES_DIR = REPORTS_DIR / 'figures'

# --- Season ------------------------------------------------------------

# The season currently under study.  College football seasons are named
# for the calendar year in which they start.
DEFAULT_SEASON = 2026

# ESPN season types: 1 = preseason, 2 = regular season, 3 = postseason.
REGULAR_SEASON_TYPE = 2

# --- ESPN group (conference) identifiers -------------------------------

# Group 80 is the whole FBS (Football Bowl Subdivision) division.
FBS_GROUP_ID = 80

# ESPN conference group id -> human readable name.
CONFERENCE_NAMES: dict[int, str] = {
  1: 'ACC',
  4: 'Big 12',
  5: 'Big Ten',
  8: 'SEC',
  9: 'Pac-12',
  12: 'Conference USA',
  15: 'MAC',
  17: 'Mountain West',
  18: 'FBS Independents',
  37: 'Sun Belt',
  151: 'American',
}

# The "Power Four" autonomy conferences plus independents (which is where
# Notre Dame lives).  These are the programs the user cares most about.
POWER_GROUP_IDS: list[int] = [1, 4, 5, 8, 18]

# Everything in the FBS.  Used so that opponents of the headline programs
# are also captured.
FBS_GROUP_IDS: list[int] = sorted(CONFERENCE_NAMES)

# Conferences that receive autonomy-level media money.  Used as a control
# variable in the regressions.
POWER_CONFERENCES = frozenset({'ACC', 'Big 12', 'Big Ten', 'SEC'})

# Programs the user explicitly called out; they are always labelled in
# the scatter plots so there is a familiar reference point in every
# quadrant.  Values are ESPN 'location' names.
HEADLINE_PROGRAMS: list[str] = [
  'Alabama',
  'Colorado',
  'Georgia',
  'LSU',
  'Miami',
  'Michigan',
  'Notre Dame',
  'Ohio State',
  'Oregon',
  'Oregon State',
  'Penn State',
  'Texas',
  'USC',
  'Washington',
  'Washington State',
]

# Subset labelled on dense small-multiple panels, where the full
# headline list would overlap into an unreadable mess.  Spans the range
# of the story: perennial powers, Pac-12 schools that left for the Big
# Ten, and the two that were left behind when the league broke up.
REFERENCE_PROGRAMS: list[str] = [
  'Ohio State',
  'Alabama',
  'Georgia',
  'LSU',
  'Oregon',
  'Washington State',
  'Oregon State',
  'Texas',
  'Michigan',
]

# --- HTTP --------------------------------------------------------------

# ESPN's edge returns HTTP 403 for unrecognised User-Agent strings and
# for browser-spoofing ones (the TLS fingerprint gives it away), but it
# accepts the stock ``python-requests/x.y.z`` agent.  Leaving this empty
# keeps that default; set CFBMONEY_USER_AGENT to override.
USER_AGENT = os.environ.get('CFBMONEY_USER_AGENT', '')

# Seconds to sleep between uncached HTTP requests to be a good citizen.
REQUEST_DELAY_SECONDS = float(os.environ.get('CFBMONEY_DELAY', '0.3'))

# How long a cached ESPN response stays fresh, in hours.  Schedules and
# stats change during game weeks, so this is deliberately short.
CACHE_TTL_HOURS = float(os.environ.get('CFBMONEY_CACHE_TTL_HOURS', '6'))


def ensure_directories() -> None:
  """Creates every directory the pipeline writes to."""
  for directory in (
    RAW_DIR,
    ESPN_CACHE_DIR,
    FINANCE_DIR,
    PROCESSED_DIR,
    REPORTS_DIR,
    FIGURES_DIR,
  ):
    directory.mkdir(parents=True, exist_ok=True)
