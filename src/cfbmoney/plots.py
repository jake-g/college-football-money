"""Charts for the money-versus-wins analysis.

All figures are written to ``reports/figures`` as PNG files.  Matplotlib
is used in its non-interactive Agg mode so the pipeline runs headless.

Conventions used across the charts:

* Money is always on a log x-axis; the distribution is brutally skewed.
* A **solid** trend line covers the range where data actually exists.
  Any **dotted** line is an extrapolation or a projection and should be
  read as a guess, not a measurement.
* On margin charts the lower-right quadrant - above-median spending,
  negative point margin - is shaded red.  That is the "paying a lot to
  lose" zone.  The upper-left, below-median spending with a positive
  margin, is shaded green: the bargains.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import matplotlib

matplotlib.use('Agg')

import matplotlib.pyplot as plt  # noqa: E402  (must follow use('Agg'))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from . import config  # noqa: E402

logger = logging.getLogger(__name__)

CONFERENCE_COLORS = {
  'SEC': '#c8102e',
  'Big Ten': '#0033a0',
  'Big 12': '#c8462e',
  'ACC': '#013ca6',
  'FBS Independents': '#5a5a5a',
  'American': '#00a3e0',
  'Mountain West': '#2e7d32',
  'Sun Belt': '#f2a900',
  'MAC': '#7b1fa2',
  'Conference USA': '#00838f',
  'Pac-12': '#004b91',
}

DEFAULT_FIGSIZE = (11.0, 7.5)

# Shading for the quadrant callouts.
_BAD_QUADRANT = '#c62828'
_GOOD_QUADRANT = '#2e7d32'

_AXIS_LABELS = {
  'football_revenue': 'Football revenue',
  'football_expenses': 'Football spending',
  'football_spend_per_player': 'Football spending per player',
  'football_nonoperating_spend': 'Football non-game-day spending',
  'football_coach_payroll_est': 'Estimated football coach payroll',
  'mens_coaching_payroll': "Men's coaching payroll",
  'recruiting_expenses_men': "Men's recruiting spending",
  'dept_total_revenue': 'Athletics department revenue',
  'dept_total_expenses': 'Athletics department spending',
  'avg_head_coach_salary_men': "Average men's head coach salary",
  'win_pct': 'Win percentage',
  'point_margin_per_game': 'Point margin per game',
  'points_per_game': 'Points scored per game',
  'points_allowed_per_game': 'Points allowed per game',
}


def _label(column: str) -> str:
  """Returns a readable axis label for a column."""
  return _AXIS_LABELS.get(column, column.replace('_', ' ').title())


def _shade_quadrants(
  axes: plt.Axes,
  x_divider: float,
  y_divider: float,
  x_limits: Sequence[float],
  y_limits: Sequence[float],
  bad_is_below: bool = True,
) -> None:
  """Shades the value and the money-pit quadrants.

  Args:
    axes: Target axes.
    x_divider: Money value splitting cheap from expensive (median).
    y_divider: Performance value splitting good from bad.
    x_limits: Current x-axis limits.
    y_limits: Current y-axis limits.
    bad_is_below: True when lower y values are worse.
  """
  low_y, high_y = y_limits
  low_x, high_x = x_limits
  bad_span = (low_y, y_divider) if bad_is_below else (y_divider, high_y)
  good_span = (y_divider, high_y) if bad_is_below else (low_y, y_divider)

  # Freeze the view so the shading cannot rescale the axes and leave a
  # visible gap at the edges.
  axes.set_xlim(low_x, high_x)
  axes.set_ylim(low_y, high_y)
  axes.autoscale(False)

  axes.fill_between(
    [x_divider, high_x],
    bad_span[0],
    bad_span[1],
    color=_BAD_QUADRANT,
    alpha=0.08,
    zorder=0,
  )
  axes.fill_between(
    [low_x, x_divider],
    good_span[0],
    good_span[1],
    color=_GOOD_QUADRANT,
    alpha=0.08,
    zorder=0,
  )
  axes.axvline(x_divider, color='grey', linestyle=':', linewidth=1)
  axes.axhline(y_divider, color='grey', linestyle=':', linewidth=1)

  axes.text(
    high_x,
    bad_span[0],
    'spending a lot, losing  ',
    ha='right',
    va='bottom',
    fontsize=9,
    color=_BAD_QUADRANT,
    alpha=0.9,
    fontweight='bold',
  )
  axes.text(
    low_x,
    good_span[1],
    '  spending little, winning',
    ha='left',
    va='top',
    fontsize=9,
    color=_GOOD_QUADRANT,
    alpha=0.9,
    fontweight='bold',
  )


def _trend_with_projection(
  axes: plt.Axes,
  log_x: np.ndarray,
  y_values: np.ndarray,
  project: bool,
) -> float:
  """Draws a fitted trend line plus a dotted extrapolation.

  Args:
    axes: Target axes.
    log_x: log10 money values.
    y_values: Performance values.
    project: Whether to extend the fit past the observed range.

  Returns:
    The Pearson correlation of the fit.
  """
  slope, intercept = np.polyfit(log_x, y_values, 1)
  correlation = float(np.corrcoef(log_x, y_values)[0, 1])
  observed = np.linspace(log_x.min(), log_x.max(), 100)
  axes.plot(
    10**observed,
    slope * observed + intercept,
    color='black',
    linewidth=1.8,
    label=f'fit over observed range (r = {correlation:.2f})',
    zorder=3,
  )
  if project:
    span = log_x.max() - log_x.min()
    upper = np.linspace(log_x.max(), log_x.max() + 0.18 * span, 30)
    lower = np.linspace(log_x.min() - 0.18 * span, log_x.min(), 30)
    for segment, label in ((upper, 'extrapolated'), (lower, None)):
      axes.plot(
        10**segment,
        slope * segment + intercept,
        color='black',
        linestyle=':',
        linewidth=1.6,
        label=label,
        zorder=3,
      )
  return correlation


def _annotate_points(
  axes: plt.Axes,
  data: pd.DataFrame,
  x_column: str,
  y_column: str,
  annotate: list[str] | None = None,
  scale_x: float = 1.0,
  max_labels: int = 18,
  fontsize: int = 8,
) -> list[str]:
  """Labels reference schools and notable outliers on a scatter plot.

  Every scatter in the report keeps the same set of familiar reference
  programs visible so charts can be compared against each other, then
  adds whichever schools are extreme on this particular pair of axes.

  Args:
    axes (plt.Axes): Axes to draw on.
    data (pd.DataFrame): Rows to label, containing a ``school`` column.
    x_column (str): Column plotted on the x axis.
    y_column (str): Column plotted on the y axis.
    annotate (list[str] | None): Explicit schools to label.  When
      ``None`` a default set is chosen automatically.
    scale_x (float): Divisor applied to x values, matching the plotted
      units (money charts plot millions).
    max_labels (int): Upper bound on labels so panels stay readable.
    fontsize (int): Label font size.

  Returns:
    list[str]: Schools that were actually labelled.
  """
  if data.empty or 'school' not in data.columns:
    return []
  usable = data.dropna(subset=[x_column, y_column])
  if usable.empty:
    return []

  if annotate is None:
    # Reference programs first so they survive the max_labels cut.
    wanted = [
      school
      for school in config.HEADLINE_PROGRAMS
      if school in set(usable['school'])
    ]
    extremes = []
    extremes += usable.nlargest(2, y_column)['school'].tolist()
    extremes += usable.nsmallest(2, y_column)['school'].tolist()
    extremes += usable.nlargest(2, x_column)['school'].tolist()
    # Whoever is deepest into the money-pit quadrant is the story.
    expensive = usable[usable[x_column] >= usable[x_column].median()]
    extremes += expensive.nsmallest(3, y_column)['school'].tolist()
    for school in extremes:
      if school not in wanted:
        wanted.append(school)
  else:
    wanted = list(dict.fromkeys(annotate))

  wanted = wanted[:max_labels]
  labelled = usable[usable['school'].isin(wanted)]
  for row in labelled.itertuples():
    axes.annotate(
      row.school,
      (getattr(row, x_column) / scale_x, getattr(row, y_column)),
      textcoords='offset points',
      xytext=(6, 5),
      fontsize=fontsize,
      zorder=4,
    )
  return labelled['school'].tolist()


def scatter_money_vs_performance(
  frame: pd.DataFrame,
  money_column: str = 'football_expenses',
  performance_column: str = 'point_margin_per_game',
  season: int = config.DEFAULT_SEASON,
  annotate: list[str] | None = None,
  filename: str | None = None,
  shade_quadrants: bool = True,
  project: bool = True,
) -> str | None:
  """Plots money against performance with a trend line and quadrants.

  Args:
    frame: Merged analysis table.
    money_column: Column on the x axis (log scale).
    performance_column: Column on the y axis.
    season: Season year, used in the title and filename.
    annotate: Schools to label; defaults to the headline programs plus
      the extremes of both axes.
    filename: Optional output filename override.
    shade_quadrants: Whether to shade the value/money-pit quadrants.
    project: Whether to extend the trend line as a dotted projection.

  Returns:
    The path written, or ``None`` when there is nothing to plot.
  """
  data = frame[
    ['school', 'conference', money_column, performance_column]
  ].dropna()
  data = data[data[money_column] > 0]
  if len(data) < 5:
    logger.warning('Not enough data to plot %s', money_column)
    return None

  x_values = data[money_column].to_numpy(dtype=float) / 1e6
  y_values = data[performance_column].to_numpy(dtype=float)

  figure, axes = plt.subplots(figsize=DEFAULT_FIGSIZE)
  for conference, group in data.groupby('conference'):
    axes.scatter(
      group[money_column] / 1e6,
      group[performance_column],
      s=70,
      alpha=0.85,
      label=conference,
      color=CONFERENCE_COLORS.get(conference, '#888888'),
      edgecolors='white',
      linewidths=0.8,
      zorder=2,
    )

  axes.set_xscale('log')
  correlation = _trend_with_projection(
    axes, np.log10(x_values), y_values, project
  )

  if shade_quadrants:
    y_divider = (
      0.0
      if performance_column in ('point_margin_per_game',)
      else float(np.median(y_values))
    )
    _shade_quadrants(
      axes,
      float(np.median(x_values)),
      y_divider,
      axes.get_xlim(),
      axes.get_ylim(),
    )

  _annotate_points(
    axes, data, money_column, performance_column, annotate, scale_x=1e6
  )

  axes.set_xlabel(f'{_label(money_column)} ($ millions, log scale)')
  axes.set_ylabel(_label(performance_column))
  axes.set_title(
    f'{_label(money_column)} vs {_label(performance_column).lower()} '
    f'- {season} season  (r = {correlation:.2f})'
  )
  axes.grid(alpha=0.2, which='both', zorder=0)
  axes.legend(fontsize=8, ncol=2, loc='lower right', framealpha=0.9)
  figure.tight_layout()

  name = filename or f'{money_column}_vs_{performance_column}_{season}.png'
  path = config.FIGURES_DIR / name
  figure.savefig(path, dpi=150)
  plt.close(figure)
  logger.info('Wrote %s', path)
  return str(path)


def revenue_vs_spending_panel(
  frame: pd.DataFrame,
  performance_column: str = 'point_margin_per_game',
  season: int = config.DEFAULT_SEASON,
  filename: str | None = None,
) -> str | None:
  """Puts money-in and money-out side by side on the same y axis.

  Args:
    frame: Merged analysis table.
    performance_column: Performance column for the shared y axis.
    season: Season year.
    filename: Optional output filename override.

  Returns:
    The path written, or ``None`` when there is nothing to plot.
  """
  columns = [
    ('football_revenue', 'Money IN: football revenue'),
    ('football_expenses', 'Money OUT: football spending'),
  ]
  available = [(c, t) for c, t in columns if c in frame.columns]
  if len(available) < 2:
    return None

  figure, axes_list = plt.subplots(1, 2, figsize=(15.0, 6.8), sharey=True)
  for axes, (column, title) in zip(axes_list, available, strict=False):
    data = frame[['school', 'conference', column, performance_column]].dropna()
    data = data[data[column] > 0]
    if data.empty:
      continue
    axes.scatter(
      data[column] / 1e6,
      data[performance_column],
      s=55,
      alpha=0.85,
      c=[CONFERENCE_COLORS.get(c, '#888888') for c in data['conference']],
      edgecolors='white',
      linewidths=0.7,
      zorder=2,
    )
    axes.set_xscale('log')
    log_x = np.log10(data[column].to_numpy(dtype=float) / 1e6)
    correlation = _trend_with_projection(
      axes, log_x, data[performance_column].to_numpy(dtype=float), True
    )
    y_divider = (
      0.0
      if performance_column == 'point_margin_per_game'
      else (float(data[performance_column].median()))
    )
    _shade_quadrants(
      axes,
      float((data[column] / 1e6).median()),
      y_divider,
      axes.get_xlim(),
      axes.get_ylim(),
    )
    _annotate_points(
      axes,
      data,
      column,
      performance_column,
      scale_x=1e6,
      max_labels=10,
      fontsize=7,
    )
    axes.set_title(f'{title}   (r = {correlation:.2f})')
    axes.set_xlabel('$ millions, log scale')
    axes.grid(alpha=0.2, which='both')
  axes_list[0].set_ylabel(_label(performance_column))
  figure.suptitle(
    f'Does taking money in look different from paying money out? - {season}',
    fontsize=13,
  )
  figure.tight_layout()

  path = config.FIGURES_DIR / (
    filename or f'revenue_vs_spending_{performance_column}_{season}.png'
  )
  figure.savefig(path, dpi=150)
  plt.close(figure)
  logger.info('Wrote %s', path)
  return str(path)


def multi_season_scatter(
  panel: pd.DataFrame,
  money_column: str = 'football_expenses',
  performance_column: str = 'point_margin_per_game',
  filename: str | None = None,
) -> str | None:
  """Draws one scatter per season so the trend can be compared.

  Args:
    panel: Long frame with a ``season`` column.
    money_column: Money column for the x axis.
    performance_column: Performance column for the y axis.
    filename: Optional output filename override.

  Returns:
    The path written, or ``None`` when fewer than two seasons exist.
  """
  usable = panel[
    ['season', 'school', 'conference', money_column, performance_column]
  ].dropna()
  usable = usable[usable[money_column] > 0]
  seasons = sorted(usable['season'].unique())
  if len(seasons) < 2:
    return None

  figure, axes_list = plt.subplots(
    1,
    len(seasons),
    figsize=(5.2 * len(seasons), 6.0),
    sharey=True,
    sharex=True,
  )
  if len(seasons) == 1:
    axes_list = [axes_list]

  for axes, season in zip(axes_list, seasons, strict=True):
    group = usable[usable['season'] == season]
    axes.scatter(
      group[money_column] / 1e6,
      group[performance_column],
      s=42,
      alpha=0.8,
      c=[CONFERENCE_COLORS.get(c, '#888888') for c in group['conference']],
      edgecolors='white',
      linewidths=0.6,
      zorder=2,
    )
    axes.set_xscale('log')
    log_x = np.log10(group[money_column].to_numpy(dtype=float) / 1e6)
    correlation = _trend_with_projection(
      axes, log_x, group[performance_column].to_numpy(dtype=float), False
    )
    y_divider = (
      0.0
      if performance_column == 'point_margin_per_game'
      else (float(group[performance_column].median()))
    )
    _shade_quadrants(
      axes,
      float((group[money_column] / 1e6).median()),
      y_divider,
      axes.get_xlim(),
      axes.get_ylim(),
    )
    _annotate_points(
      axes,
      group,
      money_column,
      performance_column,
      annotate=config.REFERENCE_PROGRAMS,
      scale_x=1e6,
      fontsize=7,
    )
    partial = season == max(seasons)
    axes.set_title(
      f'{season}{" (in progress)" if partial else ""}\n'
      f'r = {correlation:.2f}, n = {len(group)}'
    )
    axes.set_xlabel(f'{_label(money_column)} ($M, log)')
    axes.grid(alpha=0.2, which='both')
    axes.get_legend_handles_labels()
  axes_list[0].set_ylabel(_label(performance_column))
  figure.suptitle(
    f'{_label(money_column)} vs '
    f'{_label(performance_column).lower()}, season by season',
    fontsize=13,
  )
  figure.tight_layout()

  path = config.FIGURES_DIR / (
    filename or f'{money_column}_vs_{performance_column}_by_season.png'
  )
  figure.savefig(path, dpi=150)
  plt.close(figure)
  logger.info('Wrote %s', path)
  return str(path)


def residual_bars(
  residuals: pd.DataFrame,
  season: int = config.DEFAULT_SEASON,
  top_n: int = 15,
  filename: str | None = None,
) -> str | None:
  """Plots the biggest over- and under-performers versus budget.

  Args:
    residuals: ``residuals`` frame from :func:`cfbmoney.analyze.fit_ols`.
    season: Season year.
    top_n: How many teams to show at each end.
    filename: Optional output filename override.

  Returns:
    The path written, or ``None`` when the frame is empty.
  """
  if residuals.empty:
    return None
  ordered = residuals.sort_values('residual', ascending=False)
  subset = pd.concat([ordered.head(top_n), ordered.tail(top_n)])
  subset = subset.drop_duplicates('school').sort_values('residual')

  figure, axes = plt.subplots(figsize=(10.0, 0.34 * len(subset) + 2.2))
  colors = [
    _GOOD_QUADRANT if value > 0 else _BAD_QUADRANT
    for value in subset['residual']
  ]
  axes.barh(subset['school'], subset['residual'], color=colors)
  axes.axvline(0, color='black', linewidth=0.9)
  axes.set_xlabel('Actual minus spending-predicted performance')
  axes.set_title(
    f'Who beats their budget - {season} season to date\n'
    'Green = doing better than their spending predicts'
  )
  axes.grid(axis='x', alpha=0.25)
  figure.tight_layout()

  path = config.FIGURES_DIR / (filename or f'residuals_{season}.png')
  figure.savefig(path, dpi=150)
  plt.close(figure)
  logger.info('Wrote %s', path)
  return str(path)


def conference_money_box(
  frame: pd.DataFrame,
  money_column: str = 'football_expenses',
  season: int = config.DEFAULT_SEASON,
  filename: str | None = None,
) -> str | None:
  """Draws a box plot of money by conference.

  Args:
    frame: Merged analysis table.
    money_column: Money column to summarise.
    season: Season year.
    filename: Optional output filename override.

  Returns:
    The path written, or ``None`` when there is nothing to plot.
  """
  data = frame[['conference', money_column]].dropna()
  if data.empty:
    return None
  order = (
    data.groupby('conference')[money_column]
    .median()
    .sort_values(ascending=False)
    .index.tolist()
  )
  samples = [
    data.loc[data['conference'] == c, money_column] / 1e6 for c in order
  ]

  figure, axes = plt.subplots(figsize=(10.0, 6.0))
  boxes = axes.boxplot(samples, tick_labels=order, patch_artist=True)
  for patch, conference in zip(boxes['boxes'], order, strict=True):
    patch.set_facecolor(CONFERENCE_COLORS.get(conference, '#888888'))
    patch.set_alpha(0.7)
  axes.set_ylabel(f'{_label(money_column)} ($ millions)')
  axes.set_title(f'{_label(money_column)} by conference - {season}')
  axes.grid(axis='y', alpha=0.25)
  plt.setp(axes.get_xticklabels(), rotation=25, ha='right')
  figure.tight_layout()

  path = config.FIGURES_DIR / (
    filename or f'{money_column}_by_conference_{season}.png'
  )
  figure.savefig(path, dpi=150)
  plt.close(figure)
  logger.info('Wrote %s', path)
  return str(path)


def money_vs_wins_history(
  panel: pd.DataFrame,
  money_columns: Sequence[str] = (
    'football_revenue',
    'football_expenses',
  ),
  season_column: str = 'season',
  filename: str = 'correlation_by_season.png',
  project: bool = True,
) -> str | None:
  """Plots how the money/wins correlation moves across seasons.

  Completed seasons are drawn solid.  The in-progress season and any
  forward projection are dotted.

  Args:
    panel: Long frame with one row per team-season.
    money_columns: Money columns to trend.
    season_column: Name of the season column.
    filename: Output filename.
    project: Whether to extend one season into the future as a dotted
      linear projection.

  Returns:
    The path written, or ``None`` when fewer than two seasons exist.
  """
  figure, axes = plt.subplots(figsize=(9.5, 5.6))
  drew_anything = False
  colors = {'football_revenue': '#0033a0', 'football_expenses': '#c8102e'}

  for money_column in money_columns:
    if money_column not in panel.columns:
      continue
    usable = panel[[season_column, money_column, 'win_pct']].dropna()
    usable = usable[usable[money_column] > 0]
    seasons, correlations = [], []
    for season, group in usable.groupby(season_column):
      if len(group) < 20:
        continue
      seasons.append(int(season))
      correlations.append(
        float(
          np.corrcoef(np.log10(group[money_column]), group['win_pct'])[0, 1]
        )
      )
    if len(seasons) < 2:
      continue
    drew_anything = True
    color = colors.get(money_column, '#555555')
    # Everything up to the final season is complete; the final season
    # is in progress, so that last hop is drawn dotted.
    axes.plot(
      seasons[:-1],
      correlations[:-1],
      marker='o',
      color=color,
      linewidth=2,
      label=_label(money_column),
    )
    axes.plot(
      seasons[-2:],
      correlations[-2:],
      marker='o',
      color=color,
      linewidth=2,
      linestyle=':',
    )
    if project and len(seasons) >= 3:
      slope, intercept = np.polyfit(seasons[:-1], correlations[:-1], 1)
      next_season = seasons[-1] + 1
      axes.plot(
        [seasons[-1], next_season],
        [correlations[-1], slope * next_season + intercept],
        color=color,
        linestyle=':',
        linewidth=1.3,
        alpha=0.7,
      )
      axes.scatter(
        [next_season],
        [slope * next_season + intercept],
        facecolors='none',
        edgecolors=color,
        s=70,
      )

  if not drew_anything:
    plt.close(figure)
    return None

  axes.set_xlabel('Season')
  axes.set_ylabel('Correlation with win percentage')
  axes.set_title(
    'Does money matter more over time?\n'
    'Solid = completed seasons, dotted = in progress or projected'
  )
  axes.grid(alpha=0.25)
  axes.set_ylim(0, 1)
  axes.legend(fontsize=9)
  figure.tight_layout()

  path = config.FIGURES_DIR / filename
  figure.savefig(path, dpi=150)
  plt.close(figure)
  logger.info('Wrote %s', path)
  return str(path)


def pac12_diaspora_chart(
  diaspora: pd.DataFrame,
  filename: str = 'pac12_diaspora.png',
) -> str | None:
  """Charts the revenue fate of the Pac-12's leavers, stayers and joiners.

  The breakup split twelve schools into three groups that experienced the
  same shock from different sides, so a grouped bar of percentage revenue
  change is the clearest way to see who won and who paid.

  Args:
    diaspora (pd.DataFrame): Output of ``realignment.diaspora``.
    filename (str): Output file name.

  Returns:
    str | None: Path written, or ``None`` when there is nothing to draw.
  """
  if diaspora.empty or 'football_revenue_pct_change' not in diaspora:
    logger.warning('Diaspora chart skipped: no revenue change data')
    return None
  data = diaspora.dropna(subset=['football_revenue_pct_change']).copy()
  if data.empty:
    logger.warning('Diaspora chart skipped: revenue change all missing')
    return None

  role_colors = {'left': '#2e7d32', 'stayed': '#c62828', 'joined': '#1565c0'}
  data = data.sort_values(['role', 'football_revenue_pct_change'])
  figure, axes = plt.subplots(figsize=(11, 6.5))
  positions = np.arange(len(data))
  axes.barh(
    positions,
    data['football_revenue_pct_change'],
    color=[role_colors.get(r, '#888888') for r in data['role']],
    edgecolor='white',
    zorder=2,
  )
  axes.set_yticks(positions)
  axes.set_yticklabels(data['school'])
  axes.axvline(0, color='black', linewidth=1)
  for position, value in zip(
    positions, data['football_revenue_pct_change'], strict=True
  ):
    offset = 1.0 if value >= 0 else -1.0
    axes.annotate(
      f'{value:+.0f}%',
      (value + offset, position),
      va='center',
      ha='left' if value >= 0 else 'right',
      fontsize=8,
    )

  # Only advertise roles that actually have bars; schools with no
  # post-move filing yet are dropped above and would otherwise leave a
  # legend entry pointing at nothing.
  role_labels = (
    ('left', 'left the Pac-12'),
    ('stayed', 'stayed behind'),
    ('joined', 'joined the new Pac-12'),
  )
  present = set(data['role'])
  handles = [
    plt.Line2D([], [], color=role_colors[role], linewidth=8, label=label)
    for role, label in role_labels
    if role in present
  ]
  axes.legend(handles=handles, fontsize=9, loc='lower right')

  span = float(data['football_revenue_pct_change'].abs().max())
  axes.set_xlim(-span * 1.25, span * 1.25)
  axes.set_xlabel('Change in football revenue, before vs after the move (%)')
  axes.set_title(
    'The Pac-12 breakup: who gained revenue and who was stranded\n'
    'Comparing the 2023 and 2024 football seasons (newest federal filing)',
    fontsize=12,
  )
  axes.grid(alpha=0.2, axis='x', zorder=0)
  figure.tight_layout()

  path = config.FIGURES_DIR / filename
  figure.savefig(path, dpi=150)
  plt.close(figure)
  logger.info('Wrote %s', path)
  return str(path)


def realignment_scatter(
  changes: pd.DataFrame,
  filename: str = 'realignment_money_vs_margin.png',
) -> str | None:
  """Plots change in revenue against change in point margin for movers.

  If buying a better address bought better football, movers who gained
  revenue would also have gained point margin and the cloud would slope
  upward.

  Args:
    changes (pd.DataFrame): Output of ``realignment.before_after``.
    filename (str): Output file name.

  Returns:
    str | None: Path written, or ``None`` when there is nothing to draw.
  """
  needed = {'football_revenue_pct_change', 'point_margin_per_game_change'}
  if changes.empty or not needed.issubset(changes.columns):
    logger.warning('Realignment scatter skipped: missing columns')
    return None
  data = changes.dropna(subset=list(needed)).copy()
  if len(data) < 3:
    logger.warning('Realignment scatter skipped: only %d movers', len(data))
    return None

  figure, axes = plt.subplots(figsize=(10, 7))
  axes.axhline(0, color='black', linewidth=1, zorder=1)
  axes.axvline(0, color='black', linewidth=1, zorder=1)
  axes.scatter(
    data['football_revenue_pct_change'],
    data['point_margin_per_game_change'],
    s=90,
    c='#1565c0',
    alpha=0.85,
    edgecolors='white',
    linewidths=0.8,
    zorder=3,
  )
  for row in data.itertuples():
    axes.annotate(
      row.school,
      (row.football_revenue_pct_change, row.point_margin_per_game_change),
      textcoords='offset points',
      xytext=(6, 5),
      fontsize=8,
      zorder=4,
    )

  x_values = data['football_revenue_pct_change'].to_numpy(dtype=float)
  y_values = data['point_margin_per_game_change'].to_numpy(dtype=float)
  # NOTE: _trend_with_projection plots 10**x because the money charts use
  # a log axis.  This chart is linear, so it needs its own fit.
  slope, intercept = np.polyfit(x_values, y_values, 1)
  correlation = float(np.corrcoef(x_values, y_values)[0, 1])
  line_x = np.linspace(x_values.min(), x_values.max(), 100)
  axes.plot(
    line_x,
    slope * line_x + intercept,
    color='black',
    linewidth=1.8,
    label=f'fit (r = {correlation:.2f})',
    zorder=3,
  )

  axes.set_xlabel('Change in football revenue after the move (%)')
  axes.set_ylabel('Change in point margin per game')
  axes.set_title(
    'Did a richer conference buy better football?\n'
    f'Schools that changed conference since 2023  (r = {correlation:.2f}, '
    f'n = {len(data)})',
    fontsize=12,
  )
  axes.grid(alpha=0.2, zorder=0)
  axes.legend(fontsize=8, loc='lower right')
  figure.tight_layout()

  path = config.FIGURES_DIR / filename
  figure.savefig(path, dpi=150)
  plt.close(figure)
  logger.info('Wrote %s', path)
  return str(path)


def travel_penalty_chart(
  by_shift: pd.DataFrame,
  within_team: dict[str, float] | None = None,
  filename: str = 'travel_timezone_penalty.png',
) -> str | None:
  """Charts away-game performance against time-zone shift.

  Args:
    by_shift (pd.DataFrame): Output of ``travel.performance_by_shift``.
    within_team (dict[str, float] | None): Output of
      ``travel.within_team_travel_effect``, annotated on the chart.
    filename (str): Output file name.

  Returns:
    str | None: Path written, or ``None`` when there is nothing to draw.
  """
  if by_shift.empty:
    logger.warning('Travel chart skipped: no data')
    return None
  data = by_shift[by_shift['games'] >= 10].copy()
  if data.empty:
    logger.warning('Travel chart skipped: every bucket is too small')
    return None

  figure, axes = plt.subplots(figsize=(11, 6.5))
  colors = [
    '#c62828' if shift >= 2 else '#1565c0' if shift > 0 else '#6a6a6a'
    for shift in data['shift']
  ]
  axes.bar(
    data['shift'],
    data['mean_margin'],
    color=colors,
    edgecolor='white',
    zorder=2,
  )
  for row in data.itertuples():
    offset = 0.6 if row.mean_margin >= 0 else -1.4
    axes.annotate(
      f'{row.mean_margin:+.1f}\nn={row.games}',
      (row.shift, row.mean_margin + offset),
      ha='center',
      fontsize=8,
    )
  axes.axhline(0, color='black', linewidth=1)
  # Leave room for the value labels above and below the bars.
  low = float(min(data['mean_margin'].min(), 0.0))
  high = float(max(data['mean_margin'].max(), 0.0))
  axes.set_ylim(low - 0.28 * (high - low) - 1, high + 0.22 * (high - low) + 1)
  axes.set_xticks(data['shift'])
  axes.set_xticklabels(
    [
      'same zone' if s == 0 else f'{abs(int(s))} {"east" if s > 0 else "west"}'
      for s in data['shift']
    ]
  )
  axes.set_xlabel('Time zones travelled (negative is westward)')
  axes.set_ylabel('Mean point margin')
  title = 'Does travelling east cost you points?'
  if within_team:
    title += (
      f'\nWithin-team penalty for trips of 2+ zones east: '
      f'{within_team["penalty"]:+.1f} points '
      f'({int(within_team["teams"])} team-seasons)'
    )
  axes.set_title(title, fontsize=12)
  axes.grid(alpha=0.2, axis='y', zorder=0)
  figure.tight_layout()

  path = config.FIGURES_DIR / filename
  figure.savefig(path, dpi=150)
  plt.close(figure)
  logger.info('Wrote %s', path)
  return str(path)
