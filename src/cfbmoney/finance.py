"""Loads the money side of the project and joins it to ESPN teams.

Three inputs are supported, all living in ``data/finance``:

``eada_football_<year>.csv``
    Federal EADA filings produced by
    :mod:`cfbmoney.sources.eada`.  This is the authoritative source.
``coach_pay_<season>.csv``
    Head coach total compensation, hand-compiled with per-row citations.
``nil_revshare_<season>.csv``
    House-settlement revenue sharing and NIL/roster payroll estimates.

Only the EADA file is required; the others are merged when present.
"""

from __future__ import annotations

import logging
import pathlib
from collections.abc import Iterable

import pandas as pd

from . import config
from . import names

logger = logging.getLogger(__name__)

# A season's finances are reported in the EADA file for the following
# academic year: the 2024 football season sits inside academic year
# 2024-25, which is EADA report year 2025.
SEASON_TO_REPORT_YEAR_LAG = 1

MONEY_COLUMNS = [
  # Money coming in.
  'football_revenue',
  'dept_total_revenue',
  # Money going out.
  'football_expenses',
  'football_spend_per_player',
  'football_nonoperating_spend',
  'football_operating_expenses',
  'football_opexp_per_participant',
  'mens_coaching_payroll',
  'avg_head_coach_salary_men',
  'avg_asst_coach_salary_men',
  'recruiting_expenses_men',
  'dept_total_expenses',
  # Context.
  'football_net',
  'football_participants',
  'football_head_coaches',
  'football_assistant_coaches',
  # Sourced outside EADA.
  'head_coach_pay',
  'head_coach_buyout',
  'revshare_cap',
  'football_allocation_est',
  'roster_payroll_est',
]


def _attach_espn_school(
  frame: pd.DataFrame,
  lookup: dict[str, str],
  column: str = 'school',
) -> pd.DataFrame:
  """Adds an ``espn_school`` column resolved from a name column.

  Args:
    frame: Any frame with a school name column.
    lookup: Mapping produced by :func:`cfbmoney.names.build_lookup`.
    column: Name of the column holding the school name.

  Returns:
    The frame with an added ``espn_school`` column (may contain nulls).
  """
  out = frame.copy()
  if 'espn_school' in out.columns:
    existing = out['espn_school'].replace('', pd.NA)
  else:
    existing = pd.Series(pd.NA, index=out.index, dtype='object')
  resolved = out[column].map(lambda v: names.resolve(v, lookup))
  out['espn_school'] = existing.fillna(pd.Series(resolved, index=out.index))
  return out


def available_eada_years() -> list[int]:
  """Returns the EADA report years present on disk, newest first."""
  years = []
  for path in config.FINANCE_DIR.glob('eada_football_*.csv'):
    stem = path.stem.rsplit('_', 1)[-1]
    if stem.isdigit():
      years.append(int(stem))
  return sorted(years, reverse=True)


def resolve_report_year(season: int, prefer: int | None = None) -> int:
  """Picks which EADA report year to pair with a football season.

  Args:
    season: Football season, e.g. 2026.
    prefer: Explicit report year override.

  Returns:
    The chosen report year.

  Raises:
    FileNotFoundError: If no EADA files have been downloaded.
  """
  years = available_eada_years()
  if not years:
    raise FileNotFoundError(
      'No EADA files in data/finance; run '
      '"python -m cfbmoney.sources.eada --fbs-only" first.'
    )
  if prefer is not None:
    if prefer not in years:
      raise FileNotFoundError(f'EADA report year {prefer} not downloaded')
    return prefer
  wanted = season + SEASON_TO_REPORT_YEAR_LAG
  if wanted in years:
    return wanted
  latest = years[0]
  logger.warning(
    'EADA report year %d is not published yet; falling back to %d '
    '(finances lag the %d season by %d year(s)).',
    wanted,
    latest,
    season,
    wanted - latest,
  )
  return latest


def load_eada(report_year: int) -> pd.DataFrame:
  """Loads one EADA report year from ``data/finance``.

  Args:
    report_year: EADA report year, e.g. 2025.

  Returns:
    The EADA frame.

  Raises:
    FileNotFoundError: If the file is missing.
  """
  path = config.FINANCE_DIR / f'eada_football_{report_year}.csv'
  if not path.exists():
    raise FileNotFoundError(f'{path} not found')
  return pd.read_csv(path)


def _load_optional(path: pathlib.Path) -> pd.DataFrame | None:
  """Reads a CSV if it exists, otherwise returns ``None``."""
  if not path.exists():
    logger.info('Optional finance file %s not present', path.name)
    return None
  frame = pd.read_csv(path)
  if frame.empty:
    return None
  return frame


