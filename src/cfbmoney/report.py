"""Renders the markdown research report."""

from __future__ import annotations

import datetime
import logging
import pathlib

import pandas as pd

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


def _flow_section(
  comparison: pd.DataFrame,
  overlap: float | None,
  top_n: int = 14,
) -> list[str]:
  """Builds the money-in versus money-out comparison section."""
  lines = [
    'Revenue is money **coming in**; expenses are money **going '
    'out**. They are not the same question:',
    '',
    '- Revenue is partly a *reward* for winning - ticket sales, '
    'donations and playoff payouts all follow success. A high '
    'correlation there is partly reverse causation.',
    '- Spending is closer to an *input*: what the program chose to '
    'pay for coaches, staff, recruiting and running the team.',
    '',
  ]
  if overlap is not None:
    lines += [
      f'In practice the two move together: the correlation between '
      f'log revenue and log spending is **{overlap:.2f}**. Rich '
      f'programs spend more, so neither variable can fully be '
      f'untangled from the other - but the ranking below shows which '
      f'one tracks results more closely.',
      '',
    ]
  if comparison.empty:
    return lines + ['_No comparison could be computed._', '']

  lines += [
    '| Money metric | In/Out | Performance metric | n | r | R² |',
    '| --- | :---: | --- | ---: | ---: | ---: |',
  ]
  for row in comparison.head(top_n).itertuples():
    label = _MONEY_LABELS.get(row.money_metric, row.money_metric)
    flow = 'IN' if row.money_flow == 'in' else 'OUT'
    lines.append(
      f'| {label} | {flow} | '
      f'{row.performance_metric.replace("_", " ")} | {row.n} | '
      f'{row.pearson_r:+.3f} | {row.r_squared:.3f} |'
    )
  lines.append('')
  return lines


def _correlation_section(correlations: pd.DataFrame) -> list[str]:
  """Builds the correlation table section."""
  if correlations.empty:
    return ['_No correlations could be computed._', '']
  lines = [
    '| Money metric | Performance metric | n | Pearson r | R² | '
    'Spearman ρ | p |',
    '| --- | --- | ---: | ---: | ---: | ---: | ---: |',
  ]
  for row in correlations.itertuples():
    label = _MONEY_LABELS.get(row.money_metric, row.money_metric)
    if row.log_scale:
      label += ' (log)'
    lines.append(
      f'| {label} | {row.performance_metric.replace("_", " ")} | '
      f'{row.n} | {row.pearson_r:+.3f} | {row.r_squared:.3f} | '
      f'{row.spearman_rho:+.3f} | {row.pearson_p:.4f}'
      f'{_stars(row.pearson_p)} |'
    )
  lines.append('')
  lines.append('`*` p<0.05, `**` p<0.01, `***` p<0.001')
  lines.append('')
  return lines


def _model_section(model: dict[str, object]) -> list[str]:
  """Builds the regression section."""
  coefficients: pd.DataFrame = model['coefficients']
  lines = [
    f'Outcome: **{model["outcome"]}**, predictor: '
    f'**{model["predictor"]}**, n = {model["n"]}, '
    f'R² = {model["r_squared"]:.3f} '
    f'(adjusted {model["adj_r_squared"]:.3f}).',
    '',
    '| Term | Estimate | Std error | t | p |',
    '| --- | ---: | ---: | ---: | ---: |',
  ]
  for row in coefficients.itertuples():
    lines.append(
      f'| {row.term} | {row.estimate:+.4f} | {row.std_error:.4f} | '
      f'{row.t_value:+.2f} | {row.p_value:.4f}{_stars(row.p_value)} |'
    )
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


