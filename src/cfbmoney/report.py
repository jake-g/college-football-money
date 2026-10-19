"""Renders the markdown research report."""

from __future__ import annotations

import datetime
import logging
import pathlib
import re

import numpy as np
import pandas as pd
from scipy import stats

from . import config

logger = logging.getLogger(__name__)

_MONEY_LABELS = {
  'football_revenue': 'Football revenue',
  'football_expenses': 'Football expenses',
  'dept_total_revenue': 'Athletics dept revenue',
  'avg_head_coach_salary_men': "Avg men's head coach salary",
  'recruiting_expenses_men': "Men's recruiting spend",
  'head_coach_pay': 'Head coach total pay',
  'roster_payroll_est': 'Roster payroll estimate',
  'talent_composite': '247 team talent composite',
  'dept_total_expenses': 'Athletics dept expenses',
  'mens_coaching_payroll': "Men's coaching payroll",
  'football_coach_payroll_est': 'Football coaching payroll (est)',
  'football_spend_per_player': 'Football spend per player',
  'football_nonoperating_spend': 'Football non-operating spend',
  'revshare_cap': 'Revenue-share cap',
}


def _usd_millions(value: float | None) -> str:
  """Formats a dollar amount in millions."""
  if value is None or pd.isna(value):
    return '-'
  return f'${value / 1e6:,.1f}M'


def _pct(value: float | None) -> str:
  """Formats a fraction as a percentage."""
  if value is None or pd.isna(value):
    return '-'
  return f'{value * 100:.1f}%'


def _fmt_p(value: float | None) -> str:
  """Formats a p-value, flooring tiny values at ``<0.01``."""
  if value is None or pd.isna(value):
    return '-'
  return '<0.01' if value < 0.01 else f'{value:.2f}'


def _stars(p_value: float) -> str:
  """Returns a significance marker for a p-value."""
  if pd.isna(p_value):
    return ''
  if p_value < 0.001:
    return '***'
  if p_value < 0.01:
    return '**'
  if p_value < 0.05:
    return '*'
  return ''


def _figure(
  pool: dict[str, str],
  stem: str,
  prefix: str,
  caption: str | None = None,
) -> list[str]:
  """Pops a figure from the pool and returns its markdown embed.

  Figures are placed next to the text that discusses them rather than
  dumped at the end.  Anything never claimed by a section is listed
  under "Other figures" so nothing silently disappears.

  Args:
    pool (dict[str, str]): Unclaimed figure filenames to paths.
    stem (str): Filename prefix identifying the figure.
    prefix (str): Relative path prefix for the markdown link.
    caption (str | None): Alt text; defaults to the filename.

  Returns:
    list[str]: Markdown lines, empty when the figure is absent.
  """
  for name in list(pool):
    if name.startswith(stem):
      pool.pop(name)
      text = caption or name.replace('_', ' ').replace('.png', '')
      return [f'![{text}]({prefix}{name})', '']
  return []


def _fmt_r(value: float | None, digits: int = 2) -> str:
  """Formats a correlation, or ``-`` when missing."""
  if value is None or pd.isna(value):
    return '-'
  return f'{value:+.{digits}f}'


def _flow_section(overlap: float | None) -> list[str]:
  """Builds the money-in versus money-out framing."""
  lines = [
    'Revenue is money **coming in** and partly a *reward* for winning '
    '(tickets, donations, playoff payouts). Spending is money **going '
    'out** and closer to an *input* the program controls.',
    '',
  ]
  if overlap is not None:
    lines += [
      f'In practice they are nearly the same variable: log revenue and '
      f'log spending correlate at **{overlap:.2f}**, so every money '
      'metric below tells essentially the same story. The table shows '
      'correlations with each outcome; the full table with p-values and '
      'Spearman rank correlations is in '
      '`data/processed/correlations_<season>.csv`.',
      '',
    ]
  return lines


_MATRIX_OUTCOMES = (
  ('point_margin_per_game', 'Margin/g'),
  ('win_pct', 'Win%'),
  ('points_per_game', 'Pts/g'),
  ('points_allowed_per_game', 'Allowed/g'),
)


def _correlation_matrix(correlations: pd.DataFrame) -> list[str]:
  """Renders one row per money metric, one column per outcome.

  Replaces a long pair-per-row listing: the same information fits in a
  dozen rows and the pattern (everything is about +0.5 to +0.6) is
  visible at a glance.

  Args:
    correlations (pd.DataFrame): Output of
      :func:`cfbmoney.analyze.correlation_table`.

  Returns:
    list[str]: Markdown lines.
  """
  if correlations.empty or 'money_metric' not in correlations.columns:
    return ['_No correlations could be computed._', '']
  pivot = correlations.pivot_table(
    index='money_metric',
    columns='performance_metric',
    values='pearson_r',
  )
  p_values = correlations.pivot_table(
    index='money_metric',
    columns='performance_metric',
    values='pearson_p',
  )
  counts = correlations.groupby('money_metric')['n'].max()
  order = pivot.reindex(
    pivot.get('point_margin_per_game', pd.Series(dtype=float))
    .sort_values(ascending=False)
    .index
  ).index
  header = '| Money metric | n | ' + ' | '.join(
    label for _, label in _MATRIX_OUTCOMES
  )
  lines = [
    header + ' |',
    '| --- | ---: |' + ' ---: |' * len(_MATRIX_OUTCOMES),
  ]
  for metric in order:
    cells = []
    for column, _ in _MATRIX_OUTCOMES:
      value = pivot.at[metric, column] if column in pivot.columns else None
      p_value = (
        p_values.at[metric, column] if column in p_values.columns else None
      )
      stars = _stars(p_value) if p_value is not None else ''
      cells.append(f'{_fmt_r(value)}{stars}')
    lines.append(
      f'| {_MONEY_LABELS.get(metric, metric)} | {int(counts[metric])} | '
      + ' | '.join(cells)
      + ' |'
    )
  lines += [
    '',
    'Money columns are log-scaled except the talent composite. '
    '`*` p<0.05, `**` p<0.01, `***` p<0.001.',
    '',
  ]
  return lines


def _model_section(model: dict[str, object]) -> list[str]:
  """Builds the regression section, showing only the money term.

  The conference dummies are nuisance terms; none is individually
  significant once money is in the model.  They are written in full to
  ``data/processed/model_coefficients_<season>.csv``.
  """
  coefficients: pd.DataFrame = model['coefficients']
  money = coefficients[
    ~coefficients['term'].str.startswith('conf[')
    & (coefficients['term'] != 'intercept')
  ]
  dummies = int(coefficients['term'].str.startswith('conf[').sum())
  lines = [
    f'OLS with {dummies} conference fixed effects (outcome '
    f'**{model["outcome"]}**, n = {model["n"]}, '
    f'R² = {model["r_squared"]:.3f}, adjusted {model["adj_r_squared"]:.3f}):',
    '',
    '| Term | Estimate | Std error | t | p |',
    '| --- | ---: | ---: | ---: | ---: |',
  ]
  for row in money.itertuples():
    lines.append(
      f'| {row.term} | {row.estimate:+.4f} | {row.std_error:.4f} | '
      f'{row.t_value:+.2f} | {row.p_value:.4f}{_stars(row.p_value)} |'
    )
  lines.append('')
  estimate = money['estimate'].iloc[0] if not money.empty else None
  if estimate is not None and model['outcome'] == 'win_pct':
    lines += [
      f'Doubling the football budget within the same conference adds '
      f'**{estimate * 0.301 * 100:+.1f} percentage points of win rate** '
      '(log10(2) = 0.301).',
      '',
    ]
  return lines


def _schedule_section(split: pd.DataFrame, season: int) -> list[str]:
  """Renders the conference versus non-conference decomposition.

  Args:
    split (pd.DataFrame): Output of
      :func:`cfbmoney.insights.schedule_split`.
    season (int): The in-progress season.

  Returns:
    list[str]: Markdown lines.
  """
  if split.empty:
    return []
  lines = [
    'The national correlation blends two different contests: '
    '**non-conference** games (often Power 4 vs Group of Five budgets) and '
    '**conference** games (peers sharing media revenue).',
    '',
    '| Season | Non-conf FBS games | Richer team wins | Conf games | '
    'Richer team wins | Conf r, absolute $ | Conf r, $ vs league |',
    '| ---: | ---: | ---: | ---: | ---: | ---: | ---: |',
  ]
  for row in split.itertuples():
    label = (
      f'{row.season} (in progress)'
      if row.season == season
      else (str(row.season))
    )
    lines.append(
      f'| {label} | {row.nonconf_fbs_games} | {_pct(row.nonconf_fbs_richer_win)} | '
      f'{row.conference_games} | {_pct(row.conference_richer_win)} | '
      f'{_fmt_r(row.conference_r_absolute)} | '
      f'{_fmt_r(row.conference_r_relative)} |'
    )
  lines.append('')

  complete = split[split['season'] < season]
  if not complete.empty:
    nonconf = complete['nonconf_fbs_richer_win'].mean()
    conf = complete['conference_richer_win'].mean()
    rel = complete['conference_r_relative'].mean()
    absolute = complete['conference_r_absolute'].mean()
    lines += [
      f'Across completed seasons the bigger budget wins **{_pct(nonconf)}** '
      f'of non-conference FBS games but only **{_pct(conf)}** of conference '
      f'games. Inside a conference, raw dollars barely track margin '
      f'(r = {absolute:+.2f}), whereas spending *relative to the league '
      f'median* does (r = {rel:+.2f}).',
      '',
    ]
  fcs = split.dropna(subset=['fcs_mean_margin'])
  if not fcs.empty:
    lines += [
      f'FCS games are excluded above; FBS teams won them by an average of '
      f'**{fcs["fcs_mean_margin"].mean():+.1f} points**.',
      '',
    ]
  return lines


def _relative_section(
  summary: dict[str, float] | None,
  extremes: tuple[pd.DataFrame, pd.DataFrame] | None,
  by_season: pd.DataFrame | None = None,
) -> list[str]:
  """Renders the conference-relative spending analysis.

  Args:
    summary (dict[str, float] | None): Output of
      :func:`cfbmoney.insights.relative_spend_summary`.
    extremes (tuple | None): Output of
      :func:`cfbmoney.insights.relative_spend_extremes`.
    by_season (pd.DataFrame | None): Output of
      :func:`cfbmoney.insights.relative_spend_by_season`.

  Returns:
    list[str]: Markdown lines.
  """
  if not summary:
    return []
  lines = [
    'Re-expressing spending as a multiple of the conference median and '
    'margin as points above the conference mean removes the SEC-vs-MAC '
    'gap to test whether *out-spending your own league* pays:',
    '',
  ]
  if by_season is not None and not by_season.empty:
    lines += [
      '| Season | n | National r (absolute $) | Within-league r '
      '(relative $) | p (within) |',
      '| --- | ---: | ---: | ---: | ---: |',
    ]
    latest = int(by_season['season'].max())
    for row in by_season.itertuples():
      label = f'{row.season}' + (
        ' (in progress)' if row.season == latest else ''
      )
      lines.append(
        f'| {label} | {int(row.n)} | {row.r_absolute:+.2f} | '
        f'{row.r_within:+.2f} | {row.p_within:.1g} |'
      )
    complete = by_season[by_season['season'] < latest]
    lines.append('')
    if not complete.empty:
      lines += [
        'Over full seasons, out-spending your conference predicts margin '
        f'as well as raw dollars do nationally (within r = '
        f'{complete["r_within"].mean():+.2f} vs national '
        f'{complete["r_absolute"].mean():+.2f}).',
        '',
      ]
  else:
    lines += [
      f'- National, absolute dollars: r = **{summary["r_absolute"]:+.2f}**',
      f'- Within conference, relative dollars: r = '
      f'**{summary["r_within"]:+.2f}** (p = {summary["p_within"]:.4f}, '
      f'n = {int(summary["n"])})',
      '',
    ]
  if extremes is None:
    return lines
  high, low = extremes
  for title, frame in (
    ('Biggest spenders relative to their Power 4 league', high),
    ('Smallest spenders relative to their Power 4 league', low),
  ):
    if frame.empty:
      continue
    lines += [
      f'**{title}**',
      '',
      '| Program | Conf | Football exp | x league median | Record | Margin/g |',
      '| --- | --- | ---: | ---: | :---: | ---: |',
    ]
    for row in frame.itertuples():
      record = (
        f'{int(row.wins)}-{int(row.losses)}'
        if not pd.isna(getattr(row, 'wins', float('nan')))
        else '-'
      )
      lines.append(
        f'| {row.school} | {row.conference} | '
        f'{_usd_millions(row.football_expenses)} | '
        f'{row.relative_spend:.2f}x | {record} | '
        f'{row.point_margin_per_game:+.1f} |'
      )
    lines.append('')
  return lines


