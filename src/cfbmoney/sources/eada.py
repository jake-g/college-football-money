"""Downloads and parses Department of Education EADA athletics filings.

The Equity in Athletics Disclosure Act requires every co-educational
institution that receives federal student aid and fields an
intercollegiate athletics program to file annual revenue, expense and
participation figures.  It is the only *mandatory, audited-ish,
whole-population* source of college sports money data, which makes it
the backbone of this project.

The public site at https://ope.ed.gov/athletics is an Angular app backed
by a small REST API:

``GET /athletics/api/dataFiles/fileList``
    Lists every published data file with its academic year.
``GET /athletics/api/dataFiles/file?fileName=<name>``
    Streams the zip archive for one academic year.

Each archive contains ``schools.xlsx`` (one row per sport per school)
and ``instLevel.xlsx`` (one row per school).  Field mapping used here,
verified against the codebooks shipped inside the archive:

===========================  ==============================================
``SPORTSCODE == 7``          Football.
``REV_MEN`` / ``EXP_MEN``    Football revenue / expenses for that row.
``GRND_TOTAL_REVENUE``       Whole athletics department revenue.
``GRND_TOTAL_EXPENSE``       Whole athletics department expenses.
``HDCOACH_SALARY_MEN``       Average head coach salary, men's teams.
``ASCOACH_SALARY_MEN``       Average assistant coach salary, men's teams.
``RECRUITEXP_MEN``           Men's recruiting expenses.
===========================  ==============================================

Note that ``IL_*`` columns are *not* department totals; they are the
institution-level residual buckets and must not be used for that
purpose.

Report year N covers academic year N-1 to N, so ``report_year=2025``
describes the financial year that contains the 2024 football season.
"""

from __future__ import annotations

import argparse
import io
import logging
import pathlib
import zipfile

import pandas as pd
import requests

logger = logging.getLogger(__name__)

FILE_LIST_URL = 'https://ope.ed.gov/athletics/api/dataFiles/fileList'
FILE_DOWNLOAD_URL = 'https://ope.ed.gov/athletics/api/dataFiles/file'
SOURCE_PAGE = 'https://ope.ed.gov/athletics/#/datafile/list'

FOOTBALL_SPORTS_CODE = 7

# Columns copied straight from schools.xlsx (sport level).
_SPORT_COLUMNS: dict[str, str] = {
  'REV_MEN': 'football_revenue',
  'EXP_MEN': 'football_expenses',
  'PARTIC_MEN': 'football_participants',
  'OPEXPPERPART_MEN': 'football_opexp_per_participant',
  'OPEXPPERTEAM_MEN': 'football_operating_expenses',
  'MEN_TOTAL_HEADCOACH': 'football_head_coaches',
  'MEN_TOTAL_ASSTCOACH': 'football_assistant_coaches',
}

# Columns copied from instLevel.xlsx (institution level).
_INST_COLUMNS: dict[str, str] = {
  'GRND_TOTAL_REVENUE': 'dept_total_revenue',
  'GRND_TOTAL_EXPENSE': 'dept_total_expenses',
  'HDCOACH_SALARY_MEN': 'avg_head_coach_salary_men',
  'ASCOACH_SALARY_MEN': 'avg_asst_coach_salary_men',
  'NUM_HDCOACH_MEN': 'num_head_coaches_men',
  'NUM_ASCOACH_MEN': 'num_asst_coaches_men',
  'RECRUITEXP_MEN': 'recruiting_expenses_men',
  'RECRUITEXP_TOTAL': 'recruiting_expenses_total',
}


class EadaError(RuntimeError):
  """Raised when EADA data cannot be retrieved or parsed."""


def list_data_files(timeout: int = 60) -> list[dict[str, object]]:
  """Returns the catalogue of published EADA data files.

  Args:
    timeout: Socket timeout in seconds.

  Returns:
    The raw catalogue entries, each with ``FileName``, ``Year`` and
    ``Format`` keys.

  Raises:
    EadaError: If the catalogue cannot be fetched.
  """
  try:
    response = requests.get(FILE_LIST_URL, timeout=timeout)
    response.raise_for_status()
    return response.json()
  except (requests.RequestException, ValueError) as exc:
    raise EadaError(f'Could not list EADA data files: {exc}') from exc


