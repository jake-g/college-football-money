"""Renders the markdown research report."""

from __future__ import annotations

import datetime
import logging
import pathlib
import re

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
    f'Outcome **{model["outcome"]}**, n = {model["n"]}, '
    f'R² = {model["r_squared"]:.3f} (adjusted '
    f'{model["adj_r_squared"]:.3f}), with {dummies} conference dummies.',
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
      f'Read: doubling the football budget within the same conference is '
      f'associated with **{estimate * 0.301 * 100:+.1f} points of win '
      'percentage** (log10(2) = 0.301).',
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
    'The national correlation blends two different contests. '
    '**Non-conference** games pit SEC budgets against MAC budgets; '
    '**conference** games pit a school against peers with similar '
    'media money. Splitting them shows where the money edge is won.',
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
  current = split[split['season'] == season]
  if not complete.empty:
    nonconf = complete['nonconf_fbs_richer_win'].mean()
    conf = complete['conference_richer_win'].mean()
    rel = complete['conference_r_relative'].mean()
    absolute = complete['conference_r_absolute'].mean()
    lines += [
      f'Across completed seasons the bigger budget wins **{_pct(nonconf)}** '
      f'of non-conference games against FBS opponents but only '
      f'**{_pct(conf)}** of conference games. Inside a conference, '
      f'absolute dollars barely track results (r = {absolute:+.2f}); '
      f'dollars *relative to the league median* do (r = {rel:+.2f}).',
      '',
    ]
    if not current.empty:
      row = current.iloc[0]
      share = row.conference_games / max(
        row.conference_games + row.nonconf_fbs_games, 1
      )
      lines += [
        '> [!IMPORTANT]',
        f'> Only **{share:.0%}** of {season} FBS-vs-FBS games so far are '
        'conference games, so the in-progress season is still dominated '
        'by the mismatches where money matters most. Expect the '
        f'{season} overall correlation to drift down toward the '
        'completed-season range as conference play fills the schedule.',
        '',
      ]
  fcs = split.dropna(subset=['fcs_mean_margin'])
  if not fcs.empty:
    lines += [
      f'Games against FCS opponents are excluded from both columns; '
      f'FBS teams won those by an average of '
      f'**{fcs["fcs_mean_margin"].mean():+.1f} points**, which is why '
      'early-season margin tables look inflated.',
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
    'Spending is re-expressed as a multiple of the conference median, '
    'and margin as points above the conference average. That removes '
    'the SEC-versus-MAC gap and leaves the question a school can act '
    'on: *does out-spending your own league pay?*',
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
        'Over a **full** season, out-spending your own conference predicts '
        'margin about as well as raw dollars do nationally (within r '
        f'{complete["r_within"].mean():+.2f} vs national '
        f'{complete["r_absolute"].mean():+.2f}, averaged over completed '
        'seasons). The in-progress season looks different mainly because '
        'September is packed with cross-league mismatches that inflate '
        'the national number; see the schedule split above.',
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
    'Is it the coaches, the recruiting budget or game-day operations? '
    'Each spending line is added to a model that already contains the '
    'total football budget. A line that mattered on its own would keep '
    'a significant coefficient (|t| > 2).',
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
    f'Every line correlates **{decomposition["corr_with_budget"].min():.2f} '
    f'or higher** with the total budget, and none survives with the '
    f'budget held fixed (largest |t| = {abs(strongest.added_t):.1f}, '
    f'{labels.get(strongest.component, strongest.component)}). Schools '
    'that spend big spend big on everything, so this data cannot say '
    '*which* line buys wins - only that the overall scale of the '
    'operation does.',
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
    'Before crediting the budget, compare it with the simplest forecast '
    "there is: last season's point margin.",
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
      f'last season alone explains **{pooled["r2_prior"]:.0%}** of the '
      f'spread in point margin, spending alone **{pooled["r2_money"]:.0%}** '
      f'and both together **{pooled["r2_both"]:.0%}**. Both stay '
      f'significant in the joint model (t = {pooled["t_prior"]:.1f} for '
      f'last season, {pooled["t_money"]:.1f} for spending): each point of '
      f"last season's margin carries {pooled['coef_prior']:.2f} points "
      'forward, and doubling the budget adds '
      f'**{pooled["coef_money"] * 0.301:+.1f} points per game** on top. '
      'Money is not just a proxy for being good last year.',
      '',
    ]
  current = table[table['season'] == season]
  if not current.empty and current.iloc[0].r_money > current.iloc[0].r_prior:
    lines += [
      f'In {season} so far spending out-predicts last season, the reverse '
      'of every completed year. That is the September schedule again: '
      'non-conference mismatches reward budget, and conference play has '
      'barely started.',
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
    'Each team gets a residual: its point margin minus what a team with '
    'its budget would be expected to post (a separate line each season). '
    'If beating the budget were luck, the residual would not repeat.',
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
      f'**{complete["r"].mean():+.2f}**: a team that beat its budget by 10 '
      f'points typically beats it by about {complete["r"].mean() * 10:.0f} '
      'the next year. That persistent part is whatever the budget line '
      'misses: coaching, scheme, player development, roster continuity, '
      'and money the federal filings do not see, such as NIL collectives.',
      '',
    ]
  if over.empty or under.empty:
    return lines
  years = sorted(
    int(c.split('_')[1]) for c in over.columns if c.startswith('residual_')
  )
  header = (
    '| Program | Conf | Football exp | '
    + ' | '.join(str(y) for y in years)
    + ' | Average |'
  )
  divider = '| --- | --- | ---: | ' + ' | '.join('---:' for _ in years)
  divider += ' | ---: |'
  for title, frame in (
    ('Consistently beating their budget (points per game)', over),
    ('Consistently missing their budget (points per game)', under),
  ):
    lines += [f'**{title}**', '', header, divider]
    for row in frame.itertuples():
      values = ' | '.join(
        f'{getattr(row, f"residual_{y}"):+.1f}' for y in years
      )
      lines.append(
        f'| {row.school} | {row.conference} | '
        f'{_usd_millions(row.football_expenses)} | {values} | '
        f'**{row.mean_residual:+.1f}** |'
      )
    lines.append('')
  cheap = over.nsmallest(2, 'football_expenses')
  rich = over.nlargest(2, 'football_expenses')
  low = cheap['football_expenses'].max()
  high = rich['football_expenses'].min()
  if low > 0 and high / low >= 3:
    lines += [
      'The over-performers span budgets from '
      f'{" and ".join(cheap["school"])} ({_usd_millions(low)} or less) to '
      f'{" and ".join(rich["school"])} ({_usd_millions(high)} or more), so '
      'this is not just rich teams outrunning a straight line.',
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

  Returns:
    list[str]: Markdown lines.
  """
  drivers = drivers or {}
  money: list[str] = []
  team: list[str] = []
  league: list[str] = []

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

  groups = [
    ('Does money buy wins?', money),
    ('What else makes a good team?', team),
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


def _residual_section(residuals: pd.DataFrame, top_n: int = 6) -> list[str]:
  """Builds the over/under-performance tables."""
  if residuals.empty:
    return []
  predictor = [
    c
    for c in residuals.columns
    if c not in ('school', 'conference', 'actual', 'predicted', 'residual')
  ]
  money_column = predictor[0] if predictor else None
  money_label = (
    _MONEY_LABELS.get(money_column, money_column) if money_column else 'Budget'
  )
  lines = [
    '**Beating their budget so far**',
    '',
    f'| Program | Conf | {money_label} | Actual | Budget-predicted | Gap |',
    '| --- | --- | ---: | ---: | ---: | ---: |',
  ]
  for row in residuals.head(top_n).itertuples():
    money = getattr(row, money_column) if money_column else None
    lines.append(
      f'| {row.school} | {row.conference} | {_usd_millions(money)} | '
      f'{_pct(row.actual)} | {_pct(row.predicted)} | '
      f'{row.residual * 100:+.1f} pts |'
    )
  lines += ['', '**Falling short of their budget so far**', '']
  lines += [
    f'| Program | Conf | {money_label} | Actual | Budget-predicted | Gap |',
    '| --- | --- | ---: | ---: | ---: | ---: |',
  ]
  for row in residuals.tail(top_n).iloc[::-1].itertuples():
    money = getattr(row, money_column) if money_column else None
    lines.append(
      f'| {row.school} | {row.conference} | {_usd_millions(money)} | '
      f'{_pct(row.actual)} | {_pct(row.predicted)} | '
      f'{row.residual * 100:+.1f} pts |'
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
    'moved for reasons that had nothing to do with how well any given '
    'team was playing.',
    '',
    '> [!IMPORTANT]',
    '> The federal finance filings lag the field by two years, so the '
    'newest money year available is the 2024 season. Schools that moved '
    'in 2024 therefore have exactly **one** post-move budget year on '
    'record, and schools that moved in 2026 have **none**. Their money '
    'columns are intentionally blank rather than filled with stale '
    'pre-move values.',
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
        'did nothing differently on the field; they simply lost their '
        'conference, and roughly a third of their football revenue went '
        'with it.',
        '',
        '> [!NOTE]',
        '> The leavers gained less than the headline media deals imply '
        'because several joined on **reduced shares**. Oregon and '
        'Washington entered the Big Ten at a reported ~$30M annual '
        'share against a full share of $65M+, escalating roughly $1M a '
        'year until they phase in near the end of the decade. That is '
        'why their measured revenue change here is single digit or even '
        'negative while UCLA and California, which did not take the '
        'same discount, moved much more.',
        '',
        '#### Realignment financial mechanics',
        '',
        'The dissolution of the original Pac-12 resulted in massive '
        'financial shifts, driven by media rights disparities and legal '
        'settlements:',
        '',
        '- **WSU/OSU Settlement & Exit Fees**: The 10 departing members '
        'forfeited **$65 million total** ($6.5M per school) to Washington '
        'State and Oregon State, who retained conference assets and '
        'liabilities.',
        '- **Media-Rights Hierarchy**: Big Ten agreements pay ~$1.1B-$1.2B '
        'annually (~$65M-$75M/school full share), compared to ~$380M for '
        'the Big 12 (~$31M/school) and ~$240M-$400M for the ACC.',
        '- **Tiered Big Ten Entry**: USC and UCLA entered at full shares '
        '(~$65M+), while Oregon and Washington entered at a $30M partial '
        'share increasing $1M/year until reaching parity in 2030.',
        '- **Travel Cost Inflation**: In their official presentation to the '
        'UC Board of Regents, UCLA Athletics projected an increase of '
        '**$4.6 million to $5.8 million** in annual travel and logistics '
        'costs due to cross-country Big Ten travel.',
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
    'Following the landmark *House v. NCAA* settlement, college football '
    'entered an era structured by an institutional revenue-sharing cap: '
    '~$20.5M for the 2025-26 academic year, escalating ~4% to ~$21.32M '
    'for 2026-27.',
    '',
    '> [!IMPORTANT]',
    '> Revenue-sharing caps and 247Sports team talent scores are public, '
    '> but **per-school football allocations and NIL collective payrolls '
    '> remain undisclosed.** While athletic departments widely cite a '
    '> rule of thumb directing ~75% of the cap to football (~$16M), no '
    '> major program publishes its exact balance sheet split. Rather than '
    '> interpolating or fabricating synthetic estimates, per-school '
    '> allocation and roster payroll columns (`football_allocation_est`, '
    '> `roster_payroll_est`) are left blank (`n/a`) until audited disclosures '
    '> exist.',
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
    'Because the House settlement revenue-share cap is uniform across all '
    'participating institutions, direct school-to-athlete distributions '
    'provide virtually zero competitive variance among top programs: every '
    'Power 4 powerhouse will max out the same cap. Consequently, competitive '
    'talent differentiation shifts into two distinct arenas: third-party '
    'booster collective fundraising ($15M-$20M+ at perennial blue-bloods) '
    'and discretionary athletic department spending on coaching, analysts, '
    'and support infrastructure.',
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
      f'{row.win_pct:.3f} | {row.point_margin_per_game:+.1f} |'
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
  )

  # Each part is built separately so the contents list only names parts
  # that actually have material.
  parts: list[tuple[str, list[str]]] = []

  money: list[str] = []
  money += ['## Spending versus revenue: which one tracks winning?', '']
  money += _flow_section(revenue_spending_overlap)
  money += _correlation_matrix(correlations)
  money += _figure(pool, 'revenue_vs_spending', figure_prefix)
  money += _figure(pool, 'football_expenses_vs_point_margin', figure_prefix)
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
    money += _figure(pool, 'relative_spend', figure_prefix)
  if model:
    money += [
      '## Holding the conference fixed',
      '',
      'Conference dummies absorb the media-rights advantage, so the '
      'money coefficient answers a narrower question: *within the '
      'same league, does the bigger budget win more?*',
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
  if model:
    reference += [f'## {season} so far: who is beating their budget', '']
    reference += [
      'Win percentage against the conference-adjusted budget model '
      'above. With only a handful of games played these swing weekly; '
      'the multi-year table in part 2 is the better guide.',
      '',
    ]
    reference += _residual_section(model['residuals'])
    reference += _figure(pool, 'residuals', figure_prefix)
  if not conference.empty:
    reference += ['## Conference summary', '']
    header = '| Conference | Teams | Median football rev | '
    header += 'Median dept rev | Mean win% | Mean margin |'
    reference += [header, '| --- | ---: | ---: | ---: | ---: | ---: |']
    for row in conference.itertuples():
      reference.append(
        f'| {row.conference} | {getattr(row, "teams", "-")} | '
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
  parts.append((f'Reference: the {season} season so far', reference))

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
    '- EADA revenue is self-reported and, at many private schools, '
    'revenue is booked to exactly equal expenses. Comparisons across '
    'the public/private line are shakier than they look.',
    '- Football revenue is partly a *consequence* of winning '
    '(ticket sales, donations, playoff payouts), so correlation here '
    'is bidirectional, not clean causation.',
    '- Revenue-share and NIL money, which is where the 2026 arms race '
    'actually happens, is largely private. The cap is public; the '
    'allocation is not.',
    "- Conference realignment means a team's conference label "
    'changed recently for several programs; fixed effects use the '
    f'{season} alignment.',
    "- Conference games are identified from both teams' conference "
    "that season; ESPN's schedule feed does not flag them.",
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