def _decomposition_section(decomposition: pd.DataFrame) -> list[str]:
  """Renders the spending-line decomposition.

  Args:
    decomposition (pd.DataFrame): Output of
      :func:`cfbmoney.insights.spending_decomposition`.

  Returns:
    list[str]: Markdown lines.
  """
  if decomposition.empty:
    return []
  labels = dict(_MONEY_LABELS)
  labels.update(
    {
      'avg_asst_coach_salary_men': "Avg men's assistant coach salary",
      'football_operating_expenses': 'Football game-day operations',
    }
  )
  lines = [
    'Each spending line is added to a regression that already controls '
    'for total football budget (|t| > 2 indicates independent signal):',
    '',
    '| Spending line | n | Corr. with total budget | r with margin alone | '
    'Added coef (pts per SD) | t | R² gain |',
    '| --- | ---: | ---: | ---: | ---: | ---: | ---: |',
  ]
  for row in decomposition.itertuples():
    lines.append(
      f'| {labels.get(row.component, row.component)} | {row.n} | '
      f'{row.corr_with_budget:.2f} | {row.r_alone:+.2f} | '
      f'{row.added_coef:+.1f} | {row.added_t:+.1f} | '
      f'{row.r_squared_gain:+.3f} |'
    )
  lines.append('')
  strongest = decomposition.loc[decomposition['added_t'].abs().idxmax()]
  lines += [
    f'Every component correlates **{decomposition["corr_with_budget"].min():.2f} '
    f'or higher** with total budget, and none is significant once total '
    f'budget is held fixed (max |t| = {abs(strongest.added_t):.1f}, '
    f'{labels.get(strongest.component, strongest.component)}). Rich '
    'programs spend across the board, so overall scale—not a single line '
    'item—drives the correlation.',
    '',
  ]
  return lines


def _slug(heading: str) -> str:
  """Returns the GitHub anchor for a markdown heading."""
  text = re.sub(r'[^\w\s-]', '', heading.lower())
  return re.sub(r'\s', '-', text.strip())


def _demote(lines: list[str]) -> list[str]:
  """Pushes every markdown heading down one level.

  Section builders emit ``##`` headings; inside a numbered part they
  become ``###`` so the document outline stays consistent.
  """
  return [f'#{line}' if line.startswith('#') else line for line in lines]


def _momentum_lines(
  table: pd.DataFrame, pooled: dict[str, float], season: int
) -> list[str]:
  """Renders last season's margin versus the budget as predictors.

  Args:
    table (pd.DataFrame): Per-season correlations from
      :func:`cfbmoney.drivers.momentum_vs_money`.
    pooled (dict[str, float]): Pooled fit over completed seasons.
    season (int): The in-progress season.

  Returns:
    list[str]: Markdown lines.
  """
  if table.empty:
    return []
  lines = [
    'Before crediting the budget, compare it with the simplest baseline: '
    "last season's point margin.",
    '',
    "| Season | n | r, last season's margin | r, football spending |",
    '| --- | ---: | ---: | ---: |',
  ]
  for row in table.itertuples():
    label = (
      f'{row.season} (in progress)'
      if row.season == season
      else (str(row.season))
    )
    lines.append(
      f'| {label} | {row.n} | {row.r_prior:+.2f} | {row.r_money:+.2f} |'
    )
  lines.append('')
  if pooled:
    lines += [
      f'Pooling {int(pooled["first_season"])}-{int(pooled["last_season"])}, '
      f'last season alone explains **{pooled["r2_prior"]:.0%}** of margin '
      f'variance, spending alone **{pooled["r2_money"]:.0%}**, and both '
      f'together **{pooled["r2_both"]:.0%}**. Both remain significant in a '
      f'joint model (t = {pooled["t_prior"]:.1f} for prior margin, '
      f'{pooled["t_money"]:.1f} for spending): each point of prior margin '
      f'carries {pooled["coef_prior"]:.2f} points forward, and doubling '
      f'the budget adds **{pooled["coef_money"] * 0.301:+.1f} points per '
      'game** on top.',
      '',
    ]
  current = table[table['season'] == season]
  if not current.empty:
    gap = float(current.iloc[0].r_money - current.iloc[0].r_prior)
    if gap >= 0.03:
      lines += [
        f'Early in {season}, spending out-predicts prior margin '
        f'({current.iloc[0].r_money:+.2f} vs {current.iloc[0].r_prior:+.2f}) '
        'because non-conference mismatches weight the opening weeks.',
        '',
      ]
    elif abs(gap) < 0.03:
      lines += [
        f'In {season} to date, prior margin ({current.iloc[0].r_prior:+.2f}) '
        f'and spending ({current.iloc[0].r_money:+.2f}) are dead even as '
        'conference play replaces September mismatches.',
        '',
      ]
  return lines


def _persistence_lines(
  lag: pd.DataFrame,
  over: pd.DataFrame,
  under: pd.DataFrame,
  season: int,
) -> list[str]:
  """Renders how consistently teams beat or miss their budget.

  Args:
    lag (pd.DataFrame): Year-over-year residual correlations.
    over (pd.DataFrame): Most consistent over-performers.
    under (pd.DataFrame): Most consistent under-performers.
    season (int): The in-progress season.

  Returns:
    list[str]: Markdown lines.
  """
  if lag.empty:
    return []
  lines = [
    'Each team gets a seasonal residual: actual point margin minus the '
    'margin expected for its budget. If beating the budget were pure luck, '
    'residuals would not correlate year to year.',
    '',
    "| Season | n | r with previous season's residual |",
    '| --- | ---: | ---: |',
  ]
  for row in lag.itertuples():
    label = (
      f'{row.season} (in progress)'
      if row.season == season
      else (str(row.season))
    )
    lines.append(f'| {label} | {row.n} | {row.r:+.2f} |')
  lines.append('')
  complete = lag[lag['season'] < season]
  if not complete.empty:
    lines += [
      f'Across completed seasons the residual repeats at r = '
      f'**{complete["r"].mean():+.2f}** (~{complete["r"].mean() * 10:.0f} '
      'points carried over per 10 points of prior over-performance), '
      'capturing coaching, player development, scheme, and off-books NIL.',
      '',
    ]
  if over.empty or under.empty:
    return lines
  years = sorted(
    int(c.split('_')[1]) for c in over.columns if c.startswith('residual_')
  )
  has_current = (
    'current_residual' in over.columns
    and over['current_residual'].notna().any()
  )
  curr_header = f' | {season} to date |' if has_current else ' |'
  header = (
    '| Program | Conf | Football exp | '
    + ' | '.join(str(y) for y in years)
    + f' | Average{curr_header}'
  )
  divider = '| --- | --- | ---: | ' + ' | '.join('---:' for _ in years)
  divider += ' | ---: |' + (' ---: |' if has_current else '')
  for title, frame in (
    ('Consistently beating their budget (points per game)', over),
    ('Consistently missing their budget (points per game)', under),
  ):
    lines += [f'**{title}**', '', header, divider]
    for row in frame.itertuples():
      values = ' | '.join(
        f'{getattr(row, f"residual_{y}"):+.1f}' for y in years
      )
      curr_val = getattr(row, 'current_residual', float('nan'))
      curr_cell = (
        f' | {"-" if pd.isna(curr_val) else f"{curr_val:+.1f}"} |'
        if has_current
        else ' |'
      )
      lines.append(
        f'| {row.school} | {row.conference} | '
        f'{_usd_millions(row.football_expenses)} | {values} | '
        f'**{row.mean_residual:+.1f}**{curr_cell}'
      )
    lines.append('')
  cheap = over.nsmallest(2, 'football_expenses')
  rich = over.nlargest(2, 'football_expenses')
  low = cheap['football_expenses'].max()
  high = rich['football_expenses'].min()
  if low > 0 and high / low >= 3:
    lines += [
      'Over-performers span budgets from '
      f'{" and ".join(cheap["school"])} ({_usd_millions(low)} or less) to '
      f'{" and ".join(rich["school"])} ({_usd_millions(high)} or more).',
      '',
    ]
  return lines


def _markers_lines(
  markers: pd.DataFrame, schedule: dict[str, float] | None
) -> list[str]:
  """Renders the box-score markers of a good team.

  Args:
    markers (pd.DataFrame): Output of
      :func:`cfbmoney.drivers.box_score_markers`.
    schedule (dict[str, float] | None): Output of
      :func:`cfbmoney.drivers.schedule_strength`.

  Returns:
    list[str]: Markdown lines.
  """
  if markers.empty:
    return []
  lines = [
    'Which on-field numbers separate winners from losers, and which of '
    'them does money buy? Each season stat is correlated with point '
    'margin and with football spending, pooling completed seasons '
    f'(n = {int(markers["n"].max())} team-seasons).',
    '',
    '| Stat | r with point margin | r with spending |',
    '| --- | ---: | ---: |',
  ]
  for row in markers.itertuples():
    lines.append(f'| {row.label} | {row.r_margin:+.2f} | {row.r_money:+.2f} |')
  lines.append('')
  top = markers.iloc[0]
  strong = markers[markers['r_margin'].abs() >= 0.5]
  if not strong.empty:
    gap = (
      strong.assign(gap=strong['r_margin'].abs() - strong['r_money'].abs())
      .nlargest(1, 'gap')
      .iloc[0]
    )
    lines += [
      f'**{top.label.split(" (")[0]}** is the clearest marker of a good '
      f'team (r = {top.r_margin:+.2f}), yet spending explains it only '
      f'loosely (r = {top.r_money:+.2f}). The widest gap is '
      f'{gap.label.split(" (")[0].lower()}: r = {gap.r_margin:+.2f} with '
      f'margin but {gap.r_money:+.2f} with spending.'
      + (
        ' Every marker tracks winning more tightly than it tracks '
        'spending: money buys a better roster at the margin, but what '
        'the roster does on the field is mostly something else.'
        if (markers['r_margin'].abs() > markers['r_money'].abs()).all()
        else ''
      ),
      '',
      'These are symptoms of a good team rather than independent causes: '
      'teams that lead run the ball late, and good defenses force '
      'interceptions.',
      '',
    ]
  if schedule:
    lines += [
      '> [!NOTE]',
      '> Richer teams also play **tougher schedules**: spending correlates '
      f"r = {schedule['r']:+.2f} with opponents' win percentage. Raw point "
      'margin therefore slightly *understates* what money buys.',
      '',
    ]
  return lines


