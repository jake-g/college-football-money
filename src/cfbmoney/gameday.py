"""Game-level evidence: luck, close games, home field and crowds.

The season table compresses every game into a record and a margin.  The
game log keeps three things that table loses, and none of them appear in
a federal finance filing:

* **Luck** - a Pythagorean expectation from points scored and allowed
  says what a team's record *should* be.  The gap between that and the
  actual record is mostly close-game luck, and the question is whether
  money buys any of it.
* **Close games versus blowouts** - whether the bigger budget decides
  tight games or only the lopsided ones.
* **Home field and crowds** - home advantage and attendance.  Crowd
  size is the one piece of money-adjacent data that arrives live, game
  by game, rather than two years late.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

import numpy as np
import pandas as pd
from scipy import stats

from . import trends

logger = logging.getLogger(__name__)

MONEY = 'football_expenses'
MARGIN = 'point_margin_per_game'

#: The usual exponent for college football.  Baseball uses 2, the NFL
#: about 2.4; the exact value barely moves the rankings.
PYTHAGOREAN_EXPONENT = 2.37

#: A one-score game is decided by a touchdown and a two-point try.
CLOSE_MARGIN = 8

#: Anything beyond this is a blowout.
BLOWOUT_MARGIN = 16


def _pearson(x: pd.Series, y: pd.Series) -> tuple[float, float]:
  """Returns Pearson r and its p-value, or NaNs with too few rows."""
  if len(x) < 10:
    return float('nan'), float('nan')
  result = stats.pearsonr(x, y)
  return float(result.statistic), float(result.pvalue)


def pythagorean_luck(
  panel: pd.DataFrame,
  season: int,
  exponent: float = PYTHAGOREAN_EXPONENT,
  min_games: int = 3,
) -> tuple[pd.DataFrame, pd.DataFrame]:
  """Compares each team's record with its points-based expectation.

  Args:
    panel (pd.DataFrame): Multi-season frame with ``points_for``,
      ``points_against``, ``wins``, ``losses`` and spending.
    season (int): The in-progress season, whose per-team table is
      returned.
    exponent (float): Pythagorean exponent.
    min_games (int): Minimum games played for a team to be included.

  Returns:
    tuple[pd.DataFrame, pd.DataFrame]: A per-season summary (``n``,
    ``r_pythagorean``: how well the expectation tracks the record,
    ``r_luck_money`` and ``p_luck_money``: whether luck follows budget,
    ``luck_sd``) and the per-team table for ``season`` sorted from
    luckiest to unluckiest by ``luck_wins`` (wins above expectation),
    with ``pythagorean_pct`` and ``luck`` (win% above expectation).
  """
  needed = {'points_for', 'points_against', 'win_pct', 'games_played'}
  if not needed <= set(panel.columns):
    return pd.DataFrame(), pd.DataFrame()
  data = panel[(panel[MONEY] > 0) & (panel['games_played'] >= min_games)]
  data = data.dropna(subset=['points_for', 'points_against', 'win_pct']).copy()
  scored = data['points_for'].astype(float) ** exponent
  allowed = data['points_against'].astype(float) ** exponent
  data['pythagorean_pct'] = scored / (scored + allowed)
  data['luck'] = data['win_pct'] - data['pythagorean_pct']
  data['luck_wins'] = data['luck'] * data['games_played']
  data['log_money'] = np.log10(data[MONEY].astype(float))

  rows = []
  for year, group in data.groupby('season'):
    r_fit, _ = _pearson(group['pythagorean_pct'], group['win_pct'])
    r_money, p_money = _pearson(group['log_money'], group['luck'])
    rows.append(
      {
        'season': int(year),
        'n': len(group),
        'r_pythagorean': r_fit,
        'r_luck_money': r_money,
        'p_luck_money': p_money,
        'luck_sd': float(group['luck'].std()),
      }
    )
  columns = [
    'school',
    'conference',
    MONEY,
    'wins',
    'losses',
    'win_pct',
    'pythagorean_pct',
    'luck',
    'luck_wins',
  ]
  current = (
    data[data['season'] == season][columns]
    .sort_values('luck_wins', ascending=False)
    .reset_index(drop=True)
  )
  return pd.DataFrame(rows), current


def _budget_games(
  panel: pd.DataFrame, games: pd.DataFrame, season: int, week: int | None
) -> pd.DataFrame:
  """Returns FBS-vs-FBS team-game rows with both budgets attached.

  Args:
    panel (pd.DataFrame): Multi-season frame with spending per season.
    games (pd.DataFrame): Long team-game frame for one season.
    season (int): Season the games belong to.
    week (int | None): Last week to include, or every week.

  Returns:
    pd.DataFrame: Completed rows with ``margin``, ``own_spend``,
    ``opp_spend`` and ``richer`` (whether this side had the bigger
    budget).  Ties and games against FCS opponents are dropped.
  """
  spend = trends.season_money(panel, season)
  if spend.empty or games.empty:
    return pd.DataFrame()
  played = trends.played_games(games)
  if week is not None:
    played = played[played['week'] <= week]
  played = played[(played['game_type'] != 'nonconf_fcs')]
  own = played['school'].map(spend)
  opp = played['opponent'].map(spend)
  keep = own.notna() & opp.notna() & (own != opp) & (played['margin'] != 0)
  out = played[keep].copy()
  out['own_spend'] = own[keep]
  out['opp_spend'] = opp[keep]
  out['richer'] = out['own_spend'] > out['opp_spend']
  return out


def _richer_win_rate(rows: pd.DataFrame) -> float:
  """Returns how often the bigger budget won among ``rows``."""
  if rows.empty:
    return float('nan')
  return float(((rows['margin'] > 0) == rows['richer']).mean())


def close_games(
  panel: pd.DataFrame,
  games_by_season: Mapping[int, pd.DataFrame],
  week: int | None = None,
  close_margin: int = CLOSE_MARGIN,
  blowout_margin: int = BLOWOUT_MARGIN,
) -> pd.DataFrame:
  """Splits the richer team's win rate by how close the game was.

  Args:
    panel (pd.DataFrame): Multi-season frame with spending per season.
    games_by_season (Mapping[int, pd.DataFrame]): Long team-game frames.
    week (int | None): Only games through this week count, so seasons
      are compared at the same point; ``None`` uses every game.
    close_margin (int): Largest margin that counts as a one-score game.
    blowout_margin (int): Smallest margin that counts as a blowout.

  Returns:
    pd.DataFrame: One row per season with game counts and the richer
    side's win rate for all games, one-score games and blowouts, plus
    ``close_share`` (one-score games as a share of all games).
  """
  rows = []
  for season, games in sorted(games_by_season.items()):
    data = _budget_games(panel, games, season, week)
    if data.empty:
      continue
    size = data['margin'].abs()
    close = data[size <= close_margin]
    blowout = data[size > blowout_margin]
    # Each game appears twice (once per team), so halve the counts.
    rows.append(
      {
        'season': int(season),
        'games': len(data) // 2,
        'richer_win_all': _richer_win_rate(data),
        'close_games': len(close) // 2,
        'richer_win_close': _richer_win_rate(close),
        'blowout_games': len(blowout) // 2,
        'richer_win_blowout': _richer_win_rate(blowout),
        'close_share': len(close) / len(data) if len(data) else np.nan,
      }
    )
  return pd.DataFrame(rows)


def home_field(
  panel: pd.DataFrame,
  games_by_season: Mapping[int, pd.DataFrame],
  week: int | None = None,
) -> pd.DataFrame:
  """Measures home advantage and whether money buys any of it.

  Neutral-site games and games against FCS opponents are excluded.
  Home advantage is measured within each team - its own home margin
  minus its own away margin - so that a rich team's generally better
  results do not masquerade as a louder stadium.

  Args:
    panel (pd.DataFrame): Multi-season frame with spending per season.
    games_by_season (Mapping[int, pd.DataFrame]): Long team-game frames.
    week (int | None): Only games through this week count.

  Returns:
    pd.DataFrame: One row per season with ``home_games``,
    ``home_win_rate``, ``home_margin``, ``teams``, ``hfa_mean`` (mean
    within-team home-minus-away margin), ``r_hfa_money`` and
    ``p_hfa_money``.
  """
  rows = []
  for season, games in sorted(games_by_season.items()):
    if not {'neutral_site', 'home_away'} <= set(games.columns):
      continue
    data = _budget_games(panel, games, season, week)
    if data.empty:
      continue
    data = data[~data['neutral_site'].fillna(False).astype(bool)]
    home = data[data['home_away'] == 'home']
    per_team = data.groupby(['school', 'home_away'])['margin'].mean().unstack()
    if not {'home', 'away'} <= set(per_team.columns):
      continue
    per_team = per_team.dropna(subset=['home', 'away'])
    per_team['hfa'] = per_team['home'] - per_team['away']
    budgets = data.drop_duplicates('school').set_index('school')['own_spend']
    per_team['log_money'] = np.log10(
      budgets.reindex(per_team.index).astype(float)
    )
    r_money, p_money = _pearson(per_team['log_money'], per_team['hfa'])
    rows.append(
      {
        'season': int(season),
        'home_games': len(home),
        'home_win_rate': float((home['margin'] > 0).mean()),
        'home_margin': float(home['margin'].mean()),
        'teams': len(per_team),
        'hfa_mean': float(per_team['hfa'].mean()),
        'r_hfa_money': r_money,
        'p_hfa_money': p_money,
      }
    )
  return pd.DataFrame(rows)


def home_attendance(
  games_by_season: Mapping[int, pd.DataFrame],
  week: int | None = None,
) -> pd.DataFrame:
  """Averages each team's home crowd per season.

  Args:
    games_by_season (Mapping[int, pd.DataFrame]): Long team-game frames
      with ``attendance``, ``home_away`` and ``neutral_site``.
    week (int | None): Only games through this week count.

  Returns:
    pd.DataFrame: ``season``, ``school``, ``home_games`` and
    ``attendance`` (mean home crowd).  Zero attendance is treated as
    unreported and dropped.
  """
  frames = []
  for season, games in sorted(games_by_season.items()):
    if 'attendance' not in games.columns or games.empty:
      continue
    played = trends.played_games(games)
    if week is not None:
      played = played[played['week'] <= week]
    home = played[
      (played['home_away'] == 'home')
      & ~played['neutral_site'].fillna(False).astype(bool)
      & (played['attendance'] > 0)
    ]
    if home.empty:
      continue
    grouped = home.groupby('school')['attendance'].agg(['size', 'mean'])
    frames.append(
      pd.DataFrame(
        {
          'season': int(season),
          'school': grouped.index,
          'home_games': grouped['size'].to_numpy(),
          'attendance': grouped['mean'].to_numpy(),
        }
      )
    )
  if not frames:
    return pd.DataFrame()
  return pd.concat(frames, ignore_index=True)


def attendance_summary(
  panel: pd.DataFrame, attendance: pd.DataFrame
) -> pd.DataFrame:
  """Relates crowd size to budget and results, season by season.

  Args:
    panel (pd.DataFrame): Multi-season frame.
    attendance (pd.DataFrame): Output of :func:`home_attendance`.

  Returns:
    pd.DataFrame: One row per season with ``n``, ``mean_attendance``,
    ``median_attendance``, ``r_money`` (log crowd vs log spending) and
    ``r_margin`` (log crowd vs point margin).
  """
  if attendance.empty:
    return pd.DataFrame()
  data = panel[panel[MONEY] > 0].merge(
    attendance, on=['season', 'school'], how='inner'
  )
  data = data.dropna(subset=[MARGIN])
  data['log_attendance'] = np.log10(data['attendance'])
  data['log_money'] = np.log10(data[MONEY].astype(float))
  rows = []
  for season, group in data.groupby('season'):
    r_money, _ = _pearson(group['log_money'], group['log_attendance'])
    r_margin, _ = _pearson(group['log_attendance'], group[MARGIN])
    rows.append(
      {
        'season': int(season),
        'n': len(group),
        'mean_attendance': float(group['attendance'].mean()),
        'median_attendance': float(group['attendance'].median()),
        'r_money': r_money,
        'r_margin': r_margin,
      }
    )
  return pd.DataFrame(rows)


def attendance_vs_budget(
  panel: pd.DataFrame, attendance: pd.DataFrame, season: int
) -> dict[str, float]:
  """Pits last season's crowd against the budget as a predictor.

  Attendance in the same season is partly a *reaction* to winning, so
  the previous season's crowd is used instead: it is known before the
  first kickoff, like the budget.

  Args:
    panel (pd.DataFrame): Multi-season frame.
    attendance (pd.DataFrame): Output of :func:`home_attendance`.
    season (int): The in-progress season, excluded from the fit.

  Returns:
    dict[str, float]: ``n``, ``r_money``, ``r_attendance`` (each alone
    against margin), ``t_money`` and ``t_attendance`` (jointly),
    ``r_squared``, ``r_money_attendance`` (how collinear they are) and
    the seasons fitted; empty when the sample is too small.
  """
  if attendance.empty:
    return {}
  prior = attendance[['season', 'school', 'attendance']].copy()
  prior['season'] = prior['season'] + 1
  prior = prior.rename(columns={'attendance': 'prior_attendance'})
  data = panel[(panel[MONEY] > 0) & (panel['season'] < season)]
  data = data.merge(prior, on=['season', 'school'], how='inner')
  data = data.dropna(subset=[MARGIN])
  if len(data) < 30:
    return {}
  log_money = np.log10(data[MONEY].astype(float))
  log_crowd = np.log10(data['prior_attendance'])
  margin = pd.Series(data[MARGIN].to_numpy(dtype=float))
  design = np.column_stack([np.ones(len(data)), log_money, log_crowd])
  beta, *_ = np.linalg.lstsq(design, margin, rcond=None)
  resid = margin.to_numpy() - design @ beta
  dof = len(data) - design.shape[1]
  cov = (resid @ resid / dof) * np.linalg.inv(design.T @ design)
  t_values = beta / np.sqrt(np.diag(cov))
  total = float(((margin - margin.mean()) ** 2).sum())
  return {
    'n': float(len(data)),
    'r_money': _pearson(log_money, margin)[0],
    'r_attendance': _pearson(log_crowd, margin)[0],
    'r_money_attendance': _pearson(log_money, log_crowd)[0],
    't_money': float(t_values[1]),
    't_attendance': float(t_values[2]),
    'r_squared': float(1 - resid @ resid / total) if total else float('nan'),
    'first_season': float(data['season'].min()),
    'last_season': float(data['season'].max()),
  }


def attendance_change(
  attendance: pd.DataFrame, season: int, top_n: int = 6, min_games: int = 2
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, float]]:
  """Compares each school's crowds with the previous season's.

  Pass attendance computed *through the same week* in every season so
  that the comparison is like for like.

  Args:
    attendance (pd.DataFrame): Output of :func:`home_attendance`.
    season (int): The in-progress season.
    top_n (int): Rows in each ranking.
    min_games (int): Minimum home games in both seasons to be ranked.

  Returns:
    tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, float]]:
    League mean crowd per season, biggest gainers, biggest losers (each
    with ``attendance``, ``prior_attendance`` and ``pct_change``) and a
    summary with ``median_pct``, ``mean_pct`` and ``n``.
  """
  empty = pd.DataFrame()
  if attendance.empty:
    return empty, empty, empty, {}
  league = (
    attendance.groupby('season')['attendance']
    .agg(['mean', 'median', 'size'])
    .rename(
      columns={
        'mean': 'mean_attendance',
        'median': 'median_attendance',
        'size': 'teams',
      }
    )
    .reset_index()
  )
  enough = attendance[attendance['home_games'] >= min_games]
  now = enough[enough['season'] == season]
  before = enough[enough['season'] == season - 1][
    ['school', 'attendance']
  ].rename(columns={'attendance': 'prior_attendance'})
  change = now.merge(before, on='school', how='inner')
  if change.empty:
    return league, empty, empty, {}
  change['pct_change'] = change['attendance'] / change['prior_attendance'] - 1
  summary = {
    'median_pct': float(change['pct_change'].median()),
    'mean_pct': float(change['pct_change'].mean()),
    'n': float(len(change)),
  }
  gainers = change.nlargest(top_n, 'pct_change').reset_index(drop=True)
  losers = change.nsmallest(top_n, 'pct_change').reset_index(drop=True)
  return league, gainers, losers, summary
