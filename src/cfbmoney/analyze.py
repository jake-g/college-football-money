"""Statistics: does money buy wins?

Three layers of analysis, deliberately kept simple and transparent:

1. **Correlations** - Pearson and Spearman between each money metric and
   each performance metric, with sample sizes and p-values.
2. **Regression** - ordinary least squares of a performance metric on
   ``log10`` money plus conference fixed effects, so that "SEC teams win
   more" is not mistaken for "spending wins more".
3. **Residuals** - what each program achieved relative to what its
   budget predicts.  This is the interesting column: who overperforms
   their wallet.

Everything is computed with numpy/scipy so there is no heavyweight
modelling dependency.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import numpy as np
import pandas as pd
from scipy import stats

from . import config

logger = logging.getLogger(__name__)

# Money coming IN.  Careful: revenue is partly a *consequence* of
# winning (tickets, donations, playoff payouts), so a correlation here
# runs in both directions.
REVENUE_METRICS: list[str] = [
  'football_revenue',
  'dept_total_revenue',
]

# Money going OUT.  This is the closer thing to an input: what the
# program chose to spend on staff, recruiting and running the team.
SPENDING_METRICS: list[str] = [
  'football_expenses',
  'football_spend_per_player',
  'football_nonoperating_spend',
  'mens_coaching_payroll',
  'avg_head_coach_salary_men',
  'recruiting_expenses_men',
  'dept_total_expenses',
  'head_coach_pay',
  'roster_payroll_est',
  'talent_composite',
]

# Everything, in the order it should appear in reports.
MONEY_METRICS: list[str] = REVENUE_METRICS + SPENDING_METRICS

# Performance metrics worth correlating against money.
PERFORMANCE_METRICS: list[str] = [
  'win_pct',
  'point_margin_per_game',
  'points_per_game',
  'points_allowed_per_game',
  'total_yards_per_game',
  'yards_per_carry',
  'opponent_win_pct',
]

# Money is extremely skewed, so these columns are analysed in logs.
LOG_TRANSFORM = frozenset(
  {
    'football_revenue',
    'dept_total_revenue',
    'football_expenses',
    'football_spend_per_player',
    'football_nonoperating_spend',
    'mens_coaching_payroll',
    'avg_head_coach_salary_men',
    'recruiting_expenses_men',
    'dept_total_expenses',
    'head_coach_pay',
    'roster_payroll_est',
  }
)


def merge_money_and_results(
  team_season: pd.DataFrame,
  money: pd.DataFrame,
) -> pd.DataFrame:
  """Joins the season summary to the money frame.

  Args:
    team_season: Output of
      :func:`cfbmoney.build.build_team_season_frame`.
    money: Output of :func:`cfbmoney.finance.build_money_frame`.

  Returns:
    The merged analysis table, one row per team.
  """
  merged = team_season.merge(
    money,
    left_on='school',
    right_on='espn_school',
    how='left',
  )
  for column in ('football_revenue', 'dept_total_revenue'):
    if column in merged.columns:
      merged[f'log_{column}'] = np.log10(
        merged[column].where(merged[column] > 0)
      )
  if {'football_revenue', 'dept_total_revenue'} <= set(merged.columns):
    merged['football_share_of_dept'] = (
      merged['football_revenue'] / merged['dept_total_revenue']
    )
  if {'football_revenue', 'football_expenses'} <= set(merged.columns):
    merged['football_margin_usd'] = (
      merged['football_revenue'] - merged['football_expenses']
    )
    merged['spend_to_revenue_ratio'] = (
      merged['football_expenses'] / merged['football_revenue']
    )
  return merged


def revenue_vs_spending(
  frame: pd.DataFrame,
  performance_metrics: Sequence[str] | None = None,
) -> pd.DataFrame:
  """Ranks money-in and money-out metrics by explanatory power.

  This is the table that answers "is revenue just a proxy, or does
  spending tell a different story?".  Each money metric is correlated
  with each performance metric and tagged as revenue or spending.

  Args:
    frame: Merged analysis table.
    performance_metrics: Performance columns to test.

  Returns:
    A frame sorted by R squared, with a ``money_flow`` column holding
    either ``in`` or ``out``.
  """
  table = correlation_table(
    frame,
    money_metrics=MONEY_METRICS,
    performance_metrics=performance_metrics
    or [
      'win_pct',
      'point_margin_per_game',
      'points_per_game',
    ],
  )
  if table.empty:
    return table
  table['money_flow'] = np.where(
    table['money_metric'].isin(REVENUE_METRICS), 'in', 'out'
  )
  return table.sort_values('r_squared', ascending=False).reset_index(drop=True)


def collinearity(
  frame: pd.DataFrame,
  left: str = 'football_revenue',
  right: str = 'football_expenses',
) -> float | None:
  """Returns the correlation between two money columns.

  Used to state plainly how much revenue and spending overlap, which
  governs how much independent signal either one can carry.

  Args:
    frame: Merged analysis table.
    left: First money column.
    right: Second money column.

  Returns:
    The Pearson correlation of the logged columns, or ``None`` when the
    columns are unavailable.
  """
  if not {left, right} <= set(frame.columns):
    return None
  usable = frame[[left, right]].dropna()
  usable = usable[(usable[left] > 0) & (usable[right] > 0)]
  if len(usable) < 5:
    return None
  return float(
    np.corrcoef(np.log10(usable[left]), np.log10(usable[right]))[0, 1]
  )


def _clean_pair(
  frame: pd.DataFrame,
  x: str,
  y: str,
  log_x: bool,
) -> tuple[np.ndarray, np.ndarray]:
  """Returns aligned, finite value arrays for two columns."""
  subset = frame[[x, y]].apply(pd.to_numeric, errors='coerce').dropna()
  if log_x:
    subset = subset[subset[x] > 0]
    x_values = np.log10(subset[x].to_numpy(dtype=float))
  else:
    x_values = subset[x].to_numpy(dtype=float)
  return x_values, subset[y].to_numpy(dtype=float)


def correlation_table(
  frame: pd.DataFrame,
  money_metrics: Sequence[str] | None = None,
  performance_metrics: Sequence[str] | None = None,
  min_observations: int = 8,
) -> pd.DataFrame:
  """Computes correlations between money and performance metrics.

  Args:
    frame: Merged analysis table.
    money_metrics: Money columns to test; defaults to
      :data:`MONEY_METRICS`.
    performance_metrics: Performance columns to test; defaults to
      :data:`PERFORMANCE_METRICS`.
    min_observations: Minimum paired observations required.

  Returns:
    A frame with one row per money/performance pair, sorted by the
    absolute Pearson coefficient.
  """
  money_metrics = list(money_metrics or MONEY_METRICS)
  performance_metrics = list(performance_metrics or PERFORMANCE_METRICS)
  rows = []
  for money_metric in money_metrics:
    if money_metric not in frame.columns:
      continue
    log_x = money_metric in LOG_TRANSFORM
    for performance_metric in performance_metrics:
      if performance_metric not in frame.columns:
        continue
      x_values, y_values = _clean_pair(
        frame, money_metric, performance_metric, log_x
      )
      if len(x_values) < min_observations:
        continue
      pearson = stats.pearsonr(x_values, y_values)
      spearman = stats.spearmanr(x_values, y_values)
      rows.append(
        {
          'money_metric': money_metric,
          'log_scale': log_x,
          'performance_metric': performance_metric,
          'n': len(x_values),
          'pearson_r': pearson.statistic,
          'pearson_p': pearson.pvalue,
          'spearman_rho': spearman.statistic,
          'spearman_p': spearman.pvalue,
          'r_squared': pearson.statistic**2,
        }
      )
  table = pd.DataFrame(rows)
  if table.empty:
    return table
  table['abs_r'] = table['pearson_r'].abs()
  return (
    table.sort_values('abs_r', ascending=False)
    .drop(columns='abs_r')
    .reset_index(drop=True)
  )


def _design_matrix(
  frame: pd.DataFrame,
  predictor: str,
  log_x: bool,
  conference_effects: bool,
) -> tuple[np.ndarray, list[str], pd.Index]:
  """Builds the OLS design matrix.

  Args:
    frame: Analysis table.
    predictor: Money column used as the regressor.
    log_x: Whether to log10-transform the predictor.
    conference_effects: Whether to add conference dummy variables.

  Returns:
    A tuple of (design matrix, column labels, retained row index).
  """
  usable = frame[frame[predictor].notna()]
  if log_x:
    usable = usable[usable[predictor] > 0]
  values = usable[predictor].to_numpy(dtype=float)
  if log_x:
    values = np.log10(values)

  columns = [np.ones(len(usable)), values]
  labels = ['intercept', f'log10({predictor})' if log_x else predictor]

  if conference_effects and 'conference' in usable.columns:
    conferences = sorted(usable['conference'].dropna().unique())
    # Drop the first level to avoid perfect collinearity.
    for conference in conferences[1:]:
      columns.append((usable['conference'] == conference).to_numpy(dtype=float))
      labels.append(f'conf[{conference}]')
  return np.column_stack(columns), labels, usable.index


def fit_ols(
  frame: pd.DataFrame,
  outcome: str = 'win_pct',
  predictor: str = 'football_revenue',
  conference_effects: bool = True,
) -> dict[str, object]:
  """Fits ``outcome ~ money (+ conference)`` by least squares.

  Args:
    frame: Merged analysis table.
    outcome: Performance column to explain.
    predictor: Money column used as the regressor.
    conference_effects: Whether to include conference dummies.

  Returns:
    A dict with the coefficient table, R squared, sample size and a
    per-team residual frame sorted by overperformance.

  Raises:
    ValueError: If required columns are missing or the sample is too
      small to fit.
  """
  for column in (outcome, predictor):
    if column not in frame.columns:
      raise ValueError(f'Column {column!r} is not in the analysis table')

  usable = frame[frame[outcome].notna()]
  log_x = predictor in LOG_TRANSFORM
  design, labels, index = _design_matrix(
    usable, predictor, log_x, conference_effects
  )
  y_values = usable.loc[index, outcome].to_numpy(dtype=float)
  if len(y_values) <= design.shape[1]:
    raise ValueError(
      f'Not enough observations ({len(y_values)}) to fit '
      f'{design.shape[1]} parameters'
    )

  beta, _, _, _ = np.linalg.lstsq(design, y_values, rcond=None)
  fitted = design @ beta
  residuals = y_values - fitted
  dof = len(y_values) - design.shape[1]
  sigma_squared = float(residuals @ residuals) / dof
  covariance = sigma_squared * np.linalg.pinv(design.T @ design)
  standard_errors = np.sqrt(np.diag(covariance))
  with np.errstate(divide='ignore', invalid='ignore'):
    t_values = beta / standard_errors
  p_values = 2 * stats.t.sf(np.abs(t_values), dof)

  total_ss = float(((y_values - y_values.mean()) ** 2).sum())
  residual_ss = float((residuals**2).sum())
  r_squared = 1 - residual_ss / total_ss if total_ss else float('nan')
  adjusted = (
    1 - (1 - r_squared) * (len(y_values) - 1) / dof if dof > 0 else float('nan')
  )

  coefficients = pd.DataFrame(
    {
      'term': labels,
      'estimate': beta,
      'std_error': standard_errors,
      't_value': t_values,
      'p_value': p_values,
    }
  )

  residual_frame = (
    pd.DataFrame(
      {
        'school': usable.loc[index, 'school'].to_numpy(),
        'conference': usable.loc[index, 'conference'].to_numpy()
        if 'conference' in usable.columns
        else None,
        predictor: usable.loc[index, predictor].to_numpy(),
        'actual': y_values,
        'predicted': fitted,
        'residual': residuals,
      }
    )
    .sort_values('residual', ascending=False)
    .reset_index(drop=True)
  )

  return {
    'outcome': outcome,
    'predictor': predictor,
    'n': int(len(y_values)),
    'r_squared': r_squared,
    'adj_r_squared': adjusted,
    'coefficients': coefficients,
    'residuals': residual_frame,
  }


def spending_efficiency(
  frame: pd.DataFrame,
  outcome: str = 'win_pct',
  predictor: str = 'football_revenue',
) -> pd.DataFrame:
  """Ranks programs by performance per dollar.

  Args:
    frame: Merged analysis table.
    outcome: Performance column.
    predictor: Money column.

  Returns:
    A frame with the money rank, performance rank and their difference
    (positive means the team outranks its budget).
  """
  usable = frame[['school', 'conference', predictor, outcome]].dropna().copy()
  usable['money_rank'] = usable[predictor].rank(ascending=False)
  usable['performance_rank'] = usable[outcome].rank(ascending=False)
  usable['rank_gain'] = usable['money_rank'] - usable['performance_rank']
  return usable.sort_values('rank_gain', ascending=False).reset_index(drop=True)


def conference_summary(frame: pd.DataFrame) -> pd.DataFrame:
  """Summarises money and results by conference.

  Args:
    frame: Merged analysis table.

  Returns:
    One row per conference with median money and mean performance.
  """
  columns = {
    'football_revenue': 'median',
    'dept_total_revenue': 'median',
    'win_pct': 'mean',
    'point_margin_per_game': 'mean',
  }
  available = {k: v for k, v in columns.items() if k in frame.columns}
  grouped = frame.groupby('conference').agg(available)
  grouped['teams'] = frame.groupby('conference').size()
  return grouped.sort_values('football_revenue', ascending=False).reset_index()


def write_outputs(
  merged: pd.DataFrame,
  correlations: pd.DataFrame,
  model: dict[str, object] | None,
  season: int,
) -> None:
  """Writes the analysis tables to ``data/processed``.

  Args:
    merged: Merged analysis table.
    correlations: Output of :func:`correlation_table`.
    model: Output of :func:`fit_ols`, or ``None``.
    season: Season year used in filenames.
  """
  config.ensure_directories()
  merged.to_csv(
    config.PROCESSED_DIR / f'analysis_table_{season}.csv', index=False
  )
  correlations.to_csv(
    config.PROCESSED_DIR / f'correlations_{season}.csv', index=False
  )
  if model:
    model['residuals'].to_csv(
      config.PROCESSED_DIR / f'residuals_{season}.csv', index=False
    )
    model['coefficients'].to_csv(
      config.PROCESSED_DIR / f'model_coefficients_{season}.csv',
      index=False,
    )
  logger.info('Analysis tables written to %s', config.PROCESSED_DIR)


def build_panel(seasons: Sequence[int]) -> pd.DataFrame:
  """Stacks several seasons of merged money and results.

  Each season is paired with the finance filing that best matches it,
  so the panel can be used to watch the money/wins relationship move
  over time.

  Args:
    seasons: Season years to include.  Seasons whose processed tables
      are missing are skipped with a warning.

  Returns:
    A long frame with one row per team-season.
  """
  from . import build  # Imported here to avoid a circular import.
  from . import finance

  frames = []
  for season in seasons:
    try:
      team_season = build.read_frame('team_season', season)
    except FileNotFoundError:
      logger.warning('No processed data for season %s; skipping', season)
      continue
    money = finance.build_money_frame(team_season['school'], season=season)
    merged = merge_money_and_results(team_season, money)
    merged['season'] = season
    frames.append(merged)
  if not frames:
    raise ValueError('No seasons could be loaded for the panel')
  panel = pd.concat(frames, ignore_index=True)
  panel.to_csv(config.PROCESSED_DIR / 'panel.csv', index=False)
  logger.info(
    'Panel covers %d team-seasons across %s',
    len(panel),
    sorted(panel['season'].unique()),
  )
  return panel


def correlation_by_season(panel: pd.DataFrame) -> pd.DataFrame:
  """Computes the money/wins correlation separately for each season.

  Args:
    panel: Output of :func:`build_panel`.

  Returns:
    One row per season with the correlation, n and p-value.
  """
  rows = []
  for season, group in panel.groupby('season'):
    usable = group[['football_revenue', 'win_pct']].dropna()
    usable = usable[usable['football_revenue'] > 0]
    if len(usable) < 20:
      continue
    result = stats.pearsonr(
      np.log10(usable['football_revenue']), usable['win_pct']
    )
    rows.append(
      {
        'season': int(season),
        'n': len(usable),
        'pearson_r': result.statistic,
        'p_value': result.pvalue,
        'r_squared': result.statistic**2,
      }
    )
  return pd.DataFrame(rows).sort_values('season').reset_index(drop=True)