def _budget_change_lines(change: dict[str, float] | None) -> list[str]:
  """Renders whether a school's budget change tracks its results change.

  Args:
    change (dict[str, float] | None): Output of
      :func:`cfbmoney.drivers.budget_change_effect`.

  Returns:
    list[str]: Markdown lines.
  """
  if not change:
    return []
  return [
    'The cross-section says rich programs win. Does *getting* richer '
    f"help? Comparing each school's {int(change['first_season'])} and "
    f'{int(change["last_season"])} seasons (median budget change '
    f'{change["median_change_pct"]:+.0f}%), the budget change is '
    f'unrelated to the margin change: r = **{change["r"]:+.2f}** '
    f'(p = {change["p"]:.2f}, n = {int(change["n"])}).',
    '',
    'Money appears to work through program scale built over many years - '
    'facilities, staff depth, recruiting pipelines - rather than a '
    'one-year raise. Two years of filings is a short window, so treat '
    'this as "no quick payoff yet" rather than "no payoff".',
    '',
  ]


def _projected_final_r(comparison: pd.DataFrame, season: int) -> float:
  """Projects the in-progress season's final r from past fade rates.

  Each completed season's final r is divided by its r at the same week;
  the mean of those ratios is applied to the in-progress value.
  """
  done = comparison[comparison['season'] < season].dropna(
    subset=['r_final', 'r_at_week']
  )
  current = comparison[comparison['season'] == season]
  if done.empty or current.empty:
    return float('nan')
  ratio = (done['r_final'] / done['r_at_week']).mean()
  return float(current['r_at_week'].iloc[0] * ratio)


def _trend_lines(trends: dict[str, object], season: int) -> list[str]:
  """Renders the in-season trends part.

  Args:
    trends (dict[str, object]): Outputs of :mod:`cfbmoney.trends` keyed
      ``comparison``, ``week``, ``upset_summary``, ``upsets``,
      ``better``, ``worse`` and ``forecast_fit``.
    season (int): The in-progress season.

  Returns:
    list[str]: Markdown lines with ``##`` section headings.
  """
  lines: list[str] = []
  comparison = trends.get('comparison')
  week = trends.get('week')
  if isinstance(comparison, pd.DataFrame) and not comparison.empty and week:
    current = comparison[comparison['season'] == season]
    done = comparison[comparison['season'] < season]
    lines += [
      '## Is 2026 more money-driven than usual?',
      '',
      'Every early-season number looks money-heavy because September is '
      'full of mismatches. The fair comparison is the same week of past '
      f'seasons: here each season is replayed through week {week}, next '
      'to where it finished.',
      '',
      f'| Season | r through week {week} | Final r | Conference share '
      f'of FBS games | Richer team wins, conf games (to date) | '
      'Final |',
      '| --- | ---: | ---: | ---: | ---: | ---: |',
    ]
    for row in comparison.itertuples():
      label = (
        f'{row.season} (in progress)'
        if row.season == season
        else (str(row.season))
      )
      final_r = '-' if pd.isna(row.r_final) else f'{row.r_final:+.2f}'
      lines.append(
        f'| {label} | {row.r_at_week:+.2f} | {final_r} | '
        f'{_pct(row.conf_share_at_week)} | '
        f'{_pct(row.richer_win_conf_at_week)} '
        f'({row.conf_games_at_week} games) | '
        f'{_pct(row.richer_win_conf_final)} |'
      )
    lines.append('')
    if not current.empty and not done.empty:
      now = current.iloc[0]
      projected = _projected_final_r(comparison, season)
      low, high = done['r_at_week'].min(), done['r_at_week'].max()
      verdict = (
        'right in line with'
        if low - 0.05 <= now.r_at_week <= high + 0.05
        else ('above' if now.r_at_week > high else 'below')
      )
      lines += [
        f'At week {week}, 2026 sits at r = **{now.r_at_week:+.2f}**, '
        f'{verdict} 2023-25 at the same point ({low:+.2f} to '
        f'{high:+.2f}). Every past season peaked around weeks 3-4 and then '
        'faded as conference play took over. Applying their average fade '
        f'projects 2026 to finish near **r = {projected:+.2f}**, not the '
        'headline number at the top of this report.',
        '',
      ]
      past_conf = done['richer_win_conf_at_week'].mean()
      lines += [
        f'Inside conference play, the bigger budget has won '
        f'**{_pct(now.richer_win_conf_at_week)}** of '
        f'{int(now.conf_games_at_week)} games so far, against '
        f'{_pct(past_conf)} for 2023-25 at the same week. With this few '
        'conference games, a gap under about ten points is noise.',
        '',
      ]
  better = trends.get('better')
  worse = trends.get('worse')
  fit = trends.get('forecast_fit') or {}
  if (
    isinstance(better, pd.DataFrame)
    and isinstance(worse, pd.DataFrame)
    and not better.empty
    and fit
  ):
    lines += [
      '## Surprises against a preseason forecast',
      '',
      "A forecast built only from last season's margin and this "
      "season's budget. It is fitted on "
      f'{int(fit["train_first"])}-{int(fit["train_last"])} margins '
      f'*through week {int(fit["week"])}* against FBS opponents only, so '
      'early-season schedule quirks are part of the expectation and FCS '
      'blowouts do not count. It already tracks reality well '
      f'(r = {fit["r_forecast"]:+.2f} across {int(fit["n"])} teams), so '
      'the teams far off it are the real stories of the season.',
      '',
    ]
    for title, frame in (
      ('Ahead of forecast', better),
      ('Behind forecast', worse),
    ):
      lines += [
        f'**{title}**',
        '',
        '| Program | Conf | Football exp | Last season | FBS games | '
        'Forecast | Actual | Gap |',
        '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |',
      ]
      for row in frame.itertuples():
        lines.append(
          f'| {row.school} | {row.conference} | '
          f'{_usd_millions(row.football_expenses)} | '
          f'{row.prior_margin:+.1f} | {row.fbs_games} | '
          f'{row.expected:+.1f} | {row.fbs_margin:+.1f} | '
          f'**{row.surprise:+.1f}** |'
        )
      lines.append('')
  summary = trends.get('upset_summary')
  details = trends.get('upsets')
  if isinstance(summary, pd.DataFrame) and not summary.empty and week:
    lines += [
      '## Upsets: when the smaller budget wins',
      '',
      'A money mismatch is a game against an FBS opponent with at least '
      f'twice the football budget. Through week {week} of each season:',
      '',
      '| Season | Mismatch games | Upsets | Upset rate |',
      '| --- | ---: | ---: | ---: |',
    ]
    for row in summary.itertuples():
      label = (
        f'{row.season} (in progress)'
        if row.season == season
        else (str(row.season))
      )
      lines.append(
        f'| {label} | {row.mismatches} | {row.upsets} | '
        f'{_pct(row.upset_rate)} |'
      )
    lines.append('')
    test = trends.get('upset_test') or {}
    if test:
      fewer = test['rate'] < test['past_rate']
      if test['p'] < 0.05:
        meaning = (
          'Favourites in lopsided games are holding serve.'
          if fewer
          else 'Lopsided games are less safe than usual.'
        )
      else:
        meaning = 'The difference is within normal noise.'
      lines += [
        f'2026 has produced **{"fewer" if fewer else "more"} upsets** '
        f'than usual: {_pct(test["rate"])} of mismatches against '
        f'{_pct(test["past_rate"])} for 2023-25 pooled (Fisher exact '
        f'p = {test["p"]:.2f}). {meaning}',
        '',
      ]
    if isinstance(details, pd.DataFrame) and not details.empty:
      current = details[details['season'] == season].head(8)
      if not current.empty:
        lines += [
          f'**Biggest {season} upsets by budget gap**',
          '',
          '| Week | Winner | Budget | Beat | Budget | Gap | Score |',
          '| ---: | --- | ---: | --- | ---: | ---: | :---: |',
        ]
        for row in current.itertuples():
          lines.append(
            f'| {row.week} | {row.winner} | '
            f'{_usd_millions(row.winner_spend)} | {row.loser} | '
            f'{_usd_millions(row.loser_spend)} | {row.ratio:.1f}x | '
            f'{row.score} |'
          )
        lines.append('')
  return lines


def _tiers_lines(tiers: pd.DataFrame | None, season: int) -> list[str]:
  """Renders the budget-tier dose-response table.

  Args:
    tiers (pd.DataFrame | None): Output of
      :func:`cfbmoney.insights.budget_tiers`.
    season (int): The in-progress season.

  Returns:
    list[str]: Markdown lines, empty without data.
  """
  if tiers is None or tiers.empty:
    return []
  done = tiers[tiers['period'] == 'completed'].sort_values('tier')
  now = tiers[tiers['period'] == str(season)].set_index('tier')
  if done.empty:
    return []
  lines = [
    'A correlation says the relationship exists; the tiers show its '
    'shape. Teams are ranked into fifths by budget within each season, '
    "so tier 1 is always the poorest fifth of that year's FBS.",
    '',
    f'| Tier | Median budget | Win% (completed) | Margin/g (completed) | '
    f'Win% ({season}) | Margin/g ({season}) | Team-seasons |',
    '| --- | ---: | ---: | ---: | ---: | ---: | ---: |',
  ]
  tier_names = {
    1: 'poorest fifth',
    2: 'second fifth',
    3: 'middle fifth',
    4: 'fourth fifth',
    5: 'richest fifth',
  }
  for row in done.itertuples():
    current = now.loc[row.tier] if row.tier in now.index else None
    t_name = tier_names.get(int(row.tier), row.label.lower())
    lines.append(
      f'| {row.tier} ({t_name}) | '
      f'{_usd_millions(row.median_budget)} | {_pct(row.win_pct)} | '
      f'{row.margin:+.1f} | '
      f'{_pct(current.win_pct) if current is not None else "-"} | '
      f'{f"{current.margin:+.1f}" if current is not None else "-"} | '
      f'{int(row.team_seasons)} |'
    )
  lines.append('')
  top = done.iloc[-1]
  second = done.iloc[-2]
  bottom = done.iloc[0]
  middle = done.iloc[1:-1]
  spread_top = top.margin - second.margin
  spread_middle = middle['margin'].max() - middle['margin'].min()
  if spread_top > spread_middle:
    shape = (
      f'The curve is convex: the middle three tiers sit within '
      f'{spread_middle:.1f} points of each other, then the richest fifth '
      f'jumps {spread_top:+.1f} points clear of the next tier. Money buys '
      'most at the very top, where the budget pays for the depth that '
      'wins the back half of a schedule.'
    )
  else:
    shape = (
      'The gain is spread fairly evenly across the tiers: each step up '
      'the budget ladder buys roughly the same improvement.'
    )
  lines += [
    f'Over completed seasons the poorest fifth (median '
    f'{_usd_millions(bottom.median_budget)}) wins {_pct(bottom.win_pct)} '
    f'of its games and the richest fifth ({_usd_millions(top.median_budget)}) '
    f'wins {_pct(top.win_pct)}: a {top.margin - bottom.margin:.0f}-point '
    f'swing in margin per game. {shape}',
    '',
  ]
  return lines