def build_money_frame(
  espn_schools: Iterable[str],
  season: int = config.DEFAULT_SEASON,
  report_year: int | None = None,
) -> pd.DataFrame:
  """Assembles one money row per ESPN school.

  Args:
    espn_schools: ESPN ``location`` names for the teams in scope.
    season: Football season being analysed.
    report_year: Optional explicit EADA report year.

  Returns:
    A frame keyed by ``espn_school`` holding every available money
    metric, plus ``money_report_year`` and ``money_lag_years``.
  """
  schools = list(espn_schools)
  lookup = names.build_lookup(schools)
  chosen_year = resolve_report_year(season, report_year)

  eada = _attach_espn_school(load_eada(chosen_year), lookup)
  eada = eada[eada['espn_school'].notna()]

  collisions = eada[eada.duplicated('espn_school', keep=False)]
  if not collisions.empty:
    for espn_name, group in collisions.groupby('espn_school'):
      logger.error(
        'Name collision: %s institutions resolve to %r (%s). '
        'Dropping all of them rather than guessing.',
        len(group),
        espn_name,
        '; '.join(group['school'].tolist()),
      )
    eada = eada[~eada['espn_school'].isin(collisions['espn_school'])]

  keep = ['espn_school', 'school', 'state', 'classification', 'sector']
  keep += [c for c in MONEY_COLUMNS if c in eada.columns]
  money = eada[keep].rename(columns={'school': 'institution_name'})
  money['money_report_year'] = chosen_year
  money['money_lag_years'] = (season + SEASON_TO_REPORT_YEAR_LAG) - chosen_year

  coach = _load_optional(config.FINANCE_DIR / f'coach_pay_{season}.csv')
  if coach is not None:
    coach = _attach_espn_school(coach, lookup)
    coach = coach[coach['espn_school'].notna()].drop_duplicates('espn_school')
    if 'confidence' in coach.columns:
      unverified = (
        coach['confidence'].astype(str).str.strip().str.lower() == 'unverified'
      )
      for pay_col in ('total_pay_usd', 'buyout', 'buyout_usd'):
        if pay_col in coach.columns:
          coach.loc[unverified, pay_col] = pd.NA
    columns = {'espn_school': 'espn_school'}
    if 'total_pay_usd' in coach.columns:
      columns['total_pay_usd'] = 'head_coach_pay'
    if 'buyout' in coach.columns:
      columns['buyout'] = 'head_coach_buyout'
    elif 'buyout_usd' in coach.columns:
      columns['buyout_usd'] = 'head_coach_buyout'
    for extra in ('head_coach', 'confidence'):
      if extra in coach.columns:
        columns[extra] = (
          'head_coach_pay_confidence' if extra == 'confidence' else extra
        )
    money = money.merge(
      coach[list(columns)].rename(columns=columns),
      on='espn_school',
      how='left',
    )

  nil = _load_optional(config.FINANCE_DIR / f'nil_revshare_{season}.csv')
  if nil is not None:
    nil = _attach_espn_school(nil, lookup)
    nil = nil[nil['espn_school'].notna()].drop_duplicates('espn_school')
    columns = {'espn_school': 'espn_school'}
    for source, target in (
      ('revshare_cap_usd', 'revshare_cap'),
      ('football_allocation_est_usd', 'football_allocation_est'),
      ('roster_payroll_est_usd', 'roster_payroll_est'),
      ('talent_composite', 'talent_composite'),
    ):
      if source in nil.columns:
        columns[source] = target
    if len(columns) > 1:
      money = money.merge(
        nil[list(columns)].rename(columns=columns),
        on='espn_school',
        how='left',
      )

  missing = sorted(set(schools) - set(money['espn_school']))
  exempt = [s for s in missing if s in names.EADA_EXEMPT]
  unexplained = [s for s in missing if s not in names.EADA_EXEMPT]
  if exempt:
    logger.info(
      '%d teams are exempt from EADA reporting and have no finance row: %s',
      len(exempt),
      ', '.join(exempt),
    )
  if unexplained:
    logger.warning(
      '%d teams have no EADA match: %s',
      len(unexplained),
      ', '.join(unexplained),
    )
  return money.reset_index(drop=True)


def unmatched_report(
  espn_schools: Iterable[str],
  money: pd.DataFrame,
) -> pd.DataFrame:
  """Lists ESPN schools that failed to match a finance record.

  Args:
    espn_schools: Schools in scope.
    money: Output of :func:`build_money_frame`.

  Returns:
    A one-column frame of unmatched school names.
  """
  missing = sorted(set(espn_schools) - set(money['espn_school']))
  return pd.DataFrame({'unmatched_espn_school': missing})
