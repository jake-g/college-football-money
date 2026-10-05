"""In-season trends: how 2026 compares with past seasons at the same week.

Every in-progress number in the report carries the same caveat: early
season schedules are full of non-conference mismatches, so money looks
stronger than it will by December.  This module removes the guesswork
by replaying completed seasons week by week:

* **Same-week comparison** - the money correlation and the richer
  team's win rate *through week N* in every season, so 2026 is judged
  against 2023-25 at the same point rather than against their finals.
* **Upsets** - games won by the team with less than half the
  opponent's budget, and how often that happens.
* **Expectation vs reality** - a forecast from last season's margin and
  this season's budget, fitted on completed seasons *at the same week*,
  applied to 2026.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

import numpy as np
import pandas as pd
from scipy import stats

from . import build
from . import drivers

logger = logging.getLogger(__name__)

MONEY = 'football_expenses'
MARGIN = 'point_margin_per_game'


def _season_money(panel: pd.DataFrame, season: int) -> pd.Series:
  """Returns positive football spending for one season keyed by school."""
  frame = panel[panel['season'] == season]
  spend = frame.set_index('school')[MONEY]
  spend = spend[spend > 0]
  return spend[~spend.index.duplicated()]


def _played(games: pd.DataFrame) -> pd.DataFrame:
  """Returns completed team-game rows with a ``margin`` and game type."""
  tagged = build.tag_conference_games(games)
  done = tagged[tagged['completed'].fillna(False).astype(bool)].dropna(
    subset=['points_for', 'points_against', 'week']
  )
  return done.assign(
    margin=done['points_for'] - done['points_against'],
    week=done['week'].astype(int),
  )


def _richer_win(rows: pd.DataFrame, spend: pd.Series) -> tuple[float, int]:
  """Returns the richer side's win rate and the number of games."""
  own = rows['school'].map(spend)
  opp = rows['opponent'].map(spend)
  usable = rows[
    own.notna() & opp.notna() & (own != opp) & (rows['margin'] != 0)
  ]
  if usable.empty:
    return float('nan'), 0
  richer = own[usable.index] > opp[usable.index]
  won = usable['margin'] > 0
  # Each game appears twice (once per team), so halve the count.
  return float((richer == won).mean()), int(len(usable) // 2)


def week_by_week(
  panel: pd.DataFrame,
  games_by_season: Mapping[int, pd.DataFrame],
  max_week: int | None = None,
) -> pd.DataFrame:
  """Replays every season cumulatively, one week at a time.

  Args:
    panel (pd.DataFrame): Multi-season frame with spending per season.
    games_by_season (Mapping[int, pd.DataFrame]): Long team-game frames.
    max_week (int | None): Last week to replay; defaults to each
      season's final week.

  Returns:
    pd.DataFrame: One row per season and week with ``r_margin`` (log
    spending vs margin per game to date), ``richer_win_conf`` and
    ``richer_win_nonconf`` (cumulative), ``conf_share`` (conference
    share of FBS-vs-FBS games to date) and ``teams``.
  """
  rows = []
  for season, games in sorted(games_by_season.items()):
    spend = _season_money(panel, season)
    if spend.empty or games.empty:
      continue
    played = _played(games)
    last = int(played['week'].max()) if not played.empty else 0
    if max_week is not None:
      last = min(last, max_week)
    for week in range(1, last + 1):
      to_date = played[played['week'] <= week]
      per_team = to_date.groupby('school')['margin'].mean()
      joined = pd.DataFrame({'m': per_team, 's': spend}).dropna()
      if len(joined) < 20:
        continue
      r_margin = float(
        stats.pearsonr(np.log10(joined['s']), joined['m']).statistic
      )
      conf = to_date[to_date['game_type'] == 'conference']
      nonconf = to_date[to_date['game_type'] == 'nonconf_fbs']
      conf_rate, conf_games = _richer_win(conf, spend)
      nonconf_rate, nonconf_games = _richer_win(nonconf, spend)
      fbs_games = conf_games + nonconf_games
      rows.append(
        {
          'season': int(season),
          'week': week,
          'teams': len(joined),
          'r_margin': r_margin,
          'richer_win_conf': conf_rate,
          'richer_win_nonconf': nonconf_rate,
          'conf_games': conf_games,
          'nonconf_games': nonconf_games,
          'conf_share': conf_games / fbs_games if fbs_games else np.nan,
        }
      )
  return pd.DataFrame(rows)


def same_week_comparison(
  weekly: pd.DataFrame, season: int, week: int
) -> pd.DataFrame:
  """Lines up every season at ``week`` next to its final value.

  Args:
    weekly (pd.DataFrame): Output of :func:`week_by_week`.
    season (int): The in-progress season.
    week (int): The in-progress season's latest completed week.

  Returns:
    pd.DataFrame: One row per season with ``r_at_week``,
    ``conf_share_at_week``, ``richer_win_conf_at_week`` and, for
    completed seasons, ``r_final`` and ``richer_win_conf_final``.
  """
  if weekly.empty:
    return pd.DataFrame()
  rows = []
  for year, group in weekly.groupby('season'):
    at = group[group['week'] <= week]
    if at.empty:
      continue
    point = at.iloc[-1]
    final = group.iloc[-1]
    rows.append(
      {
        'season': int(year),
        'week': int(point['week']),
        'r_at_week': float(point['r_margin']),
        'conf_share_at_week': float(point['conf_share']),
        'richer_win_conf_at_week': float(point['richer_win_conf']),
        'conf_games_at_week': int(point['conf_games']),
        'r_final': float(final['r_margin']) if year != season else np.nan,
        'richer_win_conf_final': (
          float(final['richer_win_conf']) if year != season else np.nan
        ),
      }
    )
  return pd.DataFrame(rows)


def upsets(
  panel: pd.DataFrame,
  games_by_season: Mapping[int, pd.DataFrame],
  week: int,
  ratio: float = 2.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
  """Finds wins by teams with a fraction of the opponent's budget.

  Args:
    panel (pd.DataFrame): Multi-season frame with spending per season.
    games_by_season (Mapping[int, pd.DataFrame]): Long team-game frames.
    week (int): Only games through this week count, so seasons are
      compared at the same point.
    ratio (float): Minimum budget ratio (richer / poorer) for a game
      to count as a money mismatch.

  Returns:
    tuple[pd.DataFrame, pd.DataFrame]: A per-season summary (mismatch
    games, upsets, upset rate) and every upset with the winner, loser,
    budgets, ratio, score and week.
  """
  summary_rows = []
  upset_rows = []
  for season, games in sorted(games_by_season.items()):
    spend = _season_money(panel, season)
    if spend.empty or games.empty:
      continue
    played = _played(games)
    played = played[played['week'] <= week]
    own = played['school'].map(spend)
    opp = played['opponent'].map(spend)
    # Keep one row per game: the poorer side's perspective.
    poorer = played[own.notna() & opp.notna() & (opp >= own * ratio)]
    poorer = poorer[poorer['margin'] != 0]
    wins = poorer[poorer['margin'] > 0]
    summary_rows.append(
      {
        'season': int(season),
        'mismatches': len(poorer),
        'upsets': len(wins),
        'upset_rate': len(wins) / len(poorer) if len(poorer) else np.nan,
      }
    )
    for row in wins.itertuples():
      upset_rows.append(
        {
          'season': int(season),
          'week': int(row.week),
          'winner': row.school,
          'winner_conf': row.conference,
          'loser': row.opponent,
          'winner_spend': float(spend[row.school]),
          'loser_spend': float(spend[row.opponent]),
          'ratio': float(spend[row.opponent] / spend[row.school]),
          'score': f'{int(row.points_for)}-{int(row.points_against)}',
          'game_type': row.game_type,
        }
      )
  summary = pd.DataFrame(summary_rows)
  details = pd.DataFrame(upset_rows)
  if not details.empty:
    details = details.sort_values(
      ['season', 'ratio'], ascending=[True, False]
    ).reset_index(drop=True)
  return summary, details


def upset_rate_test(summary: pd.DataFrame, season: int) -> dict[str, float]:
  """Tests the in-progress upset rate against past seasons pooled.

  Args:
    summary (pd.DataFrame): Per-season summary from :func:`upsets`.
    season (int): The in-progress season.

  Returns:
    dict[str, float]: Current and past rates plus a two-sided Fisher
    exact ``p``, or empty when either side has no games.
  """
  current = summary[summary['season'] == season]
  past = summary[summary['season'] < season]
  if current.empty or past.empty:
    return {}
  now_up = int(current['upsets'].sum())
  now_n = int(current['mismatches'].sum())
  past_up = int(past['upsets'].sum())
  past_n = int(past['mismatches'].sum())
  if not now_n or not past_n:
    return {}
  result = stats.fisher_exact(
    [[now_up, now_n - now_up], [past_up, past_n - past_up]]
  )
  return {
    'rate': now_up / now_n,
    'past_rate': past_up / past_n,
    'p': float(result.pvalue),
  }


def margin_to_date(
  games_by_season: Mapping[int, pd.DataFrame], week: int
) -> pd.DataFrame:
  """Returns each team's margin against FBS opponents through ``week``.

  FCS games are dropped: they are scheduled unevenly and won by about
  30 points, which would swamp a three- or four-game sample.

  Args:
    games_by_season (Mapping[int, pd.DataFrame]): Long team-game frames.
    week (int): Last week included.

  Returns:
    pd.DataFrame: ``season``, ``school``, ``fbs_margin`` and
    ``fbs_games``.
  """
  frames = []
  for season, games in sorted(games_by_season.items()):
    if games.empty:
      continue
    played = _played(games)
    played = played[
      (played['week'] <= week) & (played['game_type'] != 'nonconf_fcs')
    ]
    grouped = played.groupby('school')['margin'].agg(['mean', 'size'])
    frames.append(
      pd.DataFrame(
        {
          'season': int(season),
          'school': grouped.index,
          'fbs_margin': grouped['mean'].to_numpy(),
          'fbs_games': grouped['size'].to_numpy(),
        }
      )
    )
  if not frames:
    return pd.DataFrame()
  return pd.concat(frames, ignore_index=True)


def expectation_vs_reality(
  panel: pd.DataFrame,
  games_by_season: Mapping[int, pd.DataFrame],
  season: int,
  week: int,
  top_n: int = 8,
  min_games: int = 2,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
  """Compares each team with a same-week forecast from last year and budget.

  The forecast is fitted on completed seasons using their margin
  against FBS opponents *through the same week*, so early-season
  schedule quirks are baked into the expectation rather than mistaken
  for surprises.

  Args:
    panel (pd.DataFrame): Multi-season frame.
    games_by_season (Mapping[int, pd.DataFrame]): Long team-game frames.
    season (int): The in-progress season.
    week (int): The in-progress season's latest completed week.
    top_n (int): Rows in each list.
    min_games (int): Minimum FBS games played to be ranked.

  Returns:
    tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]: Biggest
    positive surprises, biggest disappointments, and fit statistics
    (``r_forecast`` between forecast and actual, coefficients, ``n``).
  """
  empty = pd.DataFrame()
  to_date = margin_to_date(games_by_season, week)
  if to_date.empty:
    return empty, empty, {}
  data = drivers.add_prior_margin(panel)
  data = data[data[MONEY] > 0].copy()
  data['log_money'] = np.log10(data[MONEY].astype(float))
  data = data.merge(to_date, on=['season', 'school'], how='inner')
  data = data[data['fbs_games'] >= min_games].dropna(
    subset=['prior_margin', 'log_money', 'fbs_margin']
  )
  train = data[data['season'] < season]
  test = data[data['season'] == season]
  if len(train) < 30 or len(test) < 10:
    return empty, empty, {}
  design = np.column_stack(
    [np.ones(len(train)), train['prior_margin'], train['log_money']]
  )
  beta, *_ = np.linalg.lstsq(design, train['fbs_margin'].to_numpy(), rcond=None)
  forecast = (
    beta[0] + beta[1] * test['prior_margin'] + beta[2] * test['log_money']
  )
  columns = [
    'school',
    'conference',
    MONEY,
    'prior_margin',
    'fbs_margin',
    'fbs_games',
  ]
  out = test[columns].assign(
    expected=forecast, surprise=test['fbs_margin'] - forecast
  )
  fit = {
    'n': float(len(out)),
    'r_forecast': float(stats.pearsonr(out['expected'], out['fbs_margin'])[0]),
    'coef_prior': float(beta[1]),
    'coef_money': float(beta[2]),
    'train_first': float(train['season'].min()),
    'train_last': float(train['season'].max()),
    'week': float(week),
  }
  better = out.nlargest(top_n, 'surprise').reset_index(drop=True)
  worse = out.nsmallest(top_n, 'surprise').reset_index(drop=True)
  return better, worse, fit