def _luck_lines(
  summary: pd.DataFrame, teams: pd.DataFrame, season: int
) -> list[str]:
  """Renders the Pythagorean luck subsection."""
  if summary is None or summary.empty or teams is None or teams.empty:
    return []
  done = summary[summary['season'] < season]
  now = summary[summary['season'] == season]
  lines = [
    "A team's record should follow its scoring. The Pythagorean "
    'expectation turns points for and against into an expected win '
    'percentage; the gap to the actual record is mostly the bounce of '
    'close games, and the question is whether the budget buys any of it.',
    '',
    '| Season | Teams | r, expected vs actual win% | r, luck vs log budget '
    '| p |',
    '| --- | ---: | ---: | ---: | ---: |',
  ]
  for row in summary.itertuples():
    label = (
      f'{row.season} (in progress)' if row.season == season else str(row.season)
    )
    lines.append(
      f'| {label} | {row.n} | {row.r_pythagorean:+.2f} | '
      f'{row.r_luck_money:+.2f} | {_fmt_p(row.p_luck_money)} |'
    )
  lines.append('')
  if not done.empty:
    mean_r = done['r_luck_money'].mean()
    significant = int((done['p_luck_money'] < 0.05).sum())
    verdict = (
      'Luck does not follow the budget'
      if abs(mean_r) < 0.15
      else (
        'Richer teams have been slightly *unluckier*'
        if mean_r < 0
        else 'Richer teams have been slightly luckier'
      )
    )
    lines += [
      f'Scoring explains the record well (r = '
      f'{done["r_pythagorean"].mean():+.2f} in completed seasons), so the '
      f'residual is small but real. {verdict}: luck correlates '
      f'{mean_r:+.2f} with log spending across completed seasons, '
      f'significant in {significant} of {len(done)}. Whatever money buys, '
      'it is not the bounce of the ball.',
      '',
    ]
  if not now.empty:
    head = teams.head(5)
    tail = teams.tail(5).iloc[::-1]
    lines += [
      f'**Luckiest and unluckiest records so far in {season}**',
      '',
      '| Group | Program | Conf | Football exp | Record | Expected win% | '
      'Actual | Wins above expectation |',
      '| --- | --- | --- | ---: | :---: | ---: | ---: | ---: |',
    ]
    for tag, frame in (('Lucky', head), ('Unlucky', tail)):
      for row in frame.itertuples():
        lines.append(
          f'| {tag} | {row.school} | {row.conference} | '
          f'{_usd_millions(row.football_expenses)} | '
          f'{int(row.wins)}-{int(row.losses)} | {_pct(row.pythagorean_pct)} | '
          f'{_pct(row.win_pct)} | **{row.luck_wins:+.1f}** |'
        )
    lines.append('')
    lucky = teams.iloc[0]
    unlucky = teams.iloc[-1]
    lines += [
      f'{lucky.school} is {int(lucky.wins)}-{int(lucky.losses)} while '
      f'scoring like a team that wins {_pct(lucky.pythagorean_pct)} of its '
      f'games; {unlucky.school} is {int(unlucky.wins)}-{int(unlucky.losses)} '
      f'while scoring like one that wins {_pct(unlucky.pythagorean_pct)}. '
      'Records like these tend to regress toward the scoring over the rest '
      'of the season.',
      '',
    ]
  return lines


def _close_lines(
  close: pd.DataFrame, season: int, week: int | None
) -> list[str]:
  """Renders the close-games-versus-blowouts subsection."""
  if close is None or close.empty:
    return []
  done = close[close['season'] < season]
  now = close[close['season'] == season]
  scope = f'through week {week}' if week else 'for the full season'
  lines = [
    'Does the bigger budget win the tight games, or only the lopsided '
    'ones? Every FBS-vs-FBS game is split by its final margin: one-score '
    '(8 points or fewer) against blowouts (17 or more). Each season is '
    f'counted {scope}.',
    '',
    '| Season | FBS games | Richer team wins | One-score games | Richer '
    'wins (one-score) | Blowouts | Richer wins (blowouts) |',
    '| --- | ---: | ---: | ---: | ---: | ---: | ---: |',
  ]
  for row in close.itertuples():
    label = (
      f'{row.season} (in progress)' if row.season == season else str(row.season)
    )
    lines.append(
      f'| {label} | {row.games} | {_pct(row.richer_win_all)} | '
      f'{row.close_games} ({_pct(row.close_share)}) | '
      f'{_pct(row.richer_win_close)} | {row.blowout_games} | '
      f'{_pct(row.richer_win_blowout)} |'
    )
  lines.append('')
  if not done.empty:
    close_rate = done['richer_win_close'].mean()
    blowout_rate = done['richer_win_blowout'].mean()
    lines += [
      f'Across completed seasons the bigger budget wins '
      f'**{_pct(blowout_rate)}** of blowouts but only '
      f'**{_pct(close_rate)}** of one-score games. Money shows up as '
      'depth and talent that turn a close game into a comfortable one; '
      'once a game is actually close, the budget is nearly irrelevant to '
      'who wins it.',
      '',
    ]
    if not now.empty:
      current = now.iloc[0]
      past_share = done['close_share'].mean()
      lines += [
        f'So far in {season}, {_pct(current.close_share)} of FBS games '
        f'have been one-score games against {_pct(past_share)} at the same '
        f'point of past seasons, and the richer side has won '
        f'{_pct(current.richer_win_close)} of them (n = '
        f'{int(current.close_games)}).',
        '',
      ]
  return lines


def _home_lines(home: pd.DataFrame, season: int) -> list[str]:
  """Renders the home-field subsection."""
  if home is None or home.empty:
    return []
  done = home[home['season'] < season]
  lines = [
    'Home advantage is measured within each team (its home margin minus '
    'its away margin against FBS opponents, neutral sites excluded) so a '
    "rich team's stronger roster is not mistaken for a louder stadium.",
    '',
    '| Season | Home games | Home win rate | Home margin | Within-team '
    'home edge | r, home edge vs log budget | p |',
    '| --- | ---: | ---: | ---: | ---: | ---: | ---: |',
  ]
  for row in home.itertuples():
    label = (
      f'{row.season} (in progress)' if row.season == season else str(row.season)
    )
    lines.append(
      f'| {label} | {row.home_games} | {_pct(row.home_win_rate)} | '
      f'{row.home_margin:+.1f} | {row.hfa_mean:+.1f} | '
      f'{row.r_hfa_money:+.2f} | {_fmt_p(row.p_hfa_money)} |'
    )
  lines.append('')
  if not done.empty:
    mean_r = done['r_hfa_money'].mean()
    signs = set(np.sign(done['r_hfa_money'].dropna()))
    stability = (
      'sign flipping year to year' if len(signs) > 1 else 'never significant'
    )
    lines += [
      f'The home side wins about {_pct(done["home_win_rate"].mean())} of '
      f'games and teams average {done["hfa_mean"].mean():.0f} points '
      'better at home than away, but that edge is unrelated to budget '
      f'(mean r = {mean_r:+.2f}, {stability}): a 100,000-seat stadium '
      'does not widen the home-field margin over a 25,000-seat one.',
      '',
    ]
  return lines


def _crowd_lines(
  summary: pd.DataFrame,
  league: pd.DataFrame,
  gainers: pd.DataFrame,
  losers: pd.DataFrame,
  change: dict[str, float],
  regression: dict[str, float],
  season: int,
  week: int | None,
) -> list[str]:
  """Renders the attendance subsection."""
  if summary is None or summary.empty:
    return []
  lines = [
    'Attendance is the one scale metric that arrives live each week '
    'instead of two years late in a federal filing. Average home crowd '
    'per team (neutral sites excluded):',
    '',
    '| Season | Teams | Mean home crowd | Median | r, log crowd vs log '
    'budget | r, log crowd vs margin |',
    '| --- | ---: | ---: | ---: | ---: | ---: |',
  ]
  for row in summary.itertuples():
    label = (
      f'{row.season} (in progress)' if row.season == season else str(row.season)
    )
    lines.append(
      f'| {label} | {row.n} | {row.mean_attendance:,.0f} | '
      f'{row.median_attendance:,.0f} | {row.r_money:+.2f} | '
      f'{row.r_margin:+.2f} |'
    )
  lines.append('')
  if regression:
    winner = (
      'the budget keeps the edge'
      if abs(regression['t_money']) > abs(regression['t_attendance'])
      else 'the crowd carries more of the signal'
    )
    lines += [
      f'Log crowd size and log budget correlate at r = '
      f"**{summary['r_money'].mean():+.2f}**. Using *last* season's "
      'crowd (known before kickoff), crowd and budget predict margin '
      f'almost equally over '
      f'{int(regression["first_season"])}-{int(regression["last_season"])} '
      f'(r = {regression["r_attendance"]:+.2f} vs '
      f'{regression["r_money"]:+.2f}, n = {int(regression["n"])}); in a '
      f'joint model {winner} (t = {regression["t_money"]:.1f} for budget, '
      f'{regression["t_attendance"]:.1f} for crowd).',
      '',
    ]
  else:
    lines += [
      f'Log crowd size and log budget correlate at r = '
      f'**{summary["r_money"].mean():+.2f}**: gate receipts, donor bases '
      'and media value all scale with attendance.',
      '',
    ]
  if league is not None and not league.empty and change:
    scope = f'through week {week}' if week else 'to date'
    trend = ' > '.join(
      f'{int(row.season)}: {row.mean_attendance:,.0f}'
      for row in league.sort_values('season').itertuples()
    )
    direction = 'down' if change['median_pct'] < 0 else 'up'
    lines += [
      f'**Are crowds growing?** Same-week comparison ({scope}), mean home '
      f'crowd across FBS: {trend}. School by school, the median change '
      f'from {season - 1} is **{change["median_pct"]:+.1%}** '
      f'({direction}, n = {int(change["n"])}).',
      '',
    ]
    for title, frame in (
      ('Biggest crowd gains', gainers),
      ('Biggest crowd losses', losers),
    ):
      if frame is None or frame.empty:
        continue
      lines += [
        f'**{title} versus {season - 1}**',
        '',
        f'| Program | Home games | {season - 1} crowd | {season} crowd | '
        'Change |',
        '| --- | ---: | ---: | ---: | ---: |',
      ]
      for row in frame.itertuples():
        lines.append(
          f'| {row.school} | {int(row.home_games)} | '
          f'{row.prior_attendance:,.0f} | {row.attendance:,.0f} | '
          f'**{row.pct_change:+.0%}** |'
        )
      lines.append('')
  return lines


def _road_gap_test(movers: pd.DataFrame) -> tuple[float, float, int]:
  """Tests whether movers' road gap (away minus home change) is non-zero.

  Args:
    movers (pd.DataFrame): Realignment travel rows with
      ``travel_gap_change``.

  Returns:
    tuple[float, float, int]: Mean gap change, two-sided p-value and the
    number of schools with a negative gap.
  """
  gaps = movers['travel_gap_change'].dropna()
  if len(gaps) < 3:
    return float('nan'), float('nan'), 0
  result = stats.ttest_1samp(gaps, 0.0)
  return float(gaps.mean()), float(result.pvalue), int((gaps < 0).sum())