def _pick_file_name(catalogue: list[dict[str, object]], year: int) -> str:
  """Chooses the per-sport Excel archive for an academic year.

  Args:
    catalogue: Output of :func:`list_data_files`.
    year: Report year, e.g. 2025 for academic year 2024-25.

  Returns:
    The archive file name.

  Raises:
    EadaError: If no archive exists for that year.
  """
  candidates = [
    entry
    for entry in catalogue
    if entry.get('Year') == year
    and str(entry.get('FileName', '')).lower().endswith('.zip')
    and 'combined' not in str(entry.get('FileName', '')).lower()
  ]
  if not candidates:
    raise EadaError(f'No EADA archive published for report year {year}')
  excel_first = sorted(candidates, key=lambda e: e.get('Format') != 'Excel')
  return str(excel_first[0]['FileName'])


def download_year(
  year: int,
  raw_dir: pathlib.Path,
  timeout: int = 300,
) -> pathlib.Path:
  """Downloads one academic year's archive, using a local cache.

  Args:
    year: Report year.
    raw_dir: Directory in which archives are cached.
    timeout: Socket timeout in seconds.

  Returns:
    Path to the cached zip archive.

  Raises:
    EadaError: If the download fails.
  """
  raw_dir.mkdir(parents=True, exist_ok=True)
  file_name = _pick_file_name(list_data_files(), year)
  destination = raw_dir / file_name.replace(' ', '_')
  if destination.exists() and destination.stat().st_size > 0:
    logger.info('Using cached EADA archive %s', destination.name)
    return destination

  logger.info('Downloading EADA archive %s', file_name)
  try:
    response = requests.get(
      FILE_DOWNLOAD_URL,
      params={'fileName': file_name},
      stream=True,
      timeout=timeout,
    )
    response.raise_for_status()
    with destination.open('wb') as handle:
      for chunk in response.iter_content(chunk_size=1 << 16):
        handle.write(chunk)
  except requests.RequestException as exc:
    destination.unlink(missing_ok=True)
    raise EadaError(f'Download failed for {file_name}: {exc}') from exc
  return destination


def _read_member(archive: zipfile.ZipFile, prefix: str) -> pd.DataFrame:
  """Reads the first Excel member whose name starts with ``prefix``.

  Args:
    archive: An open zip archive.
    prefix: Lowercase file name prefix, e.g. ``schools``.

  Returns:
    The parsed sheet.

  Raises:
    EadaError: If no matching member exists.
  """
  for name in archive.namelist():
    base = name.split('/')[-1].lower()
    if base.startswith(prefix) and base.endswith('.xlsx'):
      payload = io.BytesIO(archive.read(name))
      return pd.read_excel(payload, engine='openpyxl')
  raise EadaError(f'No {prefix}*.xlsx member in archive')


def parse_year(archive_path: pathlib.Path, year: int) -> pd.DataFrame:
  """Extracts football and department finances from one archive.

  Args:
    archive_path: Path to a cached EADA zip archive.
    year: Report year to stamp on every row.

  Returns:
    One row per institution that fields football.

  Raises:
    EadaError: If the archive is missing expected members.
  """
  with zipfile.ZipFile(archive_path) as archive:
    sports = _read_member(archive, 'schools')
    institutions = _read_member(archive, 'instlevel')

  football = sports[sports['SPORTSCODE'] == FOOTBALL_SPORTS_CODE].copy()
  if football.empty:
    raise EadaError(f'No football rows in {archive_path.name}')

  keep = [
    'unitid',
    'institution_name',
    'state_cd',
    'classification_name',
    'sector_name',
  ]
  keep += [c for c in _SPORT_COLUMNS if c in football.columns]
  football = football[keep].rename(columns=_SPORT_COLUMNS)

  inst_keep = ['unitid'] + [
    c for c in _INST_COLUMNS if c in institutions.columns
  ]
  inst = institutions[inst_keep].rename(columns=_INST_COLUMNS)

  merged = football.merge(inst, on='unitid', how='left')
  merged = merged.rename(
    columns={
      'institution_name': 'school',
      'state_cd': 'state',
      'classification_name': 'classification',
      'sector_name': 'sector',
    }
  )
  merged['school'] = merged['school'].astype(str).str.strip()
  merged['report_year'] = year
  merged['academic_year'] = f'{year - 1}-{str(year)[-2:]}'
  merged['source_url'] = SOURCE_PAGE
  merged = _add_spending_metrics(merged)
  return merged.sort_values('school').reset_index(drop=True)


