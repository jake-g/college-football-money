"""What separates good teams from bad, beyond the size of the budget.

The money analysis answers *does spending track winning?*  This module
asks the follow-up questions a reader actually cares about:

* **Momentum vs money** - how much of this season is explained by last
  season, and does the budget add anything on top?
* **Persistent over-performance** - is beating your budget a repeatable
  trait (coaching, culture, scheme) or just noise that washes out?
* **Box-score markers** - which on-field numbers separate winners from
  losers, and which of those does money actually buy?
* **Budget changes** - does a school that raises its budget improve?
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)

MARGIN = 'point_margin_per_game'
MONEY = 'football_expenses'

#: Season box-score columns from ESPN, with readable labels.  Offensive
#: stats describe the team's own offense; ``sacks``, tackles for loss
#: and interceptions caught describe its defense.
BOX_SCORE_STATS: dict[str, str] = {
  'passer_rating': 'Passer rating (offense)',
  'yards_per_carry': 'Yards per carry (offense)',
  'completion_pct': 'Completion % (offense)',
  'sacks': 'Sacks (defense)',
  'rush_yards_per_game': 'Rush yards per game (offense)',
  'interceptions_caught': 'Interceptions caught (defense)',
  'tackles_for_loss': 'Tackles for loss (defense)',
  'interceptions_thrown': 'Interceptions thrown (offense)',
  'pass_yards_per_game': 'Pass yards per game (offense)',
  'fumbles_lost': 'Fumbles lost (offense)',
}


def _with_log_money(panel: pd.DataFrame) -> pd.DataFrame:
  """Returns rows with positive spending plus a ``log_money`` column."""
  if MONEY not in panel.columns or MARGIN not in panel.columns:
    return pd.DataFrame()
  data = panel[panel[MONEY] > 0].copy()
  data['log_money'] = np.log10(data[MONEY].astype(float))
  return data


def _ols(
  data: pd.DataFrame, outcome: str, predictors: list[str]
) -> dict[str, float]:
  """Fits OLS and returns coefficients, t-values, R² and n.

  Args:
    data (pd.DataFrame): Input rows.
    outcome (str): Dependent column.
    predictors (list[str]): Independent columns.

  Returns:
    dict[str, float]: ``coef_<x>``, ``t_<x>``, ``r_squared`` and ``n``.
  """
  rows = data.dropna(subset=[outcome, *predictors])
  n = len(rows)
  if n <= len(predictors) + 2:
    return {}
  design = np.column_stack(
    [np.ones(n)] + [rows[c].to_numpy(dtype=float) for c in predictors]
  )
  y = rows[outcome].to_numpy(dtype=float)
  beta, *_ = np.linalg.lstsq(design, y, rcond=None)
  resid = y - design @ beta
  dof = n - design.shape[1]
  cov = (resid @ resid / dof) * np.linalg.inv(design.T @ design)
  t_values = beta / np.sqrt(np.diag(cov))
  total = (y - y.mean()) @ (y - y.mean())
  out = {'n': float(n), 'r_squared': float(1 - resid @ resid / total)}
  for name, coef, t_value in zip(
    predictors, beta[1:], t_values[1:], strict=True
  ):
    out[f'coef_{name}'] = float(coef)
    out[f't_{name}'] = float(t_value)
  return out


def add_prior_margin(panel: pd.DataFrame) -> pd.DataFrame:
  """Adds each team's point margin from the previous season.

  Args:
    panel (pd.DataFrame): Multi-season frame with ``school``,
      ``season`` and point margin.

  Returns:
    pd.DataFrame: Copy with a ``prior_margin`` column (NaN when the team
    has no row for the previous season).
  """
  prior = panel[['school', 'season', MARGIN]].copy()
  prior['season'] = prior['season'] + 1
  prior = prior.rename(columns={MARGIN: 'prior_margin'})
  return panel.merge(prior, on=['school', 'season'], how='left')


def momentum_vs_money(
  panel: pd.DataFrame, season: int
) -> tuple[pd.DataFrame, dict[str, float]]:
  """Compares last season's margin with the budget as predictors.

  Args:
    panel (pd.DataFrame): Multi-season frame.
    season (int): The in-progress season; excluded from the pooled fit.

  Returns:
    tuple[pd.DataFrame, dict[str, float]]: A per-season table with
    ``r_prior`` and ``r_money``, and a pooled fit over completed seasons
    with R² for each predictor alone and together plus joint t-values.
  """
  data = add_prior_margin(_with_log_money(panel))
  if data.empty:
    return pd.DataFrame(), {}
  data = data.dropna(subset=['prior_margin', 'log_money', MARGIN])
  rows = []
  for year, group in data.groupby('season'):
    if len(group) < 10:
      continue
    rows.append(
      {
        'season': int(year),
        'n': len(group),
        'r_prior': float(
          stats.pearsonr(group['prior_margin'], group[MARGIN])[0]
        ),
        'r_money': float(stats.pearsonr(group['log_money'], group[MARGIN])[0]),
      }
    )
  table = pd.DataFrame(rows)
  complete = data[data['season'] < season]
  pooled: dict[str, float] = {}
  if len(complete) >= 30:
    prior_only = _ols(complete, MARGIN, ['prior_margin'])
    money_only = _ols(complete, MARGIN, ['log_money'])
    both = _ols(complete, MARGIN, ['prior_margin', 'log_money'])
    pooled = {
      'n': both['n'],
      'r2_prior': prior_only['r_squared'],
      'r2_money': money_only['r_squared'],
      'r2_both': both['r_squared'],
      't_prior': both['t_prior_margin'],
      't_money': both['t_log_money'],
      'coef_prior': both['coef_prior_margin'],
      'coef_money': both['coef_log_money'],
      'first_season': float(complete['season'].min()),
      'last_season': float(complete['season'].max()),
    }
  return table, pooled


def budget_residuals(panel: pd.DataFrame) -> pd.DataFrame:
  """Measures how far each team beat or missed its budget each season.

  A separate line of point margin on log spending is fitted for each
  season, so league-wide shifts in scoring do not leak across years.

  Args:
    panel (pd.DataFrame): Multi-season frame.

  Returns:
    pd.DataFrame: ``school``, ``conference``, ``season``, spending,
    margin and ``residual`` (points above the budget line).
  """
  data = _with_log_money(panel)
  if data.empty:
    return pd.DataFrame()
  data = data.dropna(subset=['log_money', MARGIN])
  frames = []
  for _, group in data.groupby('season'):
    if len(group) < 10:
      continue
    slope, intercept = np.polyfit(group['log_money'], group[MARGIN], 1)
    frames.append(
      group.assign(
        residual=group[MARGIN] - (slope * group['log_money'] + intercept)
      )[['school', 'conference', 'season', MONEY, MARGIN, 'residual']]
    )
  if not frames:
    return pd.DataFrame()
  return pd.concat(frames, ignore_index=True)


def residual_persistence(
  residuals: pd.DataFrame, season: int, top_n: int = 8
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
  """Tests whether beating the budget repeats from one year to the next.

  Args:
    residuals (pd.DataFrame): Output of :func:`budget_residuals`.
    season (int): The in-progress season, excluded from the rankings.
    top_n (int): Rows in each ranking.

  Returns:
    tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]: Year-over-year
    residual correlations (``season``, ``r``, ``n``), the most
    consistent over-performers and the most consistent
    under-performers across completed seasons.
  """
  empty = pd.DataFrame()
  if residuals.empty:
    return empty, empty, empty
  wide = residuals.pivot_table(
    index='school', columns='season', values='residual'
  )
  seasons = sorted(wide.columns)
  lag_rows = []
  for previous, current in zip(seasons, seasons[1:], strict=False):
    pair = wide[[previous, current]].dropna()
    if len(pair) >= 10:
      lag_rows.append(
        {
          'season': int(current),
          'n': len(pair),
          'r': float(stats.pearsonr(pair[previous], pair[current])[0]),
        }
      )
  complete = [s for s in seasons if s < season]
  if len(complete) < 2:
    return pd.DataFrame(lag_rows), empty, empty
  block = wide[complete].dropna()
  latest = residuals[residuals['season'] == max(complete)].set_index('school')
  ranking = pd.DataFrame(
    {
      'school': block.index,
      'conference': latest['conference'].reindex(block.index).to_numpy(),
      'mean_residual': block.mean(axis=1).to_numpy(),
      'seasons_above': (block > 0).sum(axis=1).to_numpy(),
      'seasons': len(complete),
      MONEY: latest[MONEY].reindex(block.index).to_numpy(),
    }
  )
  for year in complete:
    ranking[f'residual_{year}'] = block[year].to_numpy()
  over = ranking.nlargest(top_n, 'mean_residual').reset_index(drop=True)
  under = ranking.nsmallest(top_n, 'mean_residual').reset_index(drop=True)
  return pd.DataFrame(lag_rows), over, under


def box_score_markers(panel: pd.DataFrame, season: int) -> pd.DataFrame:
  """Ranks box-score stats by how well they separate winners.

  Each stat is correlated with point margin (what winning teams do) and
  with log spending (what money buys) across completed seasons.

  Args:
    panel (pd.DataFrame): Multi-season frame.
    season (int): The in-progress season, excluded.

  Returns:
    pd.DataFrame: ``stat``, ``label``, ``n``, ``r_margin`` and
    ``r_money``, sorted by the strength of ``r_margin``.
  """
  data = _with_log_money(panel)
  if data.empty:
    return pd.DataFrame()
  data = data[data['season'] < season]
  rows = []
  for column, label in BOX_SCORE_STATS.items():
    if column not in data.columns:
      continue
    usable = data[[column, MARGIN, 'log_money']].dropna()
    if len(usable) < 30:
      continue
    rows.append(
      {
        'stat': column,
        'label': label,
        'n': len(usable),
        'r_margin': float(stats.pearsonr(usable[column], usable[MARGIN])[0]),
        'r_money': float(
          stats.pearsonr(usable[column], usable['log_money'])[0]
        ),
      }
    )
  table = pd.DataFrame(rows)
  if table.empty:
    return table
  order = table['r_margin'].abs().sort_values(ascending=False).index
  return table.loc[order].reset_index(drop=True)


def schedule_strength(panel: pd.DataFrame, season: int) -> dict[str, float]:
  """Checks whether richer teams face tougher opponents.

  Args:
    panel (pd.DataFrame): Multi-season frame with ``opponent_win_pct``.
    season (int): The in-progress season, excluded.

  Returns:
    dict[str, float]: Correlation of log spending with opponent win
    percentage (``r``, ``p``, ``n``), or empty when unavailable.
  """
  data = _with_log_money(panel)
  if data.empty or 'opponent_win_pct' not in data.columns:
    return {}
  data = data[data['season'] < season].dropna(
    subset=['opponent_win_pct', 'log_money']
  )
  if len(data) < 30:
    return {}
  result = stats.pearsonr(data['log_money'], data['opponent_win_pct'])
  return {
    'r': float(result.statistic),
    'p': float(result.pvalue),
    'n': float(len(data)),
  }


def budget_change_effect(panel: pd.DataFrame, season: int) -> dict[str, float]:
  """Tests whether a school's budget change tracks its margin change.

  Compares the earliest and latest completed seasons for each school.
  The cross-section says rich programs win; this asks whether *getting*
  richer helps.

  Args:
    panel (pd.DataFrame): Multi-season frame.
    season (int): The in-progress season, excluded.

  Returns:
    dict[str, float]: ``r``, ``p``, ``n``, the two seasons compared and
    the median budget change in percent, or empty when unavailable.
  """
  data = _with_log_money(panel)
  if data.empty:
    return {}
  complete = sorted(s for s in data['season'].unique() if s < season)
  if len(complete) < 2:
    return {}
  first, last = complete[0], complete[-1]
  wide = data.pivot_table(
    index='school', columns='season', values=['log_money', MARGIN]
  )
  change = pd.DataFrame(
    {
      'money': wide[('log_money', last)] - wide[('log_money', first)],
      'margin': wide[(MARGIN, last)] - wide[(MARGIN, first)],
    }
  ).dropna()
  if len(change) < 30 or change['money'].std() == 0:
    return {}
  result = stats.pearsonr(change['money'], change['margin'])
  return {
    'r': float(result.statistic),
    'p': float(result.pvalue),
    'n': float(len(change)),
    'first_season': float(first),
    'last_season': float(last),
    'median_change_pct': float((10 ** change['money'].median() - 1) * 100),
  }