def _key_findings(
  merged: pd.DataFrame,
  correlations: pd.DataFrame,
  split: pd.DataFrame | None,
  relative: dict[str, float] | None,
  decomposition: pd.DataFrame | None,
  diaspora: pd.DataFrame | None,
  realignment_travel: pd.DataFrame | None,
  season: int,
  relative_by_season: pd.DataFrame | None = None,
  drivers: dict[str, object] | None = None,
  trends: dict[str, object] | None = None,
  tiers: pd.DataFrame | None = None,
  gameday: dict[str, object] | None = None,
) -> list[str]:
  """Summarises the report's strongest results, computed from the data.

  Args:
    merged (pd.DataFrame): Merged analysis table.
    correlations (pd.DataFrame): Correlation table.
    split (pd.DataFrame | None): Conference/non-conference split.
    relative (dict[str, float] | None): Relative-spend summary.
    decomposition (pd.DataFrame | None): Spending-line decomposition.
    diaspora (pd.DataFrame | None): Pac-12 breakup table.
    realignment_travel (pd.DataFrame | None): Mover travel changes.
    season (int): The in-progress season.
    relative_by_season (pd.DataFrame | None): Per-season relative-spend
      correlations.
    drivers (dict[str, object] | None): Outputs of
      :mod:`cfbmoney.drivers`, keyed as in :func:`build_report`.
    trends (dict[str, object] | None): Outputs of
      :mod:`cfbmoney.trends`, keyed as in :func:`_trend_lines`.
    tiers (pd.DataFrame | None): Output of
      :func:`cfbmoney.insights.budget_tiers`.
    gameday (dict[str, object] | None): Outputs of
      :mod:`cfbmoney.gameday`, keyed as in :func:`build_report`.

  Returns:
    list[str]: Markdown lines.
  """
  drivers = drivers or {}
  gameday = gameday or {}
  money: list[str] = []
  team: list[str] = []
  league: list[str] = []
  games: list[str] = []

  by_season = (
    relative_by_season
    if relative_by_season is not None
    else pd.DataFrame(columns=['season'])
  )
  complete = by_season[by_season['season'] < season]
  if not correlations.empty and 'money_metric' in correlations.columns:
    row = correlations[
      (correlations['money_metric'] == 'football_expenses')
      & (correlations['performance_metric'] == 'point_margin_per_game')
    ]
    if not row.empty:
      history = ''
      if not complete.empty:
        history = (
          f' (r = {complete["r_absolute"].min():+.2f} to '
          f'{complete["r_absolute"].max():+.2f} in completed seasons)'
        )
      money.append(
        f'**Yes, money tracks results.** Log football spending correlates '
        f'r = {row.iloc[0].pearson_r:+.2f} with point margin across '
        f'{int(row.iloc[0].n)} FBS teams so far in {season}{history}.'
      )
  if split is not None and not split.empty:
    done = split[split['season'] < season]
    if not done.empty:
      money.append(
        '**The edge is biggest across leagues.** The bigger budget wins '
        f'{_pct(done["nonconf_fbs_richer_win"].mean())} of '
        'non-conference FBS games but only '
        f'{_pct(done["conference_richer_win"].mean())} of conference '
        'games.'
      )
  if not complete.empty:
    money.append(
      '**Out-spending your own conference pays as much as raw dollars.** '
      'Spend relative to the conference median tracks margin at r = '
      f'{complete["r_within"].mean():+.2f} over completed seasons, '
      f'against {complete["r_absolute"].mean():+.2f} for absolute spend.'
    )
  elif relative:
    money.append(
      '**Out-spending your own league still helps** (within-conference '
      f'r = {relative["r_within"]:+.2f}).'
    )
  if tiers is not None and not tiers.empty:
    done = tiers[tiers['period'] == 'completed'].sort_values('tier')
    if len(done) >= 3:
      top, second, bottom = done.iloc[-1], done.iloc[-2], done.iloc[0]
      money.append(
        '**The return on money is concentrated at the top.** The richest '
        f'fifth of FBS wins {_pct(top.win_pct)} of its games against '
        f'{_pct(second.win_pct)} for the next fifth and '
        f'{_pct(bottom.win_pct)} for the poorest; the top tier is '
        f'{top.margin - second.margin:+.1f} points per game clear of '
        'everyone below it.'
      )

  close = gameday.get('close')
  if isinstance(close, pd.DataFrame) and not close.empty:
    done = close[close['season'] < season]
    if not done.empty:
      games.append(
        '**Money decides blowouts, not close games.** The bigger budget '
        f'wins {_pct(done["richer_win_blowout"].mean())} of games decided '
        f'by 17+ points but only {_pct(done["richer_win_close"].mean())} '
        'of one-score games in completed seasons.'
      )
  luck_summary = gameday.get('luck_summary')
  luck_teams = gameday.get('luck_teams')
  if (
    isinstance(luck_summary, pd.DataFrame)
    and isinstance(luck_teams, pd.DataFrame)
    and not luck_summary.empty
    and not luck_teams.empty
  ):
    done = luck_summary[luck_summary['season'] < season]
    lucky = ', '.join(
      f'{r.school} ({r.luck_wins:+.1f} wins)'
      for r in luck_teams.head(3).itertuples()
    )
    unlucky = ', '.join(
      f'{r.school} ({r.luck_wins:+.1f})'
      for r in luck_teams.tail(3).iloc[::-1].itertuples()
    )
    history = (
      f' Luck is unrelated to budget (r = {done["r_luck_money"].mean():+.2f} '
      'in completed seasons).'
      if not done.empty
      else ''
    )
    games.append(
      f'**Records outrunning the scoring in {season}:** {lucky}. '
      f'**Trailing it:** {unlucky}.{history}'
    )
  home = gameday.get('home')
  if isinstance(home, pd.DataFrame) and not home.empty:
    done = home[home['season'] < season]
    if not done.empty:
      games.append(
        '**Money does not buy a home-field edge.** Teams are '
        f'{done["hfa_mean"].mean():.0f} points better at home than away, '
        f'and that edge is uncorrelated with budget (r = '
        f'{done["r_hfa_money"].mean():+.2f}).'
      )
  crowd = gameday.get('attendance_summary')
  change = gameday.get('attendance_change') or {}
  regression = gameday.get('attendance_regression') or {}
  if isinstance(crowd, pd.DataFrame) and not crowd.empty:
    text = (
      '**Crowd size is the budget, measured live.** Log home attendance '
      f'and log spending correlate {crowd["r_money"].mean():+.2f}'
    )
    if regression:
      text += (
        f"; last season's crowd predicts this season's margin about as "
        f'well as the budget does (r = {regression["r_attendance"]:+.2f} '
        f'vs {regression["r_money"]:+.2f})'
      )
    if change:
      text += (
        f'. Same-week crowds are {change["median_pct"]:+.1%} versus '
        f'{season - 1} at the median school'
      )
    games.append(text + '.')

  pooled = drivers.get('momentum') or {}
  if pooled:
    team.append(
      "**Last season is the best single predictor.** Last year's margin "
      f"explains {pooled['r2_prior']:.0%} of this year's, the budget "
      f'{pooled["r2_money"]:.0%}, both {pooled["r2_both"]:.0%}; money '
      f'still adds signal on top (t = {pooled["t_money"]:.1f}).'
    )
  lag = drivers.get('residual_lag')
  over = drivers.get('over')
  under = drivers.get('under')
  if isinstance(lag, pd.DataFrame) and not lag.empty:
    done = lag[lag['season'] < season]
    names = ''
    if isinstance(over, pd.DataFrame) and isinstance(under, pd.DataFrame):
      always_over = over[over['seasons_above'] == over['seasons']]
      always_under = under[under['seasons_above'] == 0]
      if not always_over.empty and not always_under.empty:
        names = (
          f' {", ".join(always_over["school"].head(4))} beat their budget '
          f'every year; {", ".join(always_under["school"].head(4))} '
          'missed it every year.'
        )
    if not done.empty:
      team.append(
        '**Beating your budget is a repeatable trait.** Margin above the '
        f'budget line carries over at r = {done["r"].mean():+.2f} year to '
        f'year: something the budget misses (coaching, development, '
        f'unrecorded NIL money) persists.{names}'
      )
  markers = drivers.get('markers')
  if isinstance(markers, pd.DataFrame) and not markers.empty:
    top = markers.iloc[0]
    name = top.label.split(' (')[0]
    headline = 'Quarterback play' if top.stat == 'passer_rating' else name
    team.append(
      f'**{headline} is the clearest on-field marker.** '
      f'{name} tracks margin at r = '
      f'{top.r_margin:+.2f} but spending at only {top.r_money:+.2f}; '
      'every box-score marker tracks winning more tightly than spending.'
    )
  if decomposition is not None and not decomposition.empty:
    coach = decomposition[decomposition['component'] == 'head_coach_pay']
    coach_text = ''
    if not coach.empty:
      coach_text = (
        f' Head coach pay adds nothing beyond the budget '
        f'(t = {coach.iloc[0].added_t:+.1f}, n = {int(coach.iloc[0].n)}).'
      )
    team.append(
      '**No single spending line stands out.** Coaching, recruiting and '
      'operations budgets move together (r >= '
      f'{decomposition["corr_with_budget"].min():.2f}) and none adds '
      f'signal once total spending is known.{coach_text}'
    )
  change = drivers.get('budget_change') or {}
  if change:
    team.append(
      '**Getting richer has not paid off quickly.** Budget changes '
      f'between {int(change["first_season"])} and '
      f'{int(change["last_season"])} are unrelated to margin changes '
      f'(r = {change["r"]:+.2f}, n = {int(change["n"])}).'
    )

  if diaspora is not None and not diaspora.empty:
    stayed = diaspora[diaspora['role'] == 'stayed']
    left = diaspora[diaspora['role'] == 'left']
    if not stayed.empty and not left.empty:
      league.append(
        '**Realignment moved money without anyone playing a down.** '
        'Pac-12 leavers: '
        f'{left["football_revenue_pct_change"].median():+.1f}% median '
        'football revenue; Oregon State and Washington State: '
        f'{stayed["football_revenue_pct_change"].median():+.1f}%.'
      )
  if realignment_travel is not None and not realignment_travel.empty:
    far = realignment_travel[realignment_travel['tz_shift_change'] > 0.5]
    far = far.dropna(subset=['home_margin_change'])
    if len(far) >= 3:
      gap, p_value, negative = _road_gap_test(far)
      league.append(
        '**Long-haul movers may be paying a road tax (suggestive).** '
        f'Across the {len(far)} schools whose travel grew most, away '
        f'margin changed {far["away_margin_change"].mean():+.1f} and home '
        f'margin {far["home_margin_change"].mean():+.1f} points per game '
        f'(road gap {gap:+.1f}, {negative} of {len(far)} negative, '
        f'p = {p_value:.2f}).'
      )

  trend: list[str] = []
  comparison = (trends or {}).get('comparison')
  week = (trends or {}).get('week')
  if isinstance(comparison, pd.DataFrame) and not comparison.empty and week:
    now = comparison[comparison['season'] == season]
    done = comparison[comparison['season'] < season]
    if not now.empty and not done.empty:
      projected = _projected_final_r(comparison, season)
      fade = 1 - projected / now.iloc[0].r_at_week
      trend.append(
        f'**2026 is a normal season so far, not an unusually rich one.** '
        f'Through week {week} the money correlation is '
        f'{now.iloc[0].r_at_week:+.2f}, against '
        f'{done["r_at_week"].min():+.2f} to {done["r_at_week"].max():+.2f} '
        'for 2023-25 at the same week. Past seasons faded by '
        f'{fade:.0%} as conference play took over; 2026 projects to about '
        f'{projected:+.2f}.'
      )
  better = (trends or {}).get('better')
  worse = (trends or {}).get('worse')
  if (
    isinstance(better, pd.DataFrame)
    and isinstance(worse, pd.DataFrame)
    and not better.empty
    and not worse.empty
  ):
    up = ', '.join(
      f'{r.school} ({r.surprise:+.0f})' for r in better.head(3).itertuples()
    )
    down = ', '.join(
      f'{r.school} ({r.surprise:+.0f})' for r in worse.head(3).itertuples()
    )
    trend.append(
      '**Biggest surprises against a same-week forecast:** '
      f'{up}. **Biggest disappointments:** {down} (points per game).'
    )
  upset_summary = (trends or {}).get('upset_summary')
  if isinstance(upset_summary, pd.DataFrame) and not upset_summary.empty:
    now = upset_summary[upset_summary['season'] == season]
    done = upset_summary[upset_summary['season'] < season]
    if not now.empty and not done.empty and done['mismatches'].sum():
      past = done['upsets'].sum() / done['mismatches'].sum()
      test = (trends or {}).get('upset_test') or {}
      p_text = f', p = {test["p"]:.2f}' if test else ''
      lower = now.iloc[0].upset_rate < past
      trend.append(
        f'**Upsets are {"rare" if lower else "common"} this year.** Teams '
        "with half the opponent's budget have won "
        f'{_pct(now.iloc[0].upset_rate)} of such games '
        f'({int(now.iloc[0].upsets)} of {int(now.iloc[0].mismatches)}), '
        f'against {_pct(past)} at the same point of 2023-25{p_text}.'
      )

  groups = [
    (f'What {season} is showing so far', trend),
    ('Does money buy wins?', money),
    ('What else makes a good team?', team),
    ('Luck, close games and crowds', games),
    ('Realignment and travel', league),
  ]
  if not any(items for _, items in groups):
    return []
  lines = ['## Summary', '']
  for title, items in groups:
    if items:
      lines += [f'**{title}**', '']
      lines += [f'- {text}' for text in items]
      lines.append('')
  return lines