def _add_spending_metrics(frame: pd.DataFrame) -> pd.DataFrame:
  """Derives the spending-side measures used by the analysis.

  EADA reports football expenses directly, but two useful angles have
  to be derived:

  * ``football_spend_per_player`` scales spending by roster size, which
    keeps a 130-man roster from looking automatically extravagant.
  * ``football_nonoperating_spend`` is total football expenses minus
    game-day operating expenses (travel, lodging, meals, equipment,
    officials).  What is left is overwhelmingly salaries, recruiting
    and facilities overhead, so it is the closest EADA gets to "what
    the program pays its people".

  Coaching payroll is only disclosed as an *average per coach across
  all men's sports*, so the football-specific figure here is an
  estimate and is named accordingly.

  Args:
    frame: The merged sport-level and institution-level frame.

  Returns:
    The frame with derived spending columns added.
  """
  out = frame.copy()
  out['football_net'] = out['football_revenue'] - out['football_expenses']
  if 'football_participants' in out.columns:
    participants = out['football_participants'].where(
      out['football_participants'] > 0
    )
    out['football_spend_per_player'] = out['football_expenses'] / participants
  if 'football_operating_expenses' in out.columns:
    out['football_nonoperating_spend'] = (
      out['football_expenses'] - out['football_operating_expenses']
    )
  head = out.get('avg_head_coach_salary_men')
  assistant = out.get('avg_asst_coach_salary_men')
  if head is not None and assistant is not None:
    if {'num_head_coaches_men', 'num_asst_coaches_men'} <= set(out.columns):
      out['mens_coaching_payroll'] = (
        head * out['num_head_coaches_men']
        + assistant * out['num_asst_coaches_men']
      )
    if {'football_head_coaches', 'football_assistant_coaches'} <= set(
      out.columns
    ):
      # Average men's-sport salaries applied to the football staff.
      # Football coaches are paid far above the men's-sport average, so
      # treat this as a floor, not a true payroll.
      out['football_coach_payroll_est'] = (
        head * out['football_head_coaches']
        + assistant * out['football_assistant_coaches']
      )
  return out


def fetch_years(
  years: list[int],
  raw_dir: pathlib.Path,
  out_dir: pathlib.Path,
  fbs_only: bool = False,
) -> pd.DataFrame:
  """Downloads, parses and writes one CSV per year plus a panel file.

  Args:
    years: Report years to fetch.
    raw_dir: Cache directory for the zip archives.
    out_dir: Directory for the tidy CSV output.
    fbs_only: When True, keep only NCAA Division I-FBS institutions.

  Returns:
    The concatenated panel across all requested years.
  """
  out_dir.mkdir(parents=True, exist_ok=True)
  frames = []
  for year in years:
    try:
      archive = download_year(year, raw_dir)
      frame = parse_year(archive, year)
    except EadaError as exc:
      logger.error('Skipping EADA year %s: %s', year, exc)
      continue
    if fbs_only:
      frame = frame[
        frame['classification'].astype(str).str.contains('FBS', na=False)
      ]
    path = out_dir / f'eada_football_{year}.csv'
    frame.to_csv(path, index=False)
    logger.info('Wrote %d rows to %s', len(frame), path)
    frames.append(frame)

  if not frames:
    raise EadaError('No EADA years could be fetched')
  panel = pd.concat(frames, ignore_index=True)
  panel_path = out_dir / 'eada_football_panel.csv'
  panel.to_csv(panel_path, index=False)
  logger.info('Wrote %d panel rows to %s', len(panel), panel_path)
  return panel


def latest_report_year() -> int:
  """Returns the most recent published EADA report year."""
  years = [
    int(entry['Year'])
    for entry in list_data_files()
    if str(entry.get('FileName', '')).lower().endswith('.zip')
  ]
  if not years:
    raise EadaError('EADA catalogue contained no archives')
  return max(years)


def main(argv: list[str] | None = None) -> int:
  """Command line entry point.

  Args:
    argv: Optional argument vector, defaults to ``sys.argv[1:]``.

  Returns:
    Process exit status.
  """
  parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  parser.add_argument(
    '--years',
    type=int,
    nargs='+',
    default=None,
    help='Report years to fetch; defaults to the latest three.',
  )
  parser.add_argument(
    '--raw-dir',
    type=pathlib.Path,
    default=pathlib.Path('data/finance/raw'),
  )
  parser.add_argument(
    '--out-dir',
    type=pathlib.Path,
    default=pathlib.Path('data/finance'),
  )
  parser.add_argument('--fbs-only', action='store_true')
  parser.add_argument('--verbose', action='store_true')
  args = parser.parse_args(argv)

  logging.basicConfig(
    level=logging.DEBUG if args.verbose else logging.INFO,
    format='%(levelname)s %(name)s: %(message)s',
  )

  years = args.years
  if not years:
    latest = latest_report_year()
    years = [latest, latest - 1, latest - 2]
  fetch_years(years, args.raw_dir, args.out_dir, args.fbs_only)
  return 0


if __name__ == '__main__':
  raise SystemExit(main())
