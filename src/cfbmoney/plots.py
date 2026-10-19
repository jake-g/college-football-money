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


def _norm_coord(
  value: float, limits: tuple[float, float], is_log: bool
) -> float:
  """Maps a data coordinate into normalized [0, 1] axis space."""
  low, high = limits
  if is_log and value > 0 and low > 0 and high > 0:
    span = max(float(np.log10(high) - np.log10(low)), 1e-6)
    return float((np.log10(value) - np.log10(low)) / span)
  span = max(float(high - low), 1e-6)
  return float((value - low) / span)


def _label_box(
  nx: float,
  ny: float,
  ha: str,
  dx: int,
  dy: int,
  text_w: float,
  text_h: float,
  axes_w_pt: float,
  axes_h_pt: float,
) -> tuple[float, float, float, float]:
  """Computes normalized [0, 1] bounding box for an offset label."""
  ax_x = nx + dx / axes_w_pt
  ax_y = ny + dy / axes_h_pt
  x0 = ax_x - text_w if ha == 'right' else ax_x
  x1 = ax_x if ha == 'right' else ax_x + text_w
  return (x0, ax_y - 0.15 * text_h, x1, ax_y + 0.85 * text_h)


def _pick_label_offset(
  nx: float,
  ny: float,
  school: str,
  fontsize: int,
  axes_w_pt: float,
  axes_h_pt: float,
  placed_boxes: list[tuple[float, float, float, float]],
  all_points: list[tuple[float, float]],
) -> tuple[str, int, int, tuple[float, float, float, float]]:
  """Selects a label offset minimizing collisions with boxes and dots."""
  text_w = (len(school) * 0.56 * fontsize + 4.0) / axes_w_pt
  text_h = (1.35 * fontsize) / axes_h_pt
  dot_rx = 5.0 / axes_w_pt
  dot_ry = 5.0 / axes_h_pt
  sides = ('right', 'left') if nx > 0.78 else ('left', 'right')
  best_score = float('inf')
  best_choice: tuple[str, int, int, tuple[float, float, float, float]] = (
    sides[0],
    -6 if sides[0] == 'right' else 6,
    4,
    (nx, ny, nx + text_w, ny + text_h),
  )
  for dy in (4, -9, 12, -16, 20, -24, 28, -32, 36, -40, 44, -48):
    for side in sides:
      dx = -6 if side == 'right' else 6
      box = _label_box(
        nx, ny, side, dx, dy, text_w, text_h, axes_w_pt, axes_h_pt
      )
      x0, y0, x1, y1 = box
      score = abs(dy) * 0.08 + (0.6 if side != sides[0] else 0.0)
      if (ny > 0.90 and dy > 0) or (ny < 0.08 and dy < 0):
        score += 5.0
      if x0 < 0.01 or x1 > 0.99 or y0 < 0.02 or y1 > 0.97:
        score += 250.0
      for px0, py0, px1, py1 in placed_boxes:
        if x0 < px1 and x1 > px0 and y0 < py1 and y1 > py0:
          score += 500.0
      for pnx, pny in all_points:
        if abs(pnx - nx) < 1e-5 and abs(pny - ny) < 1e-5:
          continue
        if x0 - dot_rx < pnx < x1 + dot_rx and y0 - dot_ry < pny < y1 + dot_ry:
          score += 25.0
      if score < best_score:
        best_score = score
        best_choice = (side, dx, dy, box)
  return best_choice


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
  x_lim = axes.get_xlim()
  y_lim = axes.get_ylim()
  log_x = axes.get_xscale() == 'log'
  log_y = axes.get_yscale() == 'log'
  bbox = axes.get_position()
  fig_w, fig_h = axes.figure.get_size_inches()
  axes_w_pt = max(float(fig_w * bbox.width * 72.0), 150.0)
  axes_h_pt = max(float(fig_h * bbox.height * 72.0), 120.0)
  all_points = [
    (
      _norm_coord(float(getattr(r, x_column)) / scale_x, x_lim, log_x),
      _norm_coord(float(getattr(r, y_column)), y_lim, log_y),
    )
    for r in usable.itertuples()
  ]
  placed_boxes: list[tuple[float, float, float, float]] = []

  for row in labelled.sort_values(
    [x_column, y_column], ascending=[False, False]
  ).itertuples():
    x_val = float(getattr(row, x_column)) / scale_x
    y_val = float(getattr(row, y_column))
    nx = _norm_coord(x_val, x_lim, log_x)
    ny = _norm_coord(y_val, y_lim, log_y)
    ha, dx, dy, box = _pick_label_offset(
      nx,
      ny,
      row.school,
      fontsize,
      axes_w_pt,
      axes_h_pt,
      placed_boxes,
      all_points,
    )
    placed_boxes.append(box)
    arrow = (
      {
        'arrowstyle': '-',
        'color': '#888888',
        'lw': 0.6,
        'shrinkA': 0,
        'shrinkB': 3,
      }
      if abs(dy) >= 12
      else None
    )
    axes.annotate(
      row.school,
      (x_val, y_val),
      textcoords='offset points',
      xytext=(dx, dy),
      ha=ha,
      fontsize=fontsize,
      arrowprops=arrow,
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
  project: bool = False,
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
  drawn: list[tuple[plt.Axes, pd.DataFrame, str]] = []
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
      axes, log_x, data[performance_column].to_numpy(dtype=float), False
    )
    axes.set_title(f'{title}   (r = {correlation:.2f})')
    axes.set_xlabel('$ millions, log scale')
    axes.grid(alpha=0.2, which='both')
    drawn.append((axes, data, column))

  # Shade and annotate in a second pass so shared y-limits encompass
  # every subplot before _shade_quadrants freezes autoscaling.
  for axes, data, column in drawn:
    y_divider = (
      0.0
      if performance_column == 'point_margin_per_game'
      else float(data[performance_column].median())
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

  drawn: list[tuple[plt.Axes, pd.DataFrame]] = []
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
    partial = season == max(seasons)
    axes.set_title(
      f'{season}{" (in progress)" if partial else ""}\n'
      f'r = {correlation:.2f}, n = {len(group)}'
    )
    axes.set_xlabel(f'{_label(money_column)} ($M, log)')
    axes.grid(alpha=0.2, which='both')
    drawn.append((axes, group))

  # Shade quadrants and place labels after all panels have populated the
  # shared x/y limits so later seasons are never clipped.
  for axes, group in drawn:
    y_divider = (
      0.0
      if performance_column == 'point_margin_per_game'
      else float(group[performance_column].median())
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


def conference_money_box(
  frame: pd.DataFrame,
  money_column: str = 'football_expenses',
  season: int = config.DEFAULT_SEASON,
  filename: str | None = None,
) -> str | None:
  """Draws a box plot of money by conference with individual team points.

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
  tick_labels = [
    f'{c} (n={len(s)})' for c, s in zip(order, samples, strict=True)
  ]

  figure, axes = plt.subplots(figsize=(10.5, 6.2))
  boxes = axes.boxplot(
    samples, tick_labels=tick_labels, patch_artist=True, showfliers=False
  )
  for index, (patch, conference, sample) in enumerate(
    zip(boxes['boxes'], order, samples, strict=True), start=1
  ):
    color = CONFERENCE_COLORS.get(conference, '#888888')
    patch.set_facecolor(color)
    patch.set_alpha(0.65)
    jitter = np.linspace(-0.14, 0.14, len(sample)) if len(sample) > 1 else [0.0]
    axes.scatter(
      np.full(len(sample), index, dtype=float) + jitter,
      sample.sort_values(),
      s=26,
      color=color,
      edgecolors='white',
      linewidths=0.6,
      alpha=0.9,
      zorder=3,
    )
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
  project: bool = False,
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
  all_seasons: set[int] = set()

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
    all_seasons.update(seasons)
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
      all_seasons.add(next_season)
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

  if all_seasons:
    axes.set_xticks(sorted(all_seasons))
  axes.set_xlabel('Season')
  axes.set_ylabel('Correlation with win percentage')
  subtitle = (
    'Solid = completed seasons, dotted = in progress or projected'
    if project
    else 'Solid = completed seasons, dotted = in progress'
  )
  axes.set_title(f'Does money matter more over time?\n{subtitle}')
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
  _annotate_points(
    axes,
    data,
    'football_revenue_pct_change',
    'point_margin_per_game_change',
    annotate=data['school'].tolist(),
    max_labels=len(data),
    fontsize=8,
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
  same_zone = data.loc[data['shift'] == 0, 'mean_margin']
  if not same_zone.empty:
    baseline = float(same_zone.iloc[0])
    axes.axhline(
      baseline,
      color='#37474f',
      linestyle='--',
      linewidth=1.1,
      label=f'Same-zone road baseline ({baseline:+.1f} pts)',
      zorder=1,
    )
    axes.legend(fontsize=9, loc='lower left')
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


def schedule_split_chart(
  split: pd.DataFrame,
  filename: str = 'schedule_split.png',
) -> str | None:
  """Shows where the money advantage is won: in or out of conference.

  Left panel: how often the higher-spending team wins, by game type.
  Right panel: correlation of team margin with absolute spending versus
  spending relative to the conference, by game type.

  Args:
    split (pd.DataFrame): Output of
      :func:`cfbmoney.insights.schedule_split`.
    filename (str): Output filename.

  Returns:
    str | None: The path written, or ``None`` with nothing to plot.
  """
  if split.empty:
    return None
  seasons = split['season'].astype(int).tolist()
  x = np.arange(len(seasons))
  width = 0.38
  figure, (left, right) = plt.subplots(1, 2, figsize=(13, 5.2))
  latest = max(seasons)
  labels = [f'{s}*' if s == latest else str(s) for s in seasons]

  nonconf_bars = left.bar(
    x - width / 2,
    split['nonconf_fbs_richer_win'] * 100,
    width,
    color='#0033a0',
    label='Non-conference vs FBS',
  )
  conf_bars = left.bar(
    x + width / 2,
    split['conference_richer_win'] * 100,
    width,
    color='#c8102e',
    label='Conference games',
  )
  for bars in (nonconf_bars, conf_bars):
    for bar in bars:
      height = bar.get_height()
      if pd.notna(height):
        left.annotate(
          f'{height:.0f}%',
          (bar.get_x() + bar.get_width() / 2, height),
          textcoords='offset points',
          xytext=(0, 3),
          ha='center',
          fontsize=8,
        )
  left.axhline(50, color='black', linewidth=0.8, linestyle='--')
  left.set_xticks(x, labels)
  left.set_ylim(40, 92)
  left.set_xlabel('Season (* = in progress)')
  left.set_ylabel('Higher-spending team win rate (%)')
  left.set_title('How often does the bigger budget win?')
  left.legend(fontsize=9, loc='upper left')
  left.grid(alpha=0.2, axis='y')

  series = (
    ('nonconf_fbs_r_absolute', 'Non-conf, absolute $', '#0033a0', '-'),
    ('conference_r_absolute', 'Conference, absolute $', '#c8102e', '-'),
    ('conference_r_relative', 'Conference, $ vs league median', '#c8102e', ':'),
  )
  for column, label, color, style in series:
    right.plot(
      x,
      split[column],
      marker='o',
      color=color,
      linestyle=style,
      linewidth=2,
      label=label,
    )
  right.axhline(0, color='black', linewidth=0.8)
  right.set_xticks(x, labels)
  right.set_ylim(-0.08, 0.85)
  right.set_xlabel('Season (* = in progress)')
  right.set_ylabel('Correlation with team point margin')
  right.set_title('Absolute vs league-relative spending')
  right.legend(fontsize=9, loc='upper right')
  right.grid(alpha=0.2)
  figure.tight_layout()

  path = config.FIGURES_DIR / filename
  figure.savefig(path, dpi=150)
  plt.close(figure)
  logger.info('Wrote %s', path)
  return str(path)


def relative_spend_by_season(
  panel: pd.DataFrame,
  outcome: str = 'point_margin_per_game',
  filename: str | None = None,
) -> str | None:
  """Plots conference-relative spend vs margin, one panel per season.

  The within-league effect is the finding a school can act on, so this
  checks whether it holds in completed seasons and not just the small
  in-progress sample.

  Args:
    panel (pd.DataFrame): Multi-season frame with ``season``,
      ``conference`` and ``relative_spend``.
    outcome (str): Performance column.
    filename (str | None): Output filename override.

  Returns:
    str | None: The path written, or ``None`` with fewer than two seasons.
  """
  needed = ['season', 'school', 'conference', 'relative_spend', outcome]
  if not set(needed) <= set(panel.columns):
    return None
  data = panel[needed].dropna()
  data = data[data['relative_spend'] > 0]
  seasons = sorted(data['season'].unique())
  if len(seasons) < 2:
    return None
  data = data.assign(
    margin_vs_conf=data[outcome]
    - data.groupby(['season', 'conference'])[outcome].transform('mean')
  )

  figure, axes_list = plt.subplots(
    1,
    len(seasons),
    figsize=(5.2 * len(seasons), 6.0),
    sharey=True,
    sharex=True,
  )
  ticks = [0.5, 0.67, 1.0, 1.5, 2.0]
  drawn: list[tuple[plt.Axes, pd.DataFrame]] = []
  for axes, season in zip(axes_list, seasons, strict=True):
    group = data[data['season'] == season]
    axes.scatter(
      group['relative_spend'],
      group['margin_vs_conf'],
      s=42,
      alpha=0.8,
      c=[CONFERENCE_COLORS.get(c, '#888888') for c in group['conference']],
      edgecolors='white',
      linewidths=0.6,
      zorder=2,
    )
    x_log = np.log10(group['relative_spend'].to_numpy(dtype=float))
    y = group['margin_vs_conf'].to_numpy(dtype=float)
    slope, intercept = np.polyfit(x_log, y, 1)
    grid = np.linspace(x_log.min(), x_log.max(), 50)
    axes.plot(10**grid, slope * grid + intercept, color='black', lw=1.5)
    r = float(np.corrcoef(x_log, y)[0, 1])
    axes.set_xscale('log')
    axes.set_xticks(ticks, [f'{t:g}x' for t in ticks])
    axes.minorticks_off()
    axes.axvline(1, color='grey', linewidth=0.8, linestyle='--')
    axes.axhline(0, color='grey', linewidth=0.8, linestyle='--')
    partial = season == max(seasons)
    axes.set_title(
      f'{season}{" (in progress)" if partial else ""}\n'
      f'r = {r:+.2f}, n = {len(group)}'
    )
    axes.set_xlabel('Spending vs conference median (log)')
    axes.grid(alpha=0.2)
    drawn.append((axes, group))

  for axes, group in drawn:
    _annotate_points(
      axes,
      group,
      'relative_spend',
      'margin_vs_conf',
      annotate=config.REFERENCE_PROGRAMS,
      scale_x=1.0,
      fontsize=7,
    )
  axes_list[0].set_ylabel('Point margin per game vs conference average')
  figure.suptitle(
    'Within-league: out-spending your own conference, season by season',
    fontsize=13,
  )
  figure.tight_layout()

  path = config.FIGURES_DIR / (filename or 'relative_spend_by_season.png')
  figure.savefig(path, dpi=150)
  plt.close(figure)
  logger.info('Wrote %s', path)
  return str(path)


def box_score_markers_chart(
  markers: pd.DataFrame, filename: str | None = None
) -> str | None:
  """Compares what winning teams do with what money buys.

  Args:
    markers (pd.DataFrame): Output of
      :func:`cfbmoney.drivers.box_score_markers`.
    filename (str | None): Output filename override.

  Returns:
    str | None: The path written, or ``None`` with no data.
  """
  if markers is None or markers.empty:
    return None
  data = markers.iloc[::-1]
  positions = np.arange(len(data))
  height = 0.38
  figure, axes = plt.subplots(figsize=(10.5, 0.58 * len(data) + 1.8))
  bars_margin = axes.barh(
    positions + height / 2,
    data['r_margin'],
    height,
    color='#1565c0',
    label='r with point margin (what winners do)',
  )
  bars_money = axes.barh(
    positions - height / 2,
    data['r_money'],
    height,
    color='#9e9e9e',
    label='r with football spending (what money buys)',
  )
  for bars in (bars_margin, bars_money):
    for bar in bars:
      val = bar.get_width()
      if pd.notna(val):
        dx = 4 if val >= 0 else -4
        axes.annotate(
          f'{val:+.2f}',
          (val, bar.get_y() + bar.get_height() / 2),
          textcoords='offset points',
          xytext=(dx, 0),
          va='center',
          ha='left' if val >= 0 else 'right',
          fontsize=7.5,
        )
  axes.set_yticks(positions, data['label'])
  axes.axvline(0, color='black', linewidth=0.8)
  axes.set_xlim(-1.05, 1.05)
  axes.set_xlabel('Pearson r, completed seasons pooled')
  axes.set_title(
    'Box-score markers of a good team, and how much money explains'
  )
  axes.grid(axis='x', alpha=0.2)
  axes.legend(loc='lower right', fontsize=8)
  figure.tight_layout()

  path = config.FIGURES_DIR / (filename or 'box_score_markers.png')
  figure.savefig(path, dpi=150)
  plt.close(figure)
  logger.info('Wrote %s', path)
  return str(path)


def season_trajectory_chart(
  weekly: pd.DataFrame, season: int, filename: str | None = None
) -> str | None:
  """Plots the money signal week by week for every season.

  Args:
    weekly (pd.DataFrame): Output of :func:`cfbmoney.trends.week_by_week`.
    season (int): The in-progress season, drawn bold.
    filename (str | None): Output filename override.

  Returns:
    str | None: The path written, or ``None`` with no data.
  """
  if weekly is None or weekly.empty:
    return None
  figure, (left, right) = plt.subplots(1, 2, figsize=(13.0, 5.2))
  past_styles = [
    ('#78909c', '--'),
    ('#455a64', '-.'),
    ('#1565c0', '-'),
    ('#2e7d32', ':'),
  ]
  seasons = sorted(weekly['season'].unique())
  completed = weekly[weekly['season'] != season]
  if not completed.empty:
    band = completed.groupby('week')['r_margin'].agg(['min', 'max'])
    left.fill_between(
      band.index,
      band['min'],
      band['max'],
      color='#90a4ae',
      alpha=0.15,
      zorder=1,
    )
    conf_completed = completed[completed['conf_games'] >= 20]
    if not conf_completed.empty:
      cband = conf_completed.groupby('week')['richer_win_conf'].agg(
        ['min', 'max']
      )
      right.fill_between(
        cband.index,
        cband['min'],
        cband['max'],
        color='#90a4ae',
        alpha=0.15,
        zorder=1,
      )
  for index, year in enumerate(seasons):
    group = weekly[weekly['season'] == year]
    current = year == season
    pcolor, pstyle = past_styles[index % len(past_styles)]
    style = {
      'color': '#c62828' if current else pcolor,
      'linestyle': '-' if current else pstyle,
      'linewidth': 3.0 if current else 1.7,
      'marker': 'o' if current else None,
      'label': f'{year}{" (in progress)" if current else ""}',
      'zorder': 3 if current else 2,
    }
    left.plot(group['week'], group['r_margin'], **style)
    conf = group[group['conf_games'] >= 20]
    right.plot(conf['week'], conf['richer_win_conf'], **style)
  left.set_title('Spending vs point margin to date (r)')
  left.set_xlabel('Week')
  left.set_ylabel('Pearson r, log spending vs margin per game')
  right.set_title('Richer team win rate, conference games to date')
  right.set_xlabel('Week')
  right.set_ylabel('Share of conference games won by the bigger budget')
  right.axhline(0.5, color='grey', linewidth=0.8, linestyle='--')
  right.yaxis.set_major_formatter(
    matplotlib.ticker.PercentFormatter(xmax=1.0, decimals=0)
  )
  for axes in (left, right):
    axes.grid(alpha=0.2)
    axes.legend(fontsize=8)
  figure.suptitle(
    'Same week, different seasons: money peaks in September and fades',
    fontsize=13,
  )
  figure.tight_layout()

  path = config.FIGURES_DIR / (filename or 'season_trajectory.png')
  figure.savefig(path, dpi=150)
  plt.close(figure)
  logger.info('Wrote %s', path)
  return str(path)


def _save(figure: plt.Figure, name: str) -> str:
  """Writes a figure to the figures directory and closes it."""
  path = config.FIGURES_DIR / name
  figure.savefig(path, dpi=150)
  plt.close(figure)
  logger.info('Wrote %s', path)
  return str(path)


def budget_tiers_chart(
  tiers: pd.DataFrame, season: int, filename: str | None = None
) -> str | None:
  """Shows win% and margin by budget quintile: the shape of the curve.

  Args:
    tiers (pd.DataFrame): Output of :func:`cfbmoney.insights.budget_tiers`.
    season (int): The in-progress season.
    filename (str | None): Output filename override.

  Returns:
    str | None: The path written, or ``None`` with no data.
  """
  if tiers is None or tiers.empty:
    return None
  periods = [p for p in ('completed', str(season)) if p in set(tiers['period'])]
  if not periods:
    return None
  figure, (left, right) = plt.subplots(1, 2, figsize=(13.0, 5.4))
  width = 0.8 / len(periods)
  colors = {'completed': '#546e7a', str(season): '#c62828'}
  for offset, period in enumerate(periods):
    group = tiers[tiers['period'] == period].sort_values('tier')
    positions = group['tier'] + (offset - (len(periods) - 1) / 2) * width
    label = (
      'completed seasons pooled'
      if period == 'completed'
      else f'{season} (in progress)'
    )
    win_bars = left.bar(
      positions, group['win_pct'], width, color=colors[period], label=label
    )
    margin_bars = right.bar(
      positions, group['margin'], width, color=colors[period], label=label
    )
    for bar, val in zip(win_bars, group['win_pct'], strict=True):
      if pd.notna(val):
        left.annotate(
          f'{val:.0%}',
          (bar.get_x() + bar.get_width() / 2, val),
          textcoords='offset points',
          xytext=(0, 3),
          ha='center',
          fontsize=7.5,
        )
    for bar, val in zip(margin_bars, group['margin'], strict=True):
      if pd.notna(val):
        dy = 3 if val >= 0 else -10
        right.annotate(
          f'{val:+.1f}',
          (bar.get_x() + bar.get_width() / 2, val),
          textcoords='offset points',
          xytext=(0, dy),
          ha='center',
          fontsize=7.5,
        )
  reference = tiers[tiers['period'] == periods[0]].sort_values('tier')
  ticks = [
    f'{int(t)}\n${b / 1e6:.0f}M'
    for t, b in zip(reference['tier'], reference['median_budget'], strict=True)
  ]
  for axes in (left, right):
    axes.set_xticks(reference['tier'], ticks)
    axes.set_xlabel('Budget tier (1 = poorest fifth) and median budget')
    axes.grid(axis='y', alpha=0.2)
    axes.legend(fontsize=8)
  left.set_ylim(0, 0.90)
  left.set_ylabel('Mean win percentage')
  left.yaxis.set_major_formatter(
    matplotlib.ticker.PercentFormatter(xmax=1.0, decimals=0)
  )
  left.axhline(0.5, color='grey', linewidth=0.8, linestyle='--')
  left.set_title('Win percentage by budget tier')
  low_m = float(tiers['margin'].min())
  high_m = float(tiers['margin'].max())
  right.set_ylim(low_m - 3.5, high_m + 3.5)
  right.set_ylabel('Mean point margin per game')
  right.axhline(0, color='black', linewidth=0.8)
  right.set_title('Point margin by budget tier')
  figure.suptitle(
    'Dose-response: the richest fifth pulls away from everyone else',
    fontsize=13,
  )
  figure.tight_layout()
  return _save(figure, filename or 'budget_tiers.png')


def close_games_chart(
  close: pd.DataFrame, season: int, filename: str | None = None
) -> str | None:
  """Compares the bigger budget's win rate in tight games and blowouts.

  Args:
    close (pd.DataFrame): Output of :func:`cfbmoney.gameday.close_games`.
    season (int): The in-progress season, highlighted.
    filename (str | None): Output filename override.

  Returns:
    str | None: The path written, or ``None`` with no data.
  """
  if close is None or close.empty:
    return None
  data = close.sort_values('season')
  positions = np.arange(len(data))
  width = 0.27
  figure, axes = plt.subplots(figsize=(10.0, 5.2))
  series = (
    ('richer_win_blowout', 'Blowouts (17+ points)', '#1565c0'),
    ('richer_win_all', 'All FBS games', '#78909c'),
    ('richer_win_close', 'One-score games (8 or fewer)', '#ef6c00'),
  )
  for offset, (column, label, color) in enumerate(series):
    bars = axes.bar(
      positions + (offset - 1) * width,
      data[column],
      width,
      color=color,
      label=label,
    )
    for bar, value in zip(bars, data[column], strict=True):
      if pd.notna(value):
        axes.annotate(
          f'{value:.0%}',
          (bar.get_x() + bar.get_width() / 2, value),
          textcoords='offset points',
          xytext=(0, 3),
          ha='center',
          fontsize=8,
        )
  labels = [
    f'{int(s)}{" (in progress)" if int(s) == season else ""}'
    for s in data['season']
  ]
  axes.set_xticks(positions, labels)
  axes.axhline(0.5, color='grey', linewidth=0.8, linestyle='--')
  axes.set_ylim(0, 1)
  axes.yaxis.set_major_formatter(
    matplotlib.ticker.PercentFormatter(xmax=1.0, decimals=0)
  )
  axes.set_ylabel('Share of games won by the bigger budget')
  axes.set_title(
    'Money decides blowouts; one-score games are closer to a coin flip'
  )
  axes.grid(axis='y', alpha=0.2)
  axes.legend(fontsize=8, loc='upper right')
  figure.tight_layout()
  return _save(figure, filename or 'close_games.png')


def pythagorean_chart(
  teams: pd.DataFrame, season: int, filename: str | None = None
) -> str | None:
  """Plots actual against points-based expected win percentage.

  Teams above the diagonal have won more than their scoring says they
  should; the furthest from the line are labelled.

  Args:
    teams (pd.DataFrame): Per-team table from
      :func:`cfbmoney.gameday.pythagorean_luck`.
    season (int): Season year for the title and filename.
    filename (str | None): Output filename override.

  Returns:
    str | None: The path written, or ``None`` with no data.
  """
  if teams is None or teams.empty:
    return None
  data = teams.dropna(subset=['pythagorean_pct', 'win_pct'])
  figure, axes = plt.subplots(figsize=(8.5, 8.0))
  for conference, group in data.groupby('conference'):
    axes.scatter(
      group['pythagorean_pct'],
      group['win_pct'],
      s=60,
      alpha=0.85,
      label=conference,
      color=CONFERENCE_COLORS.get(conference, '#888888'),
      edgecolors='white',
      linewidths=0.8,
      zorder=2,
    )
  axes.plot([0, 1], [0, 1], color='black', linewidth=1.2, zorder=1)
  axes.fill_between(
    [0, 1], [0, 1], [1, 1], color=_GOOD_QUADRANT, alpha=0.05, zorder=0
  )
  axes.fill_between(
    [0, 1], [0, 0], [0, 1], color=_BAD_QUADRANT, alpha=0.05, zorder=0
  )
  axes.text(
    0.03,
    0.96,
    'Lucky: record better than scoring',
    fontsize=9,
    color=_GOOD_QUADRANT,
    transform=axes.transAxes,
  )
  axes.text(
    0.97,
    0.03,
    'Unlucky: record worse than scoring',
    fontsize=9,
    color=_BAD_QUADRANT,
    ha='right',
    transform=axes.transAxes,
  )
  axes.set_xlim(0, 1)
  axes.set_ylim(0, 1)
  extremes = pd.concat(
    [data.nlargest(5, 'luck_wins'), data.nsmallest(5, 'luck_wins')]
  ).drop_duplicates('school')
  _annotate_points(
    axes,
    data,
    'pythagorean_pct',
    'win_pct',
    annotate=extremes['school'].tolist(),
    max_labels=len(extremes),
    fontsize=8,
  )
  formatter = matplotlib.ticker.PercentFormatter(xmax=1.0, decimals=0)
  axes.xaxis.set_major_formatter(formatter)
  axes.yaxis.set_major_formatter(formatter)
  axes.set_xlabel('Expected win percentage from points scored and allowed')
  axes.set_ylabel('Actual win percentage')
  axes.set_title(f'Who is outrunning their scoring - {season} season')
  axes.grid(alpha=0.2, zorder=0)
  axes.legend(
    fontsize=7,
    ncol=2,
    loc='upper left',
    bbox_to_anchor=(0.0, 0.94),
    framealpha=0.9,
  )
  figure.tight_layout()
  return _save(figure, filename or f'pythagorean_{season}.png')


def attendance_chart(
  frame: pd.DataFrame,
  attendance: pd.DataFrame,
  season: int,
  filename: str | None = None,
) -> str | None:
  """Plots average home crowd against football spending.

  Args:
    frame (pd.DataFrame): Merged analysis table for ``season``.
    attendance (pd.DataFrame): Output of
      :func:`cfbmoney.gameday.home_attendance`.
    season (int): Season year for the title and filename.
    filename (str | None): Output filename override.

  Returns:
    str | None: The path written, or ``None`` with no data.
  """
  if attendance is None or attendance.empty:
    return None
  crowd = attendance[attendance['season'] == season][['school', 'attendance']]
  data = frame[['school', 'conference', 'football_expenses']].merge(
    crowd, on='school', how='inner'
  )
  data = data[(data['football_expenses'] > 0) & (data['attendance'] > 0)]
  if len(data) < 5:
    return None
  figure, axes = plt.subplots(figsize=DEFAULT_FIGSIZE)
  for conference, group in data.groupby('conference'):
    axes.scatter(
      group['football_expenses'] / 1e6,
      group['attendance'] / 1e3,
      s=70,
      alpha=0.85,
      label=conference,
      color=CONFERENCE_COLORS.get(conference, '#888888'),
      edgecolors='white',
      linewidths=0.8,
      zorder=2,
    )
  axes.set_xscale('log')
  axes.set_yscale('log')
  log_x = np.log10(data['football_expenses'].to_numpy(dtype=float) / 1e6)
  log_y = np.log10(data['attendance'].to_numpy(dtype=float) / 1e3)
  slope, intercept = np.polyfit(log_x, log_y, 1)
  correlation = float(np.corrcoef(log_x, log_y)[0, 1])
  grid = np.linspace(log_x.min(), log_x.max(), 100)
  axes.plot(
    10**grid,
    10 ** (slope * grid + intercept),
    color='black',
    linewidth=1.8,
    label=f'fit over observed range (r = {correlation:.2f})',
    zorder=3,
  )
  scaled = data.assign(attendance_k=data['attendance'] / 1e3)
  _annotate_points(
    axes, scaled, 'football_expenses', 'attendance_k', scale_x=1e6
  )
  axes.set_xlabel('Football spending ($ millions, log scale)')
  axes.set_ylabel('Average home attendance (thousands, log scale)')
  plain = matplotlib.ticker.StrMethodFormatter('{x:,.0f}')
  for axis in (axes.xaxis, axes.yaxis):
    axis.set_major_formatter(plain)
    axis.set_minor_formatter(plain)
  axes.set_title(
    f'Crowd size tracks the budget almost one for one - {season} season'
  )
  axes.grid(alpha=0.2, which='both', zorder=0)
  axes.legend(fontsize=8, ncol=2, loc='lower right', framealpha=0.9)
  figure.tight_layout()
  return _save(figure, filename or f'attendance_vs_spending_{season}.png')