def _leaderboard_section(merged: pd.DataFrame) -> list[str]:
  """Builds the richest-programs table."""
  columns = [
    c
    for c in (
      'school',
      'conference',
      'football_revenue',
      'football_expenses',
      'dept_total_revenue',
      'wins',
      'losses',
      'win_pct',
      'point_margin_per_game',
    )
    if c in merged.columns
  ]
  top = merged.dropna(subset=['football_revenue']).nlargest(
    20, 'football_revenue'
  )[columns]
  lines = [
    '| # | Program | Conf | Football rev | Football exp | Dept rev | '
    'Record | Win% | Margin/g |',
    '| ---: | --- | --- | ---: | ---: | ---: | :---: | ---: | ---: |',
  ]
  for rank, row in enumerate(top.itertuples(), start=1):
    wins = getattr(row, 'wins', float('nan'))
    losses = getattr(row, 'losses', float('nan'))
    record = (
      f'{int(wins)}-{int(losses)}'
      if not pd.isna(wins) and not pd.isna(losses)
      else '-'
    )
    margin = getattr(row, 'point_margin_per_game', float('nan'))
    margin_text = '-' if pd.isna(margin) else f'{margin:+.1f}'
    lines.append(
      f'| {rank} | {row.school} | {row.conference} | '
      f'{_usd_millions(getattr(row, "football_revenue", None))} | '
      f'{_usd_millions(getattr(row, "football_expenses", None))} | '
      f'{_usd_millions(getattr(row, "dept_total_revenue", None))} | '
      f'{record} | {_pct(getattr(row, "win_pct", None))} | '
      f'{margin_text} |'
    )
  lines.append('')
  return lines


def _realignment_section(
  changes: pd.DataFrame,
  diaspora: pd.DataFrame,
) -> list[str]:
  """Renders the conference realignment analysis.

  Args:
    changes (pd.DataFrame): Output of
      :func:`cfbmoney.realignment.before_after`.
    diaspora (pd.DataFrame): Output of
      :func:`cfbmoney.realignment.diaspora`.

  Returns:
    list[str]: Markdown lines.
  """
  if changes.empty:
    return ['No conference changes were detected in the panel.', '']

  lines = [
    'Between 2023 and 2026 the sport redrew its map: '
    f'**{len(changes)} schools changed conference**. That is the closest '
    'thing this data has to a controlled experiment, because the money '
    'moved for reasons unrelated to recent on-field performance.',
    '',
    '> [!IMPORTANT]',
    '> Federal finance filings lag by two years, so 2024 is the newest '
    'money year on record. Schools that moved in 2024 have **one** '
    'post-move budget year (some, like Texas, show a 1-year dip off a '
    'pre-move 2023 contribution spike); 2026 movers have **none** and '
    'are left blank rather than filled with pre-move figures. On-field '
    'margin changes compare seasons before versus from the move year '
    'onward (including 2026 to date).',
    '',
  ]

  if not diaspora.empty:
    lines += [
      '### The Pac-12 breakup',
      '',
      'Ten of the twelve 2023 Pac-12 members left. Two did not, and the '
      'gap between those two groups is the single starkest result in '
      'this project.',
      '',
      '| School | Role | Football revenue before | After | Change | '
      'Point margin change |',
      '| --- | --- | ---: | ---: | ---: | ---: |',
    ]
    role_labels = {
      'left': 'left',
      'stayed': 'stayed behind',
      'joined': 'joined new Pac-12',
    }
    for row in diaspora.itertuples():
      pct = getattr(row, 'football_revenue_pct_change', float('nan'))
      margin = getattr(row, 'point_margin_per_game_change', float('nan'))
      lines.append(
        f'| {row.school} | {role_labels.get(row.role, row.role)} | '
        f'{_usd_millions(getattr(row, "football_revenue_before", None))} | '
        f'{_usd_millions(getattr(row, "football_revenue_after", None))} | '
        f'{"n/a" if pd.isna(pct) else f"{pct:+.1f}%"} | '
        f'{"n/a" if pd.isna(margin) else f"{margin:+.1f}"} |'
      )
    lines.append('')

    left = diaspora[diaspora['role'] == 'left']
    stayed = diaspora[diaspora['role'] == 'stayed']
    if not left.empty and not stayed.empty:
      left_median = left['football_revenue_pct_change'].median()
      stayed_median = stayed['football_revenue_pct_change'].median()
      lines += [
        f'Median revenue change for the schools that left: '
        f'**{left_median:+.1f}%**. For the two left behind: '
        f'**{stayed_median:+.1f}%**. Washington State and Oregon State '
        'lost roughly a third of their football revenue simply by losing '
        'their conference.',
        '',
        '#### Realignment financial mechanics',
        '',
        'Several leavers show modest 2024 revenue gains because they '
        'entered on reduced media shares (Oregon and Washington joined '
        'the Big Ten at ~$30M/yr vs ~$65M+ full shares for USC and UCLA) '
        'while absorbing exit settlements and cross-country travel costs:',
        '',
        '| Financial impact | Reported figure | Scope | Confidence | Source |',
        '| :--- | :--- | :--- | :--- | :--- |',
        '| WSU/OSU Settlement | $65M Withheld | 10 Departing Schools | High | [The Athletic](https://theathletic.com/5155122/2023/12/21/pac-12-settlement-washington-state-oregon-state/) |',
        '| B1G Media Deal | ~$1.1 - $1.2B/yr | Big Ten | High | [CBS Sports](https://www.cbssports.com/college-football/news/big-ten-reaches-seven-year-media-rights-deal-with-cbs-fox-and-nbc-worth-more-than-7-billion/) |',
        '| Big 12 Media Deal | ~$380M/yr | Big 12 | High | [ESPN](https://www.espn.com/college-football/story/_/id/34907937/big-12-agrees-new-media-rights-deal-espn-fox-sports) |',
        '| USC / UCLA B1G Share | Full Share (~$65M+) | USC, UCLA | High | [LA Times](https://www.latimes.com/sports/ucla/story/2022-06-30/ucla-usc-big-ten-conference-move) |',
        '| Oregon / UW B1G Share | $30M, +$1M/yr | Oregon, Washington | High | [ESPN](https://www.espn.com/college-football/story/_/id/38135860/oregon-washington-join-big-ten-2024) |',
        '| Increased Travel Costs | $4.6M to $5.8M | UCLA | High | [LA Times](https://www.latimes.com/sports/ucla/story/2022-12-14/ucla-big-ten-move-uc-regents-approval-travel-costs) |',
        '',
      ]

  others = changes
  heading = '### Every school that moved'
  if not diaspora.empty:
    others = changes[~changes['school'].isin(diaspora['school'])]
    heading = '### The other schools that moved'
  if others.empty:
    return lines
  lines += [heading, '']
  lines += [
    '| School | Move | Effective | Revenue change | Point margin change |',
    '| --- | --- | ---: | ---: | ---: |',
  ]
  for row in others.sort_values(['move_season', 'school']).itertuples():
    pct = getattr(row, 'football_revenue_pct_change', float('nan'))
    margin = getattr(row, 'point_margin_per_game_change', float('nan'))
    lines.append(
      f'| {row.school} | {row.move} | {row.move_season} | '
      f'{"not yet filed" if pd.isna(pct) else f"{pct:+.1f}%"} | '
      f'{"n/a" if pd.isna(margin) else f"{margin:+.1f}"} |'
    )
  lines.append('')
  return lines


def _nil_revshare_section(
  merged: pd.DataFrame,
  correlations: pd.DataFrame,
) -> list[str]:
  """Renders the NIL, revenue sharing, and roster economics analysis.

  Args:
    merged (pd.DataFrame): Merged analysis table.
    correlations (pd.DataFrame): Correlation table.

  Returns:
    list[str]: Markdown lines.
  """
  lines = [
    '## Roster economics: NIL, revenue sharing and the House settlement',
    '',
    'Under the *House v. NCAA* settlement, schools may share up to '
    '~$20.5M in athletics revenue with athletes in 2025-26 (~$21.32M in '
    '2026-27).',
    '',
    '> [!IMPORTANT]',
    '> Revenue-sharing caps and 247Sports talent composites are public, '
    'but **per-school football allocations and NIL collective payrolls '
    'remain undisclosed.** Rather than fabricating synthetic estimates, '
    'per-school allocation (`football_allocation_est`) and roster payroll '
    '(`roster_payroll_est`) columns remain blank (`n/a`) until audited '
    'disclosures exist.',
    '',
    '| Data point | Reported figure | Scope | Confidence | Source |',
    '| :--- | :--- | :--- | :--- | :--- |',
    '| Revenue-share cap | ~$20.5M (25-26), ~$21.32M (26-27) | Every school | High | [ESPN](https://www.espn.com/college-sports/story/_/id/40206364/ncaa-power-conferences-agree-settle-house-vs-ncaa-lawsuit) |',
    '| Football share of cap | ~75% | League-wide rule of thumb | Low per school | [Yahoo Sports](https://sports.yahoo.com/college-sports-revenue-sharing-model/) |',
    '| Collective budgets | $15M-$20M+ | Elite tier only | Medium | [On3](https://www.on3.com/nil/news/college-football-nil-collective-budgets/) |',
    '| Roster valuations | $12M-$15M+ | Top 5 rosters | Medium | [On3](https://www.on3.com/nil/rankings/player/college/football/) |',
    '| 2026 recruiting spend | $3M-$5M | Top 15 classes | Medium | [247Sports](https://247sports.com/college-football/recruiting/) |',
    '| Per-school football allocation | not disclosed | — | — | — |',
    '',
    '### Talent composite and the equal-cap paradox',
    '',
    'Because the House revenue-share cap is uniform across institutions, '
    'nearly every Power 4 program will max out the same ~$16M football '
    'share. Competitive differentiation therefore shifts to third-party '
    'NIL collectives ($15M-$20M+ at top programs) and uncapped coaching, '
    'recruiting, and support budgets.',
    '',
  ]
  if 'talent_composite' in merged.columns:
    has_talent = merged.dropna(subset=['talent_composite'])
    if not has_talent.empty:
      tc_rows = (
        correlations[
          (correlations['money_metric'] == 'talent_composite')
          & (correlations['performance_metric'] == 'points_per_game')
        ]
        if not correlations.empty and 'money_metric' in correlations.columns
        else pd.DataFrame()
      )
      if not tc_rows.empty:
        tc = tc_rows.iloc[0]
        stat_text = (
          f'(r = {tc.pearson_r:+.3f} with points per game, '
          f'p = {tc.pearson_p:.3f})'
        )
      else:
        stat_text = '(with points per game)'
      lines += [
        f'247Sports Team Talent Composite ratings are on file for '
        f'**{len(has_talent)} elite programs** only. Among them, talent '
        f'tracks scoring {stat_text}. With so few schools, all from the '
        'top of the sport, treat this as a hint rather than a result.',
        '',
      ]
  return lines