def _residual_section(residuals: pd.DataFrame, top_n: int = 12) -> list[str]:
  """Builds the over/under-performance tables."""
  if residuals.empty:
    return []
  lines = [
    '**Beating their budget**',
    '',
    '| Program | Conf | Football rev | Actual | Budget-predicted | Gap |',
    '| --- | --- | ---: | ---: | ---: | ---: |',
  ]
  predictor = [
    c
    for c in residuals.columns
    if c not in ('school', 'conference', 'actual', 'predicted', 'residual')
  ]
  money_column = predictor[0] if predictor else None
  for row in residuals.head(top_n).itertuples():
    money = getattr(row, money_column) if money_column else None
    lines.append(
      f'| {row.school} | {row.conference} | {_usd_millions(money)} | '
      f'{_pct(row.actual)} | {_pct(row.predicted)} | '
      f'{row.residual * 100:+.1f} pts |'
    )
  lines += ['', '**Falling short of their budget**', '']
  lines += [
    '| Program | Conf | Football rev | Actual | Budget-predicted | Gap |',
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
        'same discount, moved much more. See research_notes_2026.md '
        'for the sourcing.',
        '',
      ]

  lines += ['### Every school that moved', '']
  lines += [
    '| School | Move | Effective | Revenue change | Point margin change |',
    '| --- | --- | ---: | ---: | ---: |',
  ]
  for row in changes.sort_values(['move_season', 'school']).itertuples():
    pct = getattr(row, 'football_revenue_pct_change', float('nan'))
    margin = getattr(row, 'point_margin_per_game_change', float('nan'))
    lines.append(
      f'| {row.school} | {row.move} | {row.move_season} | '
      f'{"not yet filed" if pd.isna(pct) else f"{pct:+.1f}%"} | '
      f'{"n/a" if pd.isna(margin) else f"{margin:+.1f}"} |'
    )
  lines.append('')
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
    f'{len(merged)} teams**. Private universities are exempt from '
    'public-records law, so the missing rows are not missing at '
    'random: they skew private and wealthy. Read this section as '
    'suggestive.',
    '',
  ]

  rows = correlations[correlations['money_metric'] == 'head_coach_pay']
  margin = rows[rows['performance_metric'] == 'point_margin_per_game']
  if not margin.empty:
    row = margin.iloc[0]
    lines += [
      f'Across those {int(row.n)} teams, head coach pay correlates '
      f'**r = {row.pearson_r:+.2f}** with point margin per game '
      f'(p = {row.pearson_p:.3f}). That is a real but much weaker '
      'signal than total program spending, which is the more telling '
      'result: paying one person more matters far less than the scale '
      'of the operation behind them.',
      '',
    ]

  top = paid.nlargest(10, 'head_coach_pay')
  lines += [
    '| Coach | School | Total pay | Win% | Point margin |',
    '| --- | --- | ---: | ---: | ---: |',
  ]
  for row in top.itertuples():
    coach = getattr(row, 'head_coach', '') or ''
    lines.append(
      f'| {coach} | {row.school} | '
      f'{_usd_millions(row.head_coach_pay)} | '
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
      lines += [
        '### Who now travels further',
        '',
        'Average time zones crossed per away game, before and after the '
        'move. The old Pac-12 fit inside two zones; the Big Ten and ACC '
        'do not.',
        '',
        '| School | Move | Zones before | Zones after | Change | '
        'Away margin change |',
        '| --- | --- | ---: | ---: | ---: | ---: |',
      ]
      for row in movers.itertuples():
        lines.append(
          f'| {row.school} | {row.move} | '
          f'{row.mean_tz_shift_before:+.2f} | '
          f'{row.mean_tz_shift_after:+.2f} | '
          f'{row.tz_shift_change:+.2f} | '
          f'{row.away_margin_change:+.1f} |'
        )
      lines.append('')

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
  comparison: pd.DataFrame | None = None,
  revenue_spending_overlap: float | None = None,
  season_trend: pd.DataFrame | None = None,
  realignment_changes: pd.DataFrame | None = None,
  pac12_diaspora: pd.DataFrame | None = None,
  travel_by_shift: pd.DataFrame | None = None,
  travel_within_team: dict[str, float] | None = None,
  realignment_travel: pd.DataFrame | None = None,
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
    comparison: Output of
      :func:`cfbmoney.analyze.revenue_vs_spending`.
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

  lines = [
    f'# Money vs winning: the {season} college football season',
    '',
    f'_Generated {now}. Season {season}, '
    f'through week {week if week else "?"}; '
    f'teams have played {played.min():.0f}-{played.max():.0f} games._',
    '',
    '> [!WARNING]',
    '> Sample-size warning: this is an in-progress season. Two or '
    'three games per team is not enough to separate skill from luck. '
    'Treat every coefficient below as directional until November.',
    '',
    '## What is being measured',
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

  lines += ['## The richest programs and what they have done so far', '']
  lines += _leaderboard_section(merged)

  lines += ['## Spending versus revenue: which one tracks winning?', '']
  lines += _flow_section(
    comparison if comparison is not None else pd.DataFrame(),
    revenue_spending_overlap,
  )

  if season_trend is not None and not season_trend.empty:
    lines += [
      '## The same question across four seasons',
      '',
      'A three-game sample cannot settle anything, so the table below '
      'repeats the headline correlation on completed seasons. The '
      'in-progress season is marked.',
      '',
      '| Season | Teams | r (log football revenue vs win%) | R² |',
      '| ---: | ---: | ---: | ---: |',
    ]
    latest = int(season_trend['season'].max())
    for row in season_trend.itertuples():
      marker = ' (in progress)' if int(row.season) == latest else ''
      lines.append(
        f'| {int(row.season)}{marker} | {row.n} | '
        f'{row.pearson_r:+.3f} | {row.r_squared:.3f} |'
      )
    lines.append('')

  if realignment_changes is not None and not realignment_changes.empty:
    lines += ['## What happened to the schools that switched conference', '']
    lines += _realignment_section(
      realignment_changes,
      pac12_diaspora if pac12_diaspora is not None else pd.DataFrame(),
    )

  coach_lines = _coach_pay_section(merged, correlations)
  if coach_lines:
    lines += ['## What the head coach is paid', '']
    lines += coach_lines

  if travel_by_shift is not None and not travel_by_shift.empty:
    lines += ['## Travel, time zones and the cost of flying east', '']
    lines += _travel_section(
      travel_by_shift, travel_within_team, realignment_travel
    )

  lines += ['## Every money metric against every performance metric', '']
  lines += _correlation_section(correlations)

  if model:
    lines += [
      '## Regression: money with conference fixed effects',
      '',
      'Conference dummies absorb the media-rights advantage, so the '
      'money coefficient answers a narrower question: *within the '
      'same league, does the bigger budget win more?*',
      '',
    ]
    lines += _model_section(model)
    lines += ['### Overperformers and underperformers', '']
    lines += _residual_section(model['residuals'])

  if not conference.empty:
    lines += ['## Conference summary', '']
    header = '| Conference | Teams | Median football rev | '
    header += 'Median dept rev | Mean win% | Mean margin |'
    lines += [header, '| --- | ---: | ---: | ---: | ---: | ---: |']
    for row in conference.itertuples():
      lines.append(
        f'| {row.conference} | {getattr(row, "teams", "-")} | '
        f'{_usd_millions(getattr(row, "football_revenue", None))} | '
        f'{_usd_millions(getattr(row, "dept_total_revenue", None))} | '
        f'{_pct(getattr(row, "win_pct", None))} | '
        f'{getattr(row, "point_margin_per_game", float("nan")):+.1f} |'
      )
    lines.append('')

  if figures:
    lines += ['## Figures', '']
    for figure in figures:
      name = pathlib.Path(figure).name
      caption = name.replace('_', ' ').replace('.png', '')
      lines.append(f'![{caption}]({figure_prefix}{name})')
      lines.append('')

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
