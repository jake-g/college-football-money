"""Client for ESPN's public college football JSON endpoints.

ESPN exposes two undocumented but stable read-only APIs that require no
API key:

* ``site.api.espn.com``  - scoreboards, team schedules, team pages.
* ``sports.core.api.espn.com`` - normalised "core" resources such as
  season statistics, conference membership and polls.

Responses are cached on disk so that re-running the pipeline during a
game week does not hammer ESPN.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

import requests

from . import config

logger = logging.getLogger(__name__)

SITE_API = (
  'https://site.api.espn.com/apis/site/v2/sports/football/college-football'
)
CORE_API = (
  'https://sports.core.api.espn.com/v2/sports/football/leagues/college-football'
)


class EspnError(RuntimeError):
  """Raised when ESPN returns something we cannot use."""


class EspnClient:
  """Fetches college football data from ESPN with an on-disk cache.

  Attributes:
    season: Season year used as the default for season-scoped calls.
    use_cache: When False every request goes to the network.
  """

  def __init__(
    self,
    season: int = config.DEFAULT_SEASON,
    use_cache: bool = True,
    cache_ttl_hours: float = config.CACHE_TTL_HOURS,
  ) -> None:
    """Initialises the client.

    Args:
      season: Default season year, e.g. 2026.
      use_cache: Whether to read from the on-disk cache.
      cache_ttl_hours: Age at which a cached response is refetched.
    """
    self.season = season
    self.use_cache = use_cache
    self.cache_ttl_seconds = cache_ttl_hours * 3600.0
    self._session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(
      pool_connections=32, pool_maxsize=32
    )
    self._session.mount('https://', adapter)
    self._session.mount('http://', adapter)
    if config.USER_AGENT:
      self._session.headers.update({'User-Agent': config.USER_AGENT})
    config.ensure_directories()

  # -- plumbing ---------------------------------------------------------

  def _cache_path(self, url: str, params: dict[str, Any] | None):
    """Returns the cache file path for a request."""
    key = url + '?' + json.dumps(params or {}, sort_keys=True)
    digest = hashlib.sha1(key.encode('utf-8')).hexdigest()[:20]
    slug = (
      url.replace(SITE_API, 'site')
      .replace(CORE_API, 'core')
      .strip('/')
      .replace('/', '_')
      .replace('?', '_')[:80]
    )
    return config.ESPN_CACHE_DIR / f'{slug}_{digest}.json'

  def get_json(
    self,
    url: str,
    params: dict[str, Any] | None = None,
  ) -> dict[str, Any]:
    """Fetches a URL and returns parsed JSON, using the disk cache.

    Args:
      url: Absolute URL to fetch.
      params: Optional query string parameters.

    Returns:
      The decoded JSON body.

    Raises:
      EspnError: If the request fails or the body is not JSON.
    """
    path = self._cache_path(url, params)
    if self.use_cache and path.exists():
      age = time.time() - path.stat().st_mtime
      if age < self.cache_ttl_seconds:
        try:
          return json.loads(path.read_text())
        except json.JSONDecodeError:
          logger.warning('Corrupt cache file %s, refetching', path)

    logger.debug('GET %s params=%s', url, params)
    try:
      response = self._session.get(url, params=params, timeout=30)
      response.raise_for_status()
      payload = response.json()
    except (requests.RequestException, ValueError) as exc:
      raise EspnError(f'ESPN request failed for {url}: {exc}') from exc

    path.write_text(json.dumps(payload))
    time.sleep(config.REQUEST_DELAY_SECONDS)
    return payload

  def _resolve_ref(self, ref: str) -> dict[str, Any]:
    """Follows a ``$ref`` link returned by the core API."""
    return self.get_json(ref.replace('http://', 'https://'))

  # -- teams and conferences -------------------------------------------

  def list_conference_team_ids(self, group_id: int) -> list[str]:
    """Lists ESPN team ids belonging to a conference for the season.

    Args:
      group_id: ESPN conference group id, e.g. 5 for the Big Ten.

    Returns:
      A list of ESPN team id strings.
    """
    url = (
      f'{CORE_API}/seasons/{self.season}/types/'
      f'{config.REGULAR_SEASON_TYPE}/groups/{group_id}/teams'
    )
    payload = self.get_json(url, {'limit': 200})
    ids = []
    for item in payload.get('items', []):
      ref = item.get('$ref', '')
      if '/teams/' in ref:
        ids.append(ref.split('/teams/')[1].split('?')[0])
    return ids

  def get_team(self, team_id: str) -> dict[str, Any]:
    """Returns the site-API team record for a team id."""
    payload = self.get_json(f'{SITE_API}/teams/{team_id}')
    team = payload.get('team')
    if not team:
      raise EspnError(f'No team payload for id {team_id}')
    return team

  def list_teams(self, group_ids: list[int]) -> list[dict[str, Any]]:
    """Builds a team directory for the given conference groups.

    Args:
      group_ids: ESPN conference group ids to include.

    Returns:
      A list of dicts with team id, school, mascot, abbreviation and the
      conference the team plays in this season.
    """
    teams: list[dict[str, Any]] = []
    seen = set()
    for group_id in group_ids:
      conference = config.CONFERENCE_NAMES.get(group_id, str(group_id))
      added = 0
      for team_id in self.list_conference_team_ids(group_id):
        if team_id in seen:
          continue
        seen.add(team_id)
        try:
          team = self.get_team(team_id)
        except EspnError as exc:
          logger.warning('Skipping team %s: %s', team_id, exc)
          continue
        teams.append(
          {
            'team_id': team_id,
            'school': team.get('location'),
            'mascot': team.get('name'),
            'display_name': team.get('displayName'),
            'abbreviation': team.get('abbreviation'),
            'conference': conference,
            'conference_group_id': group_id,
            'is_power': conference in config.POWER_CONFERENCES,
          }
        )
        added += 1
      logger.info('%s: %d teams', conference, added)
    return teams

  # -- schedules and results -------------------------------------------

  def get_team_schedule(self, team_id: str) -> dict[str, Any]:
    """Returns the full season schedule payload for a team."""
    return self.get_json(
      f'{SITE_API}/teams/{team_id}/schedule',
      {'season': self.season, 'seasontype': config.REGULAR_SEASON_TYPE},
    )

  # -- statistics -------------------------------------------------------

  def get_team_season_stats(self, team_id: str) -> dict[str, Any]:
    """Returns cumulative season statistics for a team.

    Args:
      team_id: ESPN team id.

    Returns:
      The raw statistics payload.  Callers should use
      :func:`cfbmoney.build.flatten_team_stats` to tidy it.
    """
    url = (
      f'{CORE_API}/seasons/{self.season}/types/'
      f'{config.REGULAR_SEASON_TYPE}/teams/{team_id}/statistics'
    )
    return self.get_json(url)

  # -- polls ------------------------------------------------------------

  def get_ap_poll(self, week: int | None = None) -> dict[str, Any]:
    """Returns the AP Top 25 poll payload for a week.

    Args:
      week: Week number.  When omitted the latest published poll for the
        season is used.

    Returns:
      The poll payload, or an empty dict when the poll is unavailable.
    """
    if week is None:
      url = f'{SITE_API}/rankings'
      return self.get_json(url, {'season': self.season})
    url = (
      f'{CORE_API}/seasons/{self.season}/types/'
      f'{config.REGULAR_SEASON_TYPE}/weeks/{week}/rankings/1'
    )
    try:
      return self.get_json(url)
    except EspnError:
      logger.warning('No AP poll for week %s', week)
      return {}

  def current_week(self) -> int:
    """Returns the current regular season week number per ESPN."""
    payload = self.get_json(f'{SITE_API}/scoreboard', {'groups': 80})
    return int(payload.get('week', {}).get('number', 0))