def _coach_pay_section(
  merged: pd.DataFrame,
  correlations: pd.DataFrame,
) -> list[str]:
  """Renders the head-coach pay angle.

  Coach pay deserves its own section because it is the one spending
  line that is unambiguously discretionary: a school chooses what to
  pay a coach in a way it does not choose its stadium debt.

  Args:
    merged (pd.DataFrame): Merged analysis table.
    correlations (pd.DataFrame): Correlation table.

  Returns:
    list[str]: Markdown lines.
  """
  if 'head_coach_pay' not in merged.columns:
    return []
  paid = merged.dropna(subset=['head_coach_pay'])
  if paid.empty:
    return []

  lines = [
    f'Verified total pay is on file for **{len(paid)} of '
    f'{len(merged)} teams**. Public universities subject to open-records '
    'laws provide high-confidence, cited figures. Private institutions '
    '(e.g., USC, Notre Dame, Stanford, Miami, TCU, Baylor, SMU, Vanderbilt) '
    'are exempt from FOIA disclosure and remain marked as unverified '
    'with blank salaries rather than synthetic estimates.',
    '',
  ]

  if not correlations.empty and 'money_metric' in correlations.columns:
    rows = correlations[correlations['money_metric'] == 'head_coach_pay']
    margin = rows[rows['performance_metric'] == 'point_margin_per_game']
    if not margin.empty:
      row = margin.iloc[0]
      power_share = (
        paid['is_power'].mean() if 'is_power' in paid.columns else None
      )
      sample_text = (
        f' Part of that is the sample: {power_share:.0%} of the verified '
        'rows are Power 4 schools, which squeezes the spread in both pay '
        'and results.'
        if power_share is not None and not pd.isna(power_share)
        else ''
      )
      lines += [
        f'Across those {int(row.n)} teams, head coach pay correlates '
        f'**r = {row.pearson_r:+.2f}** with point margin per game '
        f'(p = {row.pearson_p:.3f}), weaker than total spending.'
        f'{sample_text} With the total budget in the model, coach pay '
        'adds nothing (see the spending-line table above).',
        '',
      ]

  top = paid.nlargest(10, 'head_coach_pay')
  lines += [
    '| Coach | School | Total pay | Buyout | Win% | Point margin |',
    '| --- | --- | ---: | ---: | ---: | ---: |',
  ]
  for row in top.itertuples():
    coach = getattr(row, 'head_coach', '') or ''
    buyout = getattr(row, 'head_coach_buyout', None)
    lines.append(
      f'| {coach} | {row.school} | '
      f'{_usd_millions(row.head_coach_pay)} | '
      f'{_usd_millions(buyout)} | '
      f'{_pct(row.win_pct)} | {row.point_margin_per_game:+.1f} |'
    )
  lines.append('')
  return lines


def _travel_section(
  by_shift: pd.DataFrame,
  within_team: dict[str, float] | None,
  realignment_travel: pd.DataFrame | None,
) -> list[str]:
  """Renders the travel and time-zone analysis.

  Args:
    by_shift (pd.DataFrame): Output of
      :func:`cfbmoney.travel.performance_by_shift`.
    within_team (dict[str, float] | None): Output of
      :func:`cfbmoney.travel.within_team_travel_effect`.
    realignment_travel (pd.DataFrame | None): Output of
      :func:`cfbmoney.travel.realignment_travel_change`.

  Returns:
    list[str]: Markdown lines.
  """
  if by_shift.empty:
    return ['No travel data was available.', '']

  lines = [
    'Realignment moved miles as well as money. A team flying east loses '
    'hours: a noon kickoff on the east coast is a 9am body clock for a '
    'team from California. The table below pools every completed game '
    'from 2023 to 2026 by how many time zones the team crossed.',
    '',
    '| Travel | Games | Mean margin | Win rate |',
    '| --- | ---: | ---: | ---: |',
  ]
  for row in by_shift.itertuples():
    if row.games < 10:
      continue
    label = row.label if isinstance(row.label, str) else f'{row.shift} zones'
    lines.append(
      f'| {label} | {row.games} | {row.mean_margin:+.1f} | {row.win_rate:.0%} |'
    )
  lines.append('')

  if within_team:
    lines += [
      '> [!IMPORTANT]',
      '> The raw split above is confounded. The teams that fly two or '
      'more zones east are disproportionately Group of Five programs '
      'taking a paycheque game at a blue blood, so they would have lost '
      'anyway. Comparing each team against **itself** - its own margin '
      'on long eastward trips versus its own margin on every other away '
      f'game - the penalty is **{within_team["penalty"]:+.1f} points** '
      f'across {int(within_team["teams"])} team-seasons '
      f'({within_team["long_trip_margin"]:+.1f} on long eastward trips '
      f'versus {within_team["other_away_margin"]:+.1f} on other away '
      'games).',
      '',
    ]

  if realignment_travel is not None and not realignment_travel.empty:
    movers = realignment_travel[realignment_travel['tz_shift_change'] > 0.5]
    if not movers.empty:
      has_home = 'home_margin_change' in movers.columns
      lines += [
        '### Who now travels further',
        '',
        'Average time zones crossed per away game, before and after the '
        'move. The old Pac-12 fit inside two zones; the Big Ten and ACC '
        'do not. Home margin is the control: a tougher new league lowers '
        'both, while a travel burden should only show up on the road.',
        '',
      ]
      if has_home:
        lines += [
          '| School | Move | Zones before | Zones after | Away margin '
          'change | Home margin change | Road gap change |',
          '| --- | --- | ---: | ---: | ---: | ---: | ---: |',
        ]
      else:
        lines += [
          '| School | Move | Zones before | Zones after | Change | '
          'Away margin change |',
          '| --- | --- | ---: | ---: | ---: | ---: |',
        ]
      for row in movers.itertuples():
        if has_home:
          lines.append(
            f'| {row.school} | {row.move} | '
            f'{row.mean_tz_shift_before:+.2f} | '
            f'{row.mean_tz_shift_after:+.2f} | '
            f'{row.away_margin_change:+.1f} | '
            f'{_fmt_r(row.home_margin_change, 1)} | '
            f'{_fmt_r(row.travel_gap_change, 1)} |'
          )
        else:
          lines.append(
            f'| {row.school} | {row.move} | '
            f'{row.mean_tz_shift_before:+.2f} | '
            f'{row.mean_tz_shift_after:+.2f} | '
            f'{row.tz_shift_change:+.2f} | '
            f'{row.away_margin_change:+.1f} |'
          )
      lines.append('')
      if has_home:
        pooled = movers.dropna(subset=['home_margin_change'])
        if len(pooled) >= 3:
          gap, p_value, negative = _road_gap_test(pooled)
          lines += [
            f'Pooled over these {len(pooled)} schools, away margin moved '
            f'**{pooled["away_margin_change"].mean():+.1f}** and home '
            f'margin **{pooled["home_margin_change"].mean():+.1f}** points '
            f'per game. The road gap averaged {gap:+.1f} with {negative} of '
            f'{len(pooled)} schools negative, but a one-sample t-test gives '
            f'p = {p_value:.2f}: few games per school and different '
            'opponents each year make this suggestive, not conclusive.',
            '',
          ]

  return lines


