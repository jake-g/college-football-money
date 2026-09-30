"""Deeper cuts at the money-versus-wins question.

The headline national correlation mixes two very different things:

* **Between leagues** - SEC budgets dwarf MAC budgets, and SEC teams
  beat MAC teams.  That is mostly settled in non-conference games.
* **Within a league** - does the richer team beat its conference peers?
  That is what conference games measure, and it is the version of the
  question a school can actually act on.

This module separates the two, measures spending relative to the
conference rather than in absolute dollars, and tests whether any
single spending line (coaches, recruiting, game-day operations) carries
signal beyond the size of the overall budget.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from collections.abc import Sequence

import numpy as np
import pandas as pd
from scipy import stats

from . import build

logger = logging.getLogger(__name__)

#: Spending lines tested against the total football budget.
COMPONENT_METRICS: list[str] = [
  'mens_coaching_payroll',
  'avg_head_coach_salary_men',
  'avg_asst_coach_salary_men',
  'recruiting_expenses_men',
  'football_operating_expenses',
  'head_coach_pay',
]

GAME_TYPE_LABELS = {
  'conference': 'Conference',
  'nonconf_fbs': 'Non-conference vs FBS',
  'nonconf_fcs': 'vs FCS',
}


def _pearson(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
  """Returns Pearson r and p, or NaNs when the sample is too small."""
  if len(x) < 5:
    return float('nan'), float('nan')
  result = stats.pearsonr(x, y)
  return float(result.statistic), float(result.pvalue)


def add_relative_spend(
  frame: pd.DataFrame,
  column: str = 'football_expenses',
) -> pd.DataFrame:
  """Adds spending relative to the conference median.

  Args:
    frame (pd.DataFrame): Analysis table with ``conference`` and,
      optionally, ``season``.
    column (str): Money column to normalise.

  Returns:
    pd.DataFrame: Copy with ``relative_spend`` (ratio to the conference
    median) and ``log_relative_spend``.
  """
  out = frame.copy()
  if column not in out.columns or 'conference' not in out.columns:
    return out
  # Independents share a label, not a league, so a "league median" for
  # Notre Dame and UConn is meaningless.
  in_league = out['conference'] != 'FBS Independents'
  positive = out[column].where((out[column] > 0) & in_league)
  # A multi-season panel is normalised within each season's league.
  keys = [out['conference']]
  if 'season' in out.columns:
    keys = [out['season'], out['conference']]
  median = positive.groupby(keys).transform('median')
  out['relative_spend'] = positive / median
  out['log_relative_spend'] = np.log10(out['relative_spend'])
  return out


def schedule_split(
  panel: pd.DataFrame,
  games_by_season: Mapping[int, pd.DataFrame],
  money_column: str = 'football_expenses',
) -> pd.DataFrame:
  """Splits the money signal into conference and non-conference games.

  For each season this measures, separately for conference games and
  non-conference games against FBS opponents:

  * how often the higher-spending team won, and
  * how strongly each team's average margin tracks absolute spending
    versus spending relative to its own conference.

  Args:
    panel (pd.DataFrame): Output of :func:`cfbmoney.analyze.build_panel`.
    games_by_season (Mapping[int, pd.DataFrame]): Long team-game frames.
    money_column (str): Spending column to compare.

  Returns:
    pd.DataFrame: One row per season.
  """
  rows = []
  for season, games in sorted(games_by_season.items()):
    season_frame = add_relative_spend(
      panel[panel['season'] == season], money_column
    )
    spend = season_frame.set_index('school')[money_column]
    spend = spend[spend > 0]
    if spend.empty or games.empty:
      continue
    tagged = build.tag_conference_games(games)
    played = tagged[tagged['completed'].fillna(False).astype(bool)].dropna(
      subset=['points_for', 'points_against']
    )
    played = played.assign(
      margin=played['points_for'] - played['points_against']
    )
    row: dict[str, float] = {'season': int(season)}
    for game_type in ('conference', 'nonconf_fbs'):
      subset = played[played['game_type'] == game_type]
      row[f'{game_type}_games'] = int(len(subset) // 2)
      row[f'{game_type}_richer_win'] = _richer_team_win_rate(subset, spend)
      per_team = subset.groupby('school')['margin'].mean()
      joined = season_frame.assign(
        m=season_frame['school'].map(per_team)
      ).dropna(subset=['m', 'log_relative_spend'])
      row[f'{game_type}_r_absolute'] = _pearson(
        np.log10(joined[money_column].to_numpy(dtype=float)),
        joined['m'].to_numpy(dtype=float),
      )[0]
      row[f'{game_type}_r_relative'] = _pearson(
        joined['log_relative_spend'].to_numpy(dtype=float),
        joined['m'].to_numpy(dtype=float),
      )[0]
    fcs = played[played['game_type'] == 'nonconf_fcs']
    row['fcs_games'] = int(len(fcs))
    row['fcs_mean_margin'] = (
      float(fcs['margin'].mean()) if not fcs.empty else float('nan')
    )
    rows.append(row)
  return pd.DataFrame(rows)


def _richer_team_win_rate(games: pd.DataFrame, spend: pd.Series) -> float:
  """Share of decided games won by the higher-spending side.

  Args:
    games (pd.DataFrame): Long team-game rows with ``margin``.
    spend (pd.Series): Spending indexed by school.

  Returns:
    float: Win rate of the richer team, or NaN with no usable games.
  """
  own = games['school'].map(spend)
  opp = games['opponent'].map(spend)
  usable = games[own.notna() & opp.notna() & (own != opp)]
  usable = usable[usable['margin'] != 0]
  if usable.empty:
    return float('nan')
  richer = own[usable.index] > opp[usable.index]
  won = usable['margin'] > 0
  return float((richer == won).mean())


def relative_spend_summary(
  frame: pd.DataFrame,
  outcome: str = 'point_margin_per_game',
  money_column: str = 'football_expenses',
) -> dict[str, float]:
  """Compares absolute and conference-relative spending.

  Args:
    frame (pd.DataFrame): Analysis table.
    outcome (str): Performance column.
    money_column (str): Spending column.

  Returns:
    dict[str, float]: ``r_absolute`` (national), ``r_within`` and
    ``p_within`` (relative spend against the margin demeaned by
    conference) and ``n``.
  """
  data = add_relative_spend(frame, money_column)
  data = data.dropna(subset=['log_relative_spend', outcome])
  if len(data) < 10:
    return {}
  demeaned = data[outcome] - data.groupby('conference')[outcome].transform(
    'mean'
  )
  r_abs, p_abs = _pearson(
    np.log10(data[money_column].to_numpy(dtype=float)),
    data[outcome].to_numpy(dtype=float),
  )
  r_within, p_within = _pearson(
    data['log_relative_spend'].to_numpy(dtype=float),
    demeaned.to_numpy(dtype=float),
  )
  return {
    'n': float(len(data)),
    'r_absolute': r_abs,
    'p_absolute': p_abs,
    'r_within': r_within,
    'p_within': p_within,
  }


def relative_spend_by_season(
  panel: pd.DataFrame,
  outcome: str = 'point_margin_per_game',
  money_column: str = 'football_expenses',
) -> pd.DataFrame:
  """Runs :func:`relative_spend_summary` separately for each season.

  Args:
    panel (pd.DataFrame): Multi-season frame with a ``season`` column.
    outcome (str): Performance column.
    money_column (str): Spending column.

  Returns:
    pd.DataFrame: One row per season with ``n``, ``r_absolute``,
    ``r_within`` and ``p_within``.
  """
  if 'season' not in panel.columns:
    return pd.DataFrame()
  rows = []
  for season, group in panel.groupby('season'):
    summary = relative_spend_summary(
      group.drop(
        columns=['relative_spend', 'log_relative_spend'], errors='ignore'
      ),
      outcome,
      money_column,
    )
    if summary:
      rows.append({'season': int(season), **summary})
  return pd.DataFrame(rows)


def relative_spend_extremes(
  frame: pd.DataFrame,
  conferences: Sequence[str],
  top_n: int = 6,
) -> tuple[pd.DataFrame, pd.DataFrame]:
  """Returns the biggest and smallest spenders relative to their league.

  Args:
    frame (pd.DataFrame): Analysis table.
    conferences (Sequence[str]): Conferences to include.
    top_n (int): Rows per side.

  Returns:
    tuple[pd.DataFrame, pd.DataFrame]: (highest, lowest) relative spend.
  """
  data = add_relative_spend(frame)
  data = data[data['conference'].isin(conferences)].dropna(
    subset=['relative_spend']
  )
  columns = [
    c
    for c in (
      'school',
      'conference',
      'football_expenses',
      'relative_spend',
      'wins',
      'losses',
      'point_margin_per_game',
    )
    if c in data.columns
  ]
  high = data.nlargest(top_n, 'relative_spend')[columns]
  low = data.nsmallest(top_n, 'relative_spend')[columns]
  return high.reset_index(drop=True), low.reset_index(drop=True)


def _standardised_ols(
  y: np.ndarray,
  predictors: Sequence[np.ndarray],
) -> tuple[np.ndarray, np.ndarray, float]:
  """Fits OLS on z-scored predictors.

  Args:
    y (np.ndarray): Outcome.
    predictors (Sequence[np.ndarray]): Predictor columns.

  Returns:
    tuple[np.ndarray, np.ndarray, float]: Coefficients (without the
    intercept), their t statistics and the model R squared.
  """
  columns = [np.ones(len(y))]
  for values in predictors:
    std = values.std()
    columns.append((values - values.mean()) / std if std else values * 0)
  design = np.column_stack(columns)
  beta, *_ = np.linalg.lstsq(design, y, rcond=None)
  residuals = y - design @ beta
  dof = len(y) - design.shape[1]
  sigma_squared = float(residuals @ residuals) / dof
  covariance = sigma_squared * np.linalg.pinv(design.T @ design)
  with np.errstate(divide='ignore', invalid='ignore'):
    t_values = beta / np.sqrt(np.diag(covariance))
  total = float(((y - y.mean()) ** 2).sum())
  r_squared = 1 - float(residuals @ residuals) / total if total else np.nan
  return beta[1:], t_values[1:], r_squared


def spending_decomposition(
  frame: pd.DataFrame,
  outcome: str = 'point_margin_per_game',
  base: str = 'football_expenses',
  components: Sequence[str] | None = None,
) -> pd.DataFrame:
  """Tests whether a spending line adds signal beyond the total budget.

  Each component is fitted alongside the logged total football budget.
  If coaching payroll, say, mattered *independently* of how big the
  operation is, its coefficient would stay significant with the total
  budget in the model.

  Args:
    frame (pd.DataFrame): Analysis table.
    outcome (str): Performance column.
    base (str): Total budget column.
    components (Sequence[str] | None): Spending lines to test.

  Returns:
    pd.DataFrame: One row per component with ``n``, correlation with the
    base budget, the component's own r, and its standardised coefficient
    and t statistic when the base budget is held fixed.
  """
  rows = []
  for component in components or COMPONENT_METRICS:
    if component not in frame.columns or base not in frame.columns:
      continue
    data = frame[[component, base, outcome]].dropna()
    data = data[(data[component] > 0) & (data[base] > 0)]
    if len(data) < 15:
      continue
    x_component = np.log10(data[component].to_numpy(dtype=float))
    x_base = np.log10(data[base].to_numpy(dtype=float))
    y = data[outcome].to_numpy(dtype=float)
    beta, t_values, r_squared = _standardised_ols(y, [x_base, x_component])
    _, _, base_r_squared = _standardised_ols(y, [x_base])
    rows.append(
      {
        'component': component,
        'n': len(data),
        'corr_with_budget': _pearson(x_component, x_base)[0],
        'r_alone': _pearson(x_component, y)[0],
        'added_coef': float(beta[1]),
        'added_t': float(t_values[1]),
        'r_squared_gain': float(r_squared - base_r_squared),
      }
    )
  return pd.DataFrame(rows)