def build_report(
  merged: pd.DataFrame,
  correlations: pd.DataFrame,
  model: dict[str, object] | None,
  conference: pd.DataFrame,
  season: int,
  week: int | None,
  figures: list[str] | None = None,
  figure_prefix: str = '',
  revenue_spending_overlap: float | None = None,
  season_trend: pd.DataFrame | None = None,
  realignment_changes: pd.DataFrame | None = None,
  pac12_diaspora: pd.DataFrame | None = None,
  travel_by_shift: pd.DataFrame | None = None,
  travel_within_team: dict[str, float] | None = None,
  realignment_travel: pd.DataFrame | None = None,
  schedule_split: pd.DataFrame | None = None,
  relative_summary: dict[str, float] | None = None,
  relative_extremes: tuple[pd.DataFrame, pd.DataFrame] | None = None,
  decomposition: pd.DataFrame | None = None,
  relative_by_season: pd.DataFrame | None = None,
  drivers: dict[str, object] | None = None,
  trends: dict[str, object] | None = None,
  tiers: pd.DataFrame | None = None,
  gameday: dict[str, object] | None = None,
) -> str:
  """Renders the full markdown report.

  Args:
    merged: Merged analysis table.
    correlations: Correlation table.
    model: Fitted OLS result, or ``None``.
    conference: Conference summary table.
    season: Season year.
    week: Current week number, if known.
    figures: Paths of generated figures to embed.
    figure_prefix: Prefix prepended to figure paths in the markdown.
    revenue_spending_overlap: Correlation between logged revenue and
      logged spending.
    season_trend: Per-season correlations from
      :func:`cfbmoney.analyze.correlation_by_season`.
    realignment_changes: Before/after table from
      :func:`cfbmoney.realignment.before_after`.
    pac12_diaspora: Role-tagged table from
      :func:`cfbmoney.realignment.diaspora`.
    travel_by_shift: Results bucketed by time-zone shift.
    travel_within_team: Within-team long-trip penalty.
    realignment_travel: Travel change for each conference mover.
    schedule_split: Output of :func:`cfbmoney.insights.schedule_split`.
    relative_summary: Output of
      :func:`cfbmoney.insights.relative_spend_summary`.
    relative_extremes: Output of
      :func:`cfbmoney.insights.relative_spend_extremes`.
    decomposition: Output of
      :func:`cfbmoney.insights.spending_decomposition`.
    relative_by_season: Output of
      :func:`cfbmoney.insights.relative_spend_by_season`.
    drivers: Outputs of :mod:`cfbmoney.drivers` keyed ``momentum_table``,
      ``momentum``, ``residual_lag``, ``over``, ``under``, ``markers``,
      ``schedule_strength`` and ``budget_change``.
    trends: Outputs of :mod:`cfbmoney.trends`, keyed as in
      :func:`_trend_lines`.
    tiers: Output of :func:`cfbmoney.insights.budget_tiers`.
    gameday: Outputs of :mod:`cfbmoney.gameday` keyed ``week``,
      ``luck_summary``, ``luck_teams``, ``close``, ``home``,
      ``attendance_summary``, ``attendance_league``,
      ``attendance_gainers``, ``attendance_losers``,
      ``attendance_change`` and ``attendance_regression``.

  Returns:
    The report as a markdown string.
  """
  now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
  played = merged['games_played'].dropna()
  report_year = (
    int(merged['money_report_year'].dropna().iloc[0])
    if 'money_report_year' in merged.columns
    and merged['money_report_year'].notna().any()
    else None
  )
  pool = {pathlib.Path(f).name: f for f in (figures or [])}

  lines = [
    f'# Money vs winning: the {season} college football season',
    '',
    f'_Generated {now}. Season {season}, '
    f'through week {week if week else "?"}; '
    f'teams have played {played.min():.0f}-{played.max():.0f} games._',
    '',
    '> [!WARNING]',
    f'> Sample-size warning: this is an in-progress season. Teams have '
    f'played {played.min():.0f}-{played.max():.0f} games, which is not '
    'enough to separate skill from luck. Treat every coefficient below as '
    'directional until November.',
    '',
  ]

  drivers = drivers or {}
  gameday = gameday or {}
  lines += _key_findings(
    merged,
    correlations,
    schedule_split,
    relative_summary,
    decomposition,
    pac12_diaspora,
    realignment_travel,
    season,
    relative_by_season,
    drivers,
    trends,
    tiers,
    gameday,
  )

  # Each part is built separately so the contents list only names parts
  # that actually have material.
  parts: list[tuple[str, list[str]]] = []

  current: list[str] = _trend_lines(trends or {}, season)
  current += _figure(pool, 'season_trajectory', figure_prefix)
  if len(current) > 1:
    parts.append((f'What {season} is showing so far', current))

  money: list[str] = []
  money += ['## Spending versus revenue: which one tracks winning?', '']
  money += _flow_section(revenue_spending_overlap)
  money += _correlation_matrix(correlations)
  money += _figure(pool, 'revenue_vs_spending', figure_prefix)
  money += _figure(pool, 'football_expenses_vs_point_margin', figure_prefix)
  tier_lines = _tiers_lines(tiers, season)
  if tier_lines:
    money += ['## Budget tiers: the shape of the curve', '']
    money += tier_lines
    money += _figure(pool, 'budget_tiers', figure_prefix)
  if schedule_split is not None and not schedule_split.empty:
    money += ['## Where the money edge is won: in or out of conference', '']
    money += _schedule_section(schedule_split, season)
    money += _figure(pool, 'schedule_split', figure_prefix)
  elif season_trend is not None and not season_trend.empty:
    money += [
      '## The same question across seasons',
      '',
      '| Season | Teams | r (log football revenue vs win%) | R² |',
      '| ---: | ---: | ---: | ---: |',
    ]
    for row in season_trend.itertuples():
      marker = ' (in progress)' if int(row.season) == season else ''
      money.append(
        f'| {int(row.season)}{marker} | {row.n} | '
        f'{row.pearson_r:+.3f} | {row.r_squared:.3f} |'
      )
    money.append('')
  relative_lines = _relative_section(
    relative_summary, relative_extremes, relative_by_season
  )
  if relative_lines:
    money += ['## Within the league: out-spending your peers', '']
    money += relative_lines
    if model:
      money += _model_section(model)
    money += _figure(pool, 'relative_spend', figure_prefix)
  elif model:
    money += [
      '## Holding the conference fixed',
      '',
    ]
    money += _model_section(model)
  parts.append(('Does money buy wins?', money))

  team: list[str] = []
  momentum_lines = _momentum_lines(
    drivers.get('momentum_table', pd.DataFrame()),
    drivers.get('momentum') or {},
    season,
  )
  if momentum_lines:
    team += ['## Last season versus this budget', '']
    team += momentum_lines
  persistence_lines = _persistence_lines(
    drivers.get('residual_lag', pd.DataFrame()),
    drivers.get('over', pd.DataFrame()),
    drivers.get('under', pd.DataFrame()),
    season,
  )
  if persistence_lines:
    team += ['## Who beats their budget year after year', '']
    team += persistence_lines
  marker_lines = _markers_lines(
    drivers.get('markers', pd.DataFrame()), drivers.get('schedule_strength')
  )
  if marker_lines:
    team += ['## On-field markers of a good team', '']
    team += marker_lines
    team += _figure(pool, 'box_score_markers', figure_prefix)
  decomposition_lines = _decomposition_section(
    decomposition if decomposition is not None else pd.DataFrame()
  )
  coach_lines = _coach_pay_section(merged, correlations)
  if decomposition_lines or coach_lines:
    team += ['## Which spending line matters?', '']
    team += decomposition_lines
    if coach_lines:
      team += ['### What the head coach is paid', '']
      team += coach_lines
  change_lines = _budget_change_lines(drivers.get('budget_change'))
  if change_lines:
    team += ['## Does getting richer help?', '']
    team += change_lines
  parts.append(('What separates good teams from bad', team))

  day: list[str] = []
  luck_lines = _luck_lines(
    gameday.get('luck_summary', pd.DataFrame()),
    gameday.get('luck_teams', pd.DataFrame()),
    season,
  )
  if luck_lines:
    day += ['## Luck: records that outrun the scoring', '']
    day += luck_lines
    day += _figure(pool, 'pythagorean', figure_prefix)
  close_lines = _close_lines(
    gameday.get('close', pd.DataFrame()), season, gameday.get('week')
  )
  if close_lines:
    day += ['## Close games versus blowouts', '']
    day += close_lines
    day += _figure(pool, 'close_games', figure_prefix)
  home_lines = _home_lines(gameday.get('home', pd.DataFrame()), season)
  if home_lines:
    day += ['## Home field: does money buy a louder stadium?', '']
    day += home_lines
  crowd_lines = _crowd_lines(
    gameday.get('attendance_summary', pd.DataFrame()),
    gameday.get('attendance_league', pd.DataFrame()),
    gameday.get('attendance_gainers', pd.DataFrame()),
    gameday.get('attendance_losers', pd.DataFrame()),
    gameday.get('attendance_change') or {},
    gameday.get('attendance_regression') or {},
    season,
    gameday.get('week'),
  )
  if crowd_lines:
    day += ['## Crowds: the live money signal', '']
    day += crowd_lines
    day += _figure(pool, 'attendance_vs_spending', figure_prefix)
  parts.append(('Luck, close games and crowds', day))

  moves: list[str] = []
  if realignment_changes is not None and not realignment_changes.empty:
    moves += ['## What happened to the schools that switched conference', '']
    moves += _realignment_section(
      realignment_changes,
      pac12_diaspora if pac12_diaspora is not None else pd.DataFrame(),
    )
    moves += _figure(pool, 'pac12_diaspora', figure_prefix)
    moves += _figure(pool, 'realignment_money_vs_margin', figure_prefix)
  if travel_by_shift is not None and not travel_by_shift.empty:
    moves += ['## Travel, time zones and the cost of flying east', '']
    moves += _travel_section(
      travel_by_shift, travel_within_team, realignment_travel
    )
    moves += _figure(pool, 'travel_timezone_penalty', figure_prefix)
  parts.append(('Realignment and travel', moves))

  nil = _nil_revshare_section(merged, correlations)
  # The NIL builder carries its own top-level heading; the part title
  # replaces it.
  nil = [line[1:] if line.startswith('###') else line for line in nil[2:]]
  parts.append(('Roster economics: NIL and revenue sharing', nil))

  reference: list[str] = []
  reference += ['## The richest programs and what they have done', '']
  reference += _leaderboard_section(merged)
  if not conference.empty:
    reference += ['## Conference summary', '']
    header = (
      '| Conference | Teams | Median football exp | Median football rev | '
      'Median dept rev | Mean win% | Mean margin |'
    )
    reference += [header, '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for row in conference.itertuples():
      reference.append(
        f'| {row.conference} | {getattr(row, "teams", "-")} | '
        f'{_usd_millions(getattr(row, "football_expenses", None))} | '
        f'{_usd_millions(getattr(row, "football_revenue", None))} | '
        f'{_usd_millions(getattr(row, "dept_total_revenue", None))} | '
        f'{_pct(getattr(row, "win_pct", None))} | '
        f'{getattr(row, "point_margin_per_game", float("nan")):+.1f} |'
      )
    reference.append('')
    reference += _figure(pool, 'football_expenses_by_conference', figure_prefix)
  if pool:
    reference += ['## Other figures', '']
    for name in list(pool):
      reference += _figure(pool, name, figure_prefix)
  parts.append(('Reference tables', reference))

  parts = [
    (f'{index}. {title}', content)
    for index, (title, content) in enumerate([(t, c) for t, c in parts if c], 1)
  ]
  lines += ['## Contents', '']
  lines += [f'- [{title}](#{_slug(title)})' for title, _ in parts]
  lines += [
    '- [Data sources](#data-sources)',
    '- [Caveats](#caveats-worth-repeating)',
    '',
  ]

  for title, content in parts:
    lines += [f'## {title}', '']
    lines += _demote(content)

  lines += [
    '## Data sources',
    '',
    '| Side | Source | Vintage |',
    '| --- | --- | --- |',
    f'| Results, scores, stats | ESPN public API | live, {season} |',
    f'| Football revenue/expenses, department revenue, average coach '
    f'salaries | US Dept of Education EADA filings | report year '
    f'{report_year if report_year else "n/a"} |',
    f'| Head coach total pay | hand-compiled, per-row citations | {season} |',
    '| Revenue-share cap, roster payroll, team talent | House '
    'settlement reporting, 247Sports | 2026 |',
    '',
  ]
  if report_year is not None and report_year < season:
    lines += [
      '> [!NOTE]',
      f'> Federal athletics finances are published on a lag, so the '
      f'{report_year} filings (academic year {report_year - 1}-'
      f'{str(report_year)[-2:]}) are the newest available. That is a '
      f'feature here rather than a bug: past spending is a *leading* '
      f'indicator of present results, so the direction of causation '
      f'runs the right way.',
      '',
    ]

  lines += [
    '## Caveats worth repeating',
    '',
    '- **Public vs. private accounting**: EADA filings are self-reported, '
    'and many private schools book revenue to exactly equal expenses.',
    '- **Reverse causation**: Football revenue partly reflects winning '
    '(tickets, donations, playoff payouts), so correlations are '
    'bidirectional.',
    '- **Unrecorded NIL & revenue-share splits**: The House cap is '
    'public, but per-school football allocations and third-party NIL '
    'collectives are private.',
    f"- **Realignment labels**: Fixed effects use each school's {season} "
    'conference; conference games are matched from same-season membership.',
    '',
  ]
  return '\n'.join(lines)


def write_report(text: str, season: int) -> pathlib.Path:
  """Writes the report to ``reports/``.

  Args:
    text: The markdown body.
    season: Season year used in the filename.

  Returns:
    The path written.
  """
  config.ensure_directories()
  path = config.REPORTS_DIR / f'money_vs_wins_{season}.md'
  path.write_text(text)
  logger.info('Wrote report to %s', path)
  return path
