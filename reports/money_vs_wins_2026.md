# Money vs winning: the 2026 college football season

_Generated 2026-11-01 12:14. Season 2026, through week 9; teams have played 8-9 games._

> [!WARNING]
> Sample-size warning: this is an in-progress season. Teams have played 8-9 games, which is not enough to fully separate skill from luck. Past the midpoint the 2026 numbers are firming up; completed seasons (2023-25) still carry the weight.

## Summary

**What 2026 is showing so far**

- **2026 is a normal season so far, not an unusually rich one.** Through week 9 the money correlation is +0.48, against +0.48 to +0.53 for 2023-25 at the same week. Past seasons faded by 12% as conference play took over; 2026 projects to about +0.42.
- **Biggest surprises against a same-week forecast:** Liberty (+25), UCLA (+23), New Mexico (+20). **Biggest disappointments:** UTEP (-22), Vanderbilt (-21), Stanford (-19) (points per game).
- **Mismatches hold, peers are coin flips.** Teams with half the opponent's budget have won 7.7% of such games (8 of 104), against 15.4% at the same point of 2023-25, p = 0.05. Inside leagues the budget edge is thinner than usual: the richer side has won 52.9% of 310 conference games, against 61.6% at the same week of 2023-25 (binomial p < 0.01).
- **The playoff field is cheaper than usual.** 4 of 14 teams with at most one loss come from the richest fifth of FBS (28.6%), against 45.9% at the same week of 2023-25. New Mexico ($14.7M) is the cheapest.

**Does money buy wins?**

- **Yes, money tracks results.** Log football spending correlates r = +0.48 with point margin across 135 FBS teams so far in 2026 (r = +0.40 to +0.46 in completed seasons).
- **The edge is biggest across leagues.** The bigger budget wins 74.7% of non-conference FBS games but only 61.1% of conference games.
- **Out-spending your own conference pays as much as raw dollars.** Spend relative to the conference median tracks margin at r = +0.41 over completed seasons, against +0.43 for absolute spend.
- **The return on money is concentrated at the top.** The richest fifth of FBS wins 66.7% of its games against 56.5% for the next fifth and 43.9% for the poorest; the top tier is +7.0 points per game clear of everyone below it.

**What else makes a good team?**

- **Last season is the best single predictor.** Last year's margin explains 30% of this year's, the budget 20%, both 35%; money still adds signal on top (t = 4.5).
- **Beating your budget is a repeatable trait.** Margin above the budget line carries over at r = +0.43 year to year: something the budget misses (coaching, development, unrecorded NIL money) persists. James Madison, Toledo, Oregon, Notre Dame beat their budget every year; Purdue, Stanford, Kent State, Massachusetts missed it every year.
- **Quarterback play is the clearest on-field marker.** Passer rating tracks margin at r = +0.73 but spending at only +0.34; every box-score marker tracks winning more tightly than spending.
- **No single spending line stands out.** Coaching, recruiting and operations budgets move together (r >= 0.77) and none adds signal once total spending is known. Head coach pay adds nothing beyond the budget (t = +0.8, n = 52).
- **Getting richer has not paid off quickly.** Budget changes between 2023 and 2025 are unrelated to margin changes (r = -0.05, n = 130).

**Luck, close games and crowds**

- **Money decides blowouts, not close games.** The bigger budget wins 78.5% of games decided by 17+ points but only 56.5% of one-score games in completed seasons.
- **Records outrunning the scoring in 2026:** Stanford (+2.3 wins), Marshall (+2.1 wins), UTSA (+1.8 wins). **Trailing it:** TCU (-2.1), Kansas (-1.9), Penn State (-1.9). Luck is unrelated to budget (r = -0.14 in completed seasons).
- **Money does not buy a home-field edge.** Teams are 10 points better at home than away, and that edge is uncorrelated with budget (r = -0.07).
- **Crowd size is the budget, measured live.** Log home attendance and log spending correlate +0.88; last season's crowd predicts this season's margin about as well as the budget does (r = +0.44 vs +0.45). Same-week crowds are -0.6% versus 2025 at the median school.

**Realignment and travel**

- **Realignment moved money without anyone playing a down.** Pac-12 leavers: +8.3% median football revenue; Oregon State and Washington State: -31.6%.
- **Long-haul movers are paying a road tax.** Across the 13 schools whose travel grew most, away margin changed -4.8 and home margin +2.2 points per game (road gap -6.9, 9 of 13 negative, p = 0.04).

## Contents

- [1. What 2026 is showing so far](#1-what-2026-is-showing-so-far)
- [2. Does money buy wins?](#2-does-money-buy-wins)
- [3. What separates good teams from bad](#3-what-separates-good-teams-from-bad)
- [4. Luck, close games and crowds](#4-luck-close-games-and-crowds)
- [5. Realignment and travel](#5-realignment-and-travel)
- [6. Roster economics: NIL and revenue sharing](#6-roster-economics-nil-and-revenue-sharing)
- [7. Reference tables](#7-reference-tables)
- [Data sources](#data-sources)
- [Caveats](#caveats-worth-repeating)

## 1. What 2026 is showing so far

### Is 2026 more money-driven than usual?

Every early-season number looks money-heavy because September is full of mismatches. The fair comparison is the same week of past seasons: here each season is replayed through week 9, next to where it finished.

| Season | r through week 9 | Final r | Conference share of FBS games | Richer team wins, conf games (to date) | Final |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2023 | +0.48 | +0.42 | 62.9% | 67.2% (290 games) | 63.9% |
| 2024 | +0.53 | +0.48 | 59.3% | 59.5% (264 games) | 60.6% |
| 2025 | +0.51 | +0.43 | 60.2% | 58.0% (269 games) | 58.8% |
| 2026 (in progress) | +0.48 | - | 64.6% | 52.9% (310 games) | - |

At week 9, 2026 sits at r = **+0.48**, right in line with 2023-25 at the same point (+0.48 to +0.53). Every past season peaked around weeks 3-4 and then faded as conference play took over. Applying their average fade projects 2026 to finish near **r = +0.42**, not the headline number at the top of this report.

Inside conference play, the bigger budget has won **52.9%** of 310 games so far, against 61.6% for 2023-25 at the same week. A 9-point gap on this many games is unlikely to be noise (binomial p < 0.01): the budget edge inside leagues is unusually thin this year.

![season trajectory](figures/season_trajectory.png)

### Surprises against a preseason forecast

A forecast built only from last season's margin and this season's budget. It is fitted on 2024-2025 margins *through week 9* against FBS opponents only, so early-season schedule quirks are part of the expectation and FCS blowouts do not count. It already tracks reality well (r = +0.60 across 133 teams), so the teams far off it are the real stories of the season.

**Ahead of forecast**

| Program | Conf | Football exp | Last season | FBS games | Forecast | Actual | Gap |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Liberty | Conference USA | $23.0M | -0.9 | 7 | -2.3 | +23.0 | **+25.3** |
| UCLA | Big Ten | $55.2M | -15.2 | 8 | -3.3 | +20.1 | **+23.4** |
| New Mexico | Mountain West | $14.7M | +5.4 | 7 | -2.3 | +17.4 | **+19.7** |
| Oregon State | Pac-12 | $23.8M | -11.2 | 7 | -6.5 | +12.3 | **+18.8** |
| Wake Forest | ACC | $39.4M | +5.3 | 8 | +3.5 | +21.2 | **+17.7** |
| LSU | SEC | $50.7M | +3.5 | 7 | +4.2 | +20.6 | **+16.4** |
| Massachusetts | MAC | $13.4M | -27.5 | 6 | -16.8 | -1.0 | **+15.8** |
| Oklahoma State | Big 12 | $32.8M | -19.2 | 7 | -8.0 | +7.6 | **+15.6** |

**Behind forecast**

| Program | Conf | Football exp | Last season | FBS games | Forecast | Actual | Gap |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| UTEP | Mountain West | $11.1M | -7.1 | 7 | -9.3 | -31.4 | **-22.2** |
| Vanderbilt | SEC | $44.1M | +17.5 | 7 | +9.3 | -11.3 | **-20.6** |
| Stanford | ACC | $36.0M | -10.3 | 8 | -3.7 | -22.5 | **-18.8** |
| California | ACC | $46.7M | -1.7 | 8 | +1.5 | -16.1 | **-17.7** |
| Georgia Tech | ACC | $42.7M | +8.1 | 7 | +5.1 | -11.6 | **-16.7** |
| Old Dominion | Sun Belt | $14.8M | +13.4 | 8 | +1.2 | -15.5 | **-16.7** |
| Rutgers | Big Ten | $75.9M | -3.2 | 7 | +3.7 | -12.9 | **-16.6** |
| San Diego State | Pac-12 | $22.3M | +12.1 | 8 | +3.0 | -13.0 | **-16.0** |

### Upsets: when the smaller budget wins

A money mismatch is a game against an FBS opponent with at least twice the football budget. Through week 9 of each season:

| Season | Mismatch games | Upsets | Upset rate |
| --- | ---: | ---: | ---: |
| 2023 | 122 | 18 | 14.8% |
| 2024 | 105 | 13 | 12.4% |
| 2025 | 105 | 20 | 19.0% |
| 2026 (in progress) | 104 | 8 | 7.7% |

2026 has produced **fewer upsets** than usual: 7.7% of mismatches against 15.4% for 2023-25 pooled (Fisher exact p = 0.05). Favourites in lopsided games are holding serve.

**Biggest 2026 upsets by budget gap**

| Week | Winner | Budget | Beat | Budget | Gap | Score |
| ---: | --- | ---: | --- | ---: | ---: | :---: |
| 1 | Massachusetts | $13.4M | Rutgers | $75.9M | 5.7x | 37-21 |
| 6 | Louisville | $30.7M | Florida State | $83.3M | 2.7x | 44-20 |
| 5 | UNLV | $20.9M | California | $46.7M | 2.2x | 39-31 |
| 8 | Virginia Tech | $37.8M | Clemson | $81.1M | 2.1x | 20-16 |
| 7 | BYU | $44.6M | Notre Dame | $93.3M | 2.1x | 28-24 |
| 3 | Toledo | $12.6M | Temple | $26.3M | 2.1x | 49-48 |
| 5 | Northwestern | $37.9M | Penn State | $77.4M | 2.0x | 34-13 |
| 8 | Northwestern | $37.9M | Rutgers | $75.9M | 2.0x | 42-14 |

### Who is still in the playoff picture

Teams with at most one loss through week 9, in each season. A playoff field is built from this group, so its budget profile is the simplest test of whether the top of the sport is bought: how many contenders come from the richest fifth of FBS, and how cheap the cheapest one is.

| Season | Contenders | From richest fifth | Median budget | Median budget, others | Cheapest contender | Finished <= 2 losses |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| 2023 | 18 | 11 | $59.1M | $24.7M | Toledo ($12.0M) | 16 of 18 |
| 2024 | 21 | 10 | $50.2M | $23.0M | Louisiana ($14.8M) | 15 of 21 |
| 2025 | 22 | 7 | $41.2M | $23.8M | North Texas ($15.4M) | 16 of 22 |
| 2026 (in progress) | 14 | 4 | $42.3M | $23.3M | New Mexico ($14.7M) | - |

The 2026 field is **cheaper than usual**: 4 of 14 contenders (28.6%) come from the richest fifth, against 45.9% at the same week of 2023-25. The median contender still spends 1.8x the median non-contender. In past seasons 77.0% of same-week contenders finished the regular season with two losses or fewer, so most of this list will still be standing in December.

**2026 contenders through week 9**

| Program | Conf | Football exp | Budget rank | Record | Margin/g |
| --- | --- | ---: | ---: | :---: | ---: |
| Miami | ACC | $88.1M | 3 | 8-0 | +29.9 |
| Utah | Big 12 | $41.4M | 45 | 8-0 | +23.0 |
| UCLA | Big Ten | $55.2M | 24 | 8-0 | +20.1 |
| Notre Dame | FBS Independents | $93.3M | 1 | 7-1 | +27.0 |
| Georgia | SEC | $71.1M | 11 | 7-1 | +26.1 |
| New Mexico | Mountain West | $14.7M | 96 | 7-1 | +23.1 |
| Wake Forest | ACC | $39.4M | 51 | 7-1 | +21.2 |
| Liberty | Conference USA | $23.0M | 73 | 7-1 | +20.2 |
| Indiana | Big Ten | $50.2M | 29 | 8-1 | +20.0 |
| Texas Tech | Big 12 | $39.7M | 50 | 7-1 | +14.5 |
| BYU | Big 12 | $44.6M | 39 | 7-1 | +13.6 |
| Boise State | Pac-12 | $25.8M | 70 | 7-1 | +12.2 |
| Kentucky | SEC | $43.3M | 41 | 7-1 | +8.1 |
| UTSA | American | $17.9M | 85 | 7-1 | +7.5 |

## 2. Does money buy wins?

### Spending versus revenue: which one tracks winning?

Revenue is money **coming in** and partly a *reward* for winning (tickets, donations, playoff payouts). Spending is money **going out** and closer to an *input* the program controls.

In practice they are nearly the same variable: log revenue and log spending correlate at **0.96**, so every money metric below tells essentially the same story. The table shows correlations with each outcome; the full table with p-values and Spearman rank correlations is in `data/processed/correlations_<season>.csv`.

| Money metric | n | Margin/g | Win% | Pts/g | Allowed/g |
| --- | ---: | ---: | ---: | ---: | ---: |
| 247 team talent composite | 19 | +0.57* | +0.54* | +0.46* | -0.44 |
| Football non-operating spend | 135 | +0.48*** | +0.39*** | +0.41*** | -0.38*** |
| Athletics dept revenue | 135 | +0.48*** | +0.38*** | +0.40*** | -0.38*** |
| Men's coaching payroll | 135 | +0.48*** | +0.39*** | +0.40*** | -0.38*** |
| Men's recruiting spend | 135 | +0.48*** | +0.42*** | +0.41*** | -0.37*** |
| Football expenses | 135 | +0.48*** | +0.38*** | +0.41*** | -0.36*** |
| Football revenue | 135 | +0.48*** | +0.38*** | +0.38*** | -0.39*** |
| Athletics dept expenses | 135 | +0.47*** | +0.38*** | +0.40*** | -0.37*** |
| Football spend per player | 135 | +0.46*** | +0.37*** | +0.40*** | -0.35*** |
| Avg men's head coach salary | 135 | +0.46*** | +0.36*** | +0.39*** | -0.35*** |
| Head coach total pay | 52 | +0.18 | +0.08 | -0.14 | -0.41** |

Money columns are log-scaled except the talent composite. `*` p<0.05, `**` p<0.01, `***` p<0.001.

![revenue vs spending point margin per game 2026](figures/revenue_vs_spending_point_margin_per_game_2026.png)

![football expenses vs point margin per game by season](figures/football_expenses_vs_point_margin_per_game_by_season.png)

### Budget tiers: the shape of the curve

A correlation says the relationship exists; the tiers show its shape. Teams are ranked into fifths by budget within each season, so tier 1 is always the poorest fifth of that year's FBS.

| Tier | Median budget | Win% (completed) | Margin/g (completed) | Win% (2026) | Margin/g (2026) | Team-seasons |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 (poorest fifth) | $11.0M | 43.9% | -3.7 | 42.5% | -3.2 | 80 |
| 2 (second fifth) | $15.2M | 48.4% | -0.5 | 50.5% | +0.6 | 78 |
| 3 (middle fifth) | $30.4M | 49.6% | +0.7 | 54.1% | +4.4 | 79 |
| 4 (fourth fifth) | $43.3M | 56.5% | +3.8 | 62.6% | +7.2 | 78 |
| 5 (richest fifth) | $62.0M | 66.7% | +10.8 | 65.4% | +11.4 | 79 |

Over completed seasons the poorest fifth (median $11.0M) wins 43.9% of its games and the richest fifth ($62.0M) wins 66.7%: a 15-point swing in margin per game. The curve is convex: the middle three tiers sit within 4.3 points of each other, then the richest fifth jumps +7.0 points clear of the next tier. Money buys most at the very top, where the budget pays for the depth that wins the back half of a schedule.

![budget tiers](figures/budget_tiers.png)

### Where the money edge is won: in or out of conference

The national correlation blends two different contests: **non-conference** games (often Power 4 vs Group of Five budgets) and **conference** games (peers sharing media revenue).

| Season | Non-conf FBS games | Richer team wins | Conf games | Richer team wins | Conf r, absolute $ | Conf r, $ vs league |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2023 | 202 | 71.8% | 541 | 63.9% | +0.15 | +0.35 |
| 2024 | 212 | 78.2% | 540 | 60.6% | +0.16 | +0.41 |
| 2025 | 203 | 74.2% | 559 | 58.8% | +0.12 | +0.34 |
| 2026 (in progress) | 174 | 77.6% | 326 | 52.9% | +0.09 | +0.29 |

Across completed seasons the bigger budget wins **74.7%** of non-conference FBS games but only **61.1%** of conference games. Inside a conference, raw dollars barely track margin (r = +0.14), whereas spending *relative to the league median* does (r = +0.36).

FCS games are excluded above; FBS teams won them by an average of **+32.0 points**.

![schedule split](figures/schedule_split.png)

### Within the league: out-spending your peers

Re-expressing spending as a multiple of the conference median and margin as points above the conference mean removes the SEC-vs-MAC gap to test whether *out-spending your own league* pays:

| Season | n | National r (absolute $) | Within-league r (relative $) | p (within) |
| --- | ---: | ---: | ---: | ---: |
| 2023 | 127 | +0.40 | +0.42 | 7e-07 |
| 2024 | 128 | +0.46 | +0.45 | 8e-08 |
| 2025 | 131 | +0.42 | +0.36 | 3e-05 |
| 2026 (in progress) | 133 | +0.46 | +0.30 | 0.0005 |

Over full seasons, out-spending your conference predicts margin as well as raw dollars do nationally (within r = +0.41 vs national +0.43).

**Biggest spenders relative to their Power 4 league**

| Program | Conf | Football exp | x league median | Record | Margin/g |
| --- | --- | ---: | ---: | :---: | ---: |
| Miami | ACC | $88.1M | 2.06x | 8-0 | +29.9 |
| Florida State | ACC | $83.3M | 1.95x | 3-5 | +1.8 |
| Clemson | ACC | $81.1M | 1.90x | 5-3 | +1.6 |
| Ohio State | Big Ten | $92.4M | 1.74x | 6-2 | +21.1 |
| TCU | Big 12 | $59.6M | 1.56x | 4-4 | +9.1 |
| Penn State | Big Ten | $77.4M | 1.46x | 4-4 | +10.4 |

**Smallest spenders relative to their Power 4 league**

| Program | Conf | Football exp | x league median | Record | Margin/g |
| --- | --- | ---: | ---: | :---: | ---: |
| Houston | Big 12 | $23.3M | 0.61x | 6-2 | +15.0 |
| Mississippi State | SEC | $37.6M | 0.65x | 4-4 | -1.5 |
| Maryland | Big Ten | $35.5M | 0.67x | 2-6 | -4.8 |
| Purdue | Big Ten | $37.2M | 0.70x | 3-5 | -2.6 |
| Kansas State | Big 12 | $27.1M | 0.71x | 4-4 | +9.9 |
| Northwestern | Big Ten | $37.9M | 0.71x | 6-2 | +14.9 |

OLS with 10 conference fixed effects (outcome **win_pct**, n = 135, R² = 0.174, adjusted 0.101):

| Term | Estimate | Std error | t | p |
| --- | ---: | ---: | ---: | ---: |
| log10(football_expenses) | +0.4948 | 0.1597 | +3.10 | 0.0024** |

Doubling the football budget within the same conference adds **+14.9 percentage points of win rate** (log10(2) = 0.301).

![relative spend by season](figures/relative_spend_by_season.png)

## 3. What separates good teams from bad

### Last season versus this budget

Before crediting the budget, compare it with the simplest baseline: last season's point margin.

| Season | n | r, last season's margin | r, football spending |
| --- | ---: | ---: | ---: |
| 2024 | 130 | +0.53 | +0.47 |
| 2025 | 131 | +0.56 | +0.43 |
| 2026 (in progress) | 133 | +0.52 | +0.49 |

Pooling 2024-2025, last season alone explains **30%** of margin variance, spending alone **20%**, and both together **35%**. Both remain significant in a joint model (t = 7.6 for prior margin, 4.5 for spending): each point of prior margin carries 0.44 points forward, and doubling the budget adds **+2.8 points per game** on top.

In 2026 to date, prior margin (+0.52) now out-predicts spending (+0.49): the usual late-season pattern once conference play has replaced September mismatches.

### Who beats their budget year after year

Each team gets a seasonal residual: actual point margin minus the margin expected for its budget. If beating the budget were pure luck, residuals would not correlate year to year.

| Season | n | r with previous season's residual |
| --- | ---: | ---: |
| 2024 | 130 | +0.41 |
| 2025 | 131 | +0.45 |
| 2026 (in progress) | 133 | +0.39 |

Across completed seasons the residual repeats at r = **+0.43** (~4 points carried over per 10 points of prior over-performance), capturing coaching, player development, scheme, and off-books NIL.

**Consistently beating their budget (points per game)**

| Program | Conf | Football exp | 2023 | 2024 | 2025 | Average | 2026 to date |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| James Madison | Sun Belt | $16.9M | +17.7 | +14.6 | +22.2 | **+18.2** | +19.5 |
| Toledo | MAC | $12.6M | +15.8 | +9.1 | +22.2 | **+15.7** | +13.4 |
| Oregon | Big Ten | $60.8M | +20.1 | +10.0 | +15.2 | **+15.1** | +1.7 |
| Notre Dame | FBS Independents | $93.3M | +14.2 | +14.9 | +13.3 | **+14.1** | +13.6 |
| Ohio State | Big Ten | $92.4M | +12.7 | +13.3 | +15.7 | **+13.9** | +7.8 |
| SMU | ACC | $45.3M | +19.8 | +11.8 | +6.1 | **+12.6** | +5.0 |
| Ohio | MAC | $10.8M | +10.7 | +16.7 | +9.6 | **+12.3** | +10.3 |
| Memphis | American | $22.0M | +9.6 | +12.0 | +11.0 | **+10.9** | +11.3 |

**Consistently missing their budget (points per game)**

| Program | Conf | Football exp | 2023 | 2024 | 2025 | Average | 2026 to date |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Purdue | Big Ten | $37.2M | -9.8 | -28.6 | -17.8 | **-18.7** | -9.2 |
| Stanford | ACC | $36.0M | -20.8 | -15.0 | -14.8 | **-16.9** | -23.3 |
| Kent State | MAC | $10.4M | -15.8 | -25.0 | -8.2 | **-16.3** | -13.4 |
| Massachusetts | MAC | $13.4M | -11.6 | -9.7 | -25.1 | **-15.5** | +6.3 |
| Michigan State | Big Ten | $48.2M | -19.5 | -13.1 | -11.9 | **-14.8** | -14.4 |
| Charlotte | American | $15.6M | -9.4 | -9.3 | -20.7 | **-13.1** | -19.8 |
| Temple | American | $26.3M | -16.7 | -17.6 | -4.2 | **-12.8** | -7.0 |
| Oklahoma State | Big 12 | $32.8M | -3.3 | -11.9 | -23.0 | **-12.8** | +8.3 |

Over-performers span budgets from Ohio and Toledo ($12.6M or less) to Notre Dame and Ohio State ($92.4M or more).

### On-field markers of a good team

Which on-field numbers separate winners from losers, and which of them does money buy? Each season stat is correlated with point margin and with football spending, pooling completed seasons (n = 393 team-seasons).

| Stat | r with point margin | r with spending |
| --- | ---: | ---: |
| Passer rating (offense) | +0.73 | +0.34 |
| Yards per carry (offense) | +0.57 | +0.16 |
| Sacks (defense) | +0.56 | +0.24 |
| Completion % (offense) | +0.55 | +0.31 |
| Rush yards per game (offense) | +0.53 | +0.10 |
| Interceptions caught (defense) | +0.50 | +0.14 |
| Tackles for loss (defense) | +0.48 | +0.15 |
| Interceptions thrown (offense) | -0.46 | -0.21 |
| Pass yards per game (offense) | +0.37 | +0.23 |
| Fumbles lost (offense) | -0.21 | -0.13 |

**Passer rating** is the clearest marker of a good team (r = +0.73), yet spending explains it only loosely (r = +0.34). The widest gap is rush yards per game: r = +0.53 with margin but +0.10 with spending. Every marker tracks winning more tightly than it tracks spending: money buys a better roster at the margin, but what the roster does on the field is mostly something else.

These are symptoms of a good team rather than independent causes: teams that lead run the ball late, and good defenses force interceptions.

> [!NOTE]
> Richer teams also play **tougher schedules**: spending correlates r = +0.41 with opponents' win percentage. Raw point margin therefore slightly *understates* what money buys.

![box score markers](figures/box_score_markers.png)

### Which spending line matters?

Each spending line is added to a regression that already controls for total football budget (|t| > 2 indicates independent signal):

| Spending line | n | Corr. with total budget | r with margin alone | Added coef (pts per SD) | t | R² gain |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Men's coaching payroll | 135 | 0.94 | +0.48 | +3.1 | +1.3 | +0.010 |
| Avg men's head coach salary | 135 | 0.84 | +0.46 | +2.1 | +1.3 | +0.010 |
| Avg men's assistant coach salary | 135 | 0.90 | +0.47 | +2.3 | +1.2 | +0.008 |
| Men's recruiting spend | 135 | 0.92 | +0.48 | +2.9 | +1.4 | +0.012 |
| Football game-day operations | 135 | 0.84 | +0.37 | -1.3 | -0.9 | +0.004 |
| Head coach total pay | 52 | 0.77 | +0.18 | +1.4 | +0.8 | +0.012 |

Every component correlates **0.77 or higher** with total budget, and none is significant once total budget is held fixed (max |t| = 1.4, Men's recruiting spend). Rich programs spend across the board, so overall scale—not a single line item—drives the correlation.

#### What the head coach is paid

Verified total pay is on file for **52 of 138 teams**. Public universities subject to open-records laws provide high-confidence, cited figures. Private institutions (e.g., USC, Notre Dame, Stanford, Miami, TCU, Baylor, SMU, Vanderbilt) are exempt from FOIA disclosure and remain marked as unverified with blank salaries rather than synthetic estimates.

Across those 52 teams, head coach pay correlates **r = +0.18** with point margin per game (p = 0.197), weaker than total spending. Part of that is the sample: 92% of the verified rows are Power 4 schools, which squeezes the spread in both pay and results. With the total budget in the model, coach pay adds nothing (see the spending-line table above).

| Coach | School | Total pay | Buyout | Win% | Point margin |
| --- | --- | ---: | ---: | ---: | ---: |
| Kirby Smart | Georgia | $13.3M | $105.1M | 87.5% | +26.1 |
| Ryan Day | Ohio State | $12.6M | $70.9M | 75.0% | +21.1 |
| Dabo Swinney | Clemson | $11.4M | $60.0M | 62.5% | +1.6 |
| Steve Sarkisian | Texas | $10.8M | $60.3M | 75.0% | +13.6 |
| Dan Lanning | Oregon | $10.4M | $56.7M | 62.5% | +11.9 |
| Kalen DeBoer | Alabama | $10.2M | $60.8M | 75.0% | +17.0 |
| Brian Kelly | LSU | $10.2M | $53.3M | 75.0% | +24.1 |
| Bill Belichick | North Carolina | $10.1M | $20.8M | 50.0% | +2.8 |
| Mark Stoops | Kentucky | $9.0M | $37.7M | 87.5% | +8.1 |
| Josh Heupel | Tennessee | $9.0M | $37.5M | 75.0% | +16.0 |

### Does getting richer help?

The cross-section says rich programs win. Does *getting* richer help? Comparing each school's 2023 and 2025 seasons (median budget change +7%), the budget change is unrelated to the margin change: r = **-0.05** (p = 0.59, n = 130).

Money appears to work through program scale built over many years - facilities, staff depth, recruiting pipelines - rather than a one-year raise. Two years of filings is a short window, so treat this as "no quick payoff yet" rather than "no payoff".

## 4. Luck, close games and crowds

### Luck: records that outrun the scoring

A team's record should follow its scoring. The Pythagorean expectation turns points for and against into an expected win percentage; the gap to the actual record is mostly the bounce of close games, and the question is whether the budget buys any of it.

| Season | Teams | r, expected vs actual win% | r, luck vs log budget | p |
| --- | ---: | ---: | ---: | ---: |
| 2023 | 130 | +0.92 | -0.04 | 0.63 |
| 2024 | 131 | +0.90 | -0.13 | 0.15 |
| 2025 | 133 | +0.91 | -0.25 | <0.01 |
| 2026 (in progress) | 135 | +0.87 | -0.17 | 0.05 |

Scoring explains the record well (r = +0.91 in completed seasons), so the residual is small but real. Luck does not follow the budget: luck correlates -0.14 with log spending across completed seasons, significant in 1 of 3. Whatever money buys, it is not the bounce of the ball.

**Luckiest and unluckiest records so far in 2026**

| Group | Program | Conf | Football exp | Record | Expected win% | Actual | Wins above expectation |
| --- | --- | --- | ---: | :---: | ---: | ---: | ---: |
| Lucky | Stanford | ACC | $36.0M | 4-5 | 19.2% | 44.4% | **+2.3** |
| Lucky | Marshall | Sun Belt | $13.6M | 5-3 | 36.4% | 62.5% | **+2.1** |
| Lucky | UTSA | American | $17.9M | 7-1 | 64.6% | 87.5% | **+1.8** |
| Lucky | Kent State | MAC | $10.4M | 3-6 | 14.3% | 33.3% | **+1.7** |
| Lucky | Kentucky | SEC | $43.3M | 7-1 | 66.2% | 87.5% | **+1.7** |
| Unlucky | TCU | Big 12 | $59.6M | 4-4 | 76.5% | 50.0% | **-2.1** |
| Unlucky | Kansas | Big 12 | $34.5M | 3-5 | 61.9% | 37.5% | **-1.9** |
| Unlucky | Penn State | Big Ten | $77.4M | 4-4 | 74.1% | 50.0% | **-1.9** |
| Unlucky | Nebraska | Big Ten | $70.6M | 5-3 | 84.9% | 62.5% | **-1.8** |
| Unlucky | Texas A&M | SEC | $60.2M | 4-4 | 72.2% | 50.0% | **-1.8** |

Stanford is 4-5 while scoring like a team that wins 19.2% of its games; TCU is 4-4 while scoring like one that wins 76.5%. Records like these tend to regress toward the scoring over the rest of the season.

![pythagorean 2026](figures/pythagorean_2026.png)

### Close games versus blowouts

Does the bigger budget win the tight games, or only the lopsided ones? Every FBS-vs-FBS game is split by its final margin: one-score (8 points or fewer) against blowouts (17 or more). Each season is counted through week 9.

| Season | FBS games | Richer team wins | One-score games | Richer wins (one-score) | Blowouts | Richer wins (blowouts) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2023 | 461 | 68.5% | 167 (36.3%) | 63.0% | 201 | 79.1% |
| 2024 | 445 | 67.4% | 173 (38.9%) | 56.6% | 192 | 78.6% |
| 2025 | 447 | 64.7% | 164 (36.7%) | 50.0% | 202 | 77.7% |
| 2026 (in progress) | 480 | 61.7% | 186 (38.8%) | 48.9% | 204 | 72.1% |

Across completed seasons the bigger budget wins **78.5%** of blowouts but only **56.5%** of one-score games. Money shows up as depth and talent that turn a close game into a comfortable one; once a game is actually close, the budget is nearly irrelevant to who wins it.

So far in 2026, 38.8% of FBS games have been one-score games against 37.3% at the same point of past seasons, and the richer side has won 48.9% of them (n = 186).

![close games](figures/close_games.png)

### Home field: does money buy a louder stadium?

Home advantage is measured within each team (its home margin minus its away margin against FBS opponents, neutral sites excluded) so a rich team's stronger roster is not mistaken for a louder stadium.

| Season | Home games | Home win rate | Home margin | Within-team home edge | r, home edge vs log budget | p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2023 | 452 | 59.3% | +4.4 | +7.7 | +0.21 | 0.02 |
| 2024 | 436 | 60.6% | +5.8 | +9.6 | -0.24 | <0.01 |
| 2025 | 441 | 62.6% | +6.8 | +12.0 | -0.18 | 0.04 |
| 2026 (in progress) | 472 | 63.1% | +6.9 | +12.4 | -0.01 | 0.91 |

The home side wins about 60.8% of games and teams average 10 points better at home than away, but that edge is unrelated to budget (mean r = -0.07, sign flipping year to year): a 100,000-seat stadium does not widen the home-field margin over a 25,000-seat one.

### Crowds: the live money signal

Attendance is the one scale metric that arrives live each week instead of two years late in a federal filing. Average home crowd per team (neutral sites excluded):

| Season | Teams | Mean home crowd | Median | r, log crowd vs log budget | r, log crowd vs margin |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2023 | 130 | 40,959 | 35,961 | +0.89 | +0.49 |
| 2024 | 131 | 40,657 | 34,623 | +0.89 | +0.51 |
| 2025 | 133 | 40,593 | 32,215 | +0.88 | +0.48 |
| 2026 (in progress) | 135 | 39,785 | 32,922 | +0.88 | +0.51 |

Log crowd size and log budget correlate at r = **+0.88**. Using *last* season's crowd (known before kickoff), crowd and budget predict margin almost equally over 2024-2025 (r = +0.44 vs +0.45, n = 261); in a joint model the budget keeps the edge (t = 2.5 for budget, 1.4 for crowd).

**Are crowds growing?** Same-week comparison (through week 9), mean home crowd across FBS: 2023: 41,161 > 2024: 40,923 > 2025: 40,825 > 2026: 39,539. School by school, the median change from 2025 is **-0.6%** (down, n = 136).

**Biggest crowd gains versus 2025**

| Program | Home games | 2025 crowd | 2026 crowd | Change |
| --- | ---: | ---: | ---: | ---: |
| Northwestern | 5 | 11,548 | 21,876 | **+89%** |
| Sam Houston | 3 | 5,304 | 9,350 | **+76%** |
| Massachusetts | 4 | 10,133 | 14,534 | **+43%** |
| New Mexico State | 3 | 9,544 | 13,242 | **+39%** |
| Miami (OH) | 4 | 11,996 | 15,074 | **+26%** |
| Temple | 5 | 19,716 | 24,270 | **+23%** |

**Biggest crowd losses versus 2025**

| Program | Home games | 2025 crowd | 2026 crowd | Change |
| --- | ---: | ---: | ---: | ---: |
| Eastern Michigan | 4 | 16,336 | 7,882 | **-52%** |
| Buffalo | 5 | 14,063 | 7,703 | **-45%** |
| Rice | 4 | 24,124 | 15,187 | **-37%** |
| South Alabama | 4 | 16,893 | 11,169 | **-34%** |
| Louisiana Tech | 4 | 25,284 | 17,978 | **-29%** |
| Washington State | 4 | 28,293 | 20,348 | **-28%** |

![attendance vs spending 2026](figures/attendance_vs_spending_2026.png)

## 5. Realignment and travel

### What happened to the schools that switched conference

Between 2023 and 2026 the sport redrew its map: **24 schools changed conference**. That is the closest thing this data has to a controlled experiment, because the money moved for reasons unrelated to recent on-field performance.

> [!IMPORTANT]
> Federal finance filings lag by two years, so 2024 is the newest money year on record. Schools that moved in 2024 have **one** post-move budget year (some, like Texas, show a 1-year dip off a pre-move 2023 contribution spike); 2026 movers have **none** and are left blank rather than filled with pre-move figures. On-field margin changes compare seasons before versus from the move year onward (including 2026 to date).

#### The Pac-12 breakup

Ten of the twelve 2023 Pac-12 members left. Two did not, and the gap between those two groups is the single starkest result in this project.

| School | Role | Football revenue before | After | Change | Point margin change |
| --- | --- | ---: | ---: | ---: | ---: |
| Arizona | left | $37.1M | $37.8M | +1.8% | -6.9 |
| Arizona State | left | $40.2M | $50.4M | +25.4% | +18.6 |
| California | left | $45.1M | $64.0M | +41.9% | -1.4 |
| Colorado | left | $64.7M | $69.3M | +7.2% | +4.8 |
| Oregon | left | $109.2M | $119.6M | +9.5% | -9.1 |
| Stanford | left | $33.7M | $36.0M | +6.7% | +4.4 |
| UCLA | left | $45.8M | $55.2M | +20.6% | -8.3 |
| USC | left | $74.9M | $74.0M | -1.1% | +2.6 |
| Utah | left | $72.8M | $95.9M | +31.8% | +11.4 |
| Washington | left | $127.8M | $121.0M | -5.3% | -7.6 |
| Oregon State | stayed behind | $47.4M | $32.6M | -31.2% | -12.9 |
| Washington State | stayed behind | $57.0M | $38.8M | -31.9% | -3.0 |
| Boise State | joined new Pac-12 | $41.1M | - | n/a | +1.0 |
| Colorado State | joined new Pac-12 | $19.6M | - | n/a | -1.8 |
| Fresno State | joined new Pac-12 | $18.3M | - | n/a | +3.3 |
| San Diego State | joined new Pac-12 | $27.5M | - | n/a | -7.1 |
| Texas State | joined new Pac-12 | $18.0M | - | n/a | -0.7 |
| Utah State | joined new Pac-12 | $17.4M | - | n/a | -4.3 |

Median revenue change for the schools that left: **+8.3%**. For the two left behind: **-31.6%**. Washington State and Oregon State lost roughly a third of their football revenue simply by losing their conference.

##### Realignment financial mechanics

Several leavers show modest 2024 revenue gains because they entered on reduced media shares (Oregon and Washington joined the Big Ten at ~$30M/yr vs ~$65M+ full shares for USC and UCLA) while absorbing exit settlements and cross-country travel costs:

| Financial impact | Reported figure | Scope | Confidence | Source |
| :--- | :--- | :--- | :--- | :--- |
| WSU/OSU Settlement | $65M Withheld | 10 Departing Schools | High | [The Athletic](https://theathletic.com/5155122/2023/12/21/pac-12-settlement-washington-state-oregon-state/) |
| B1G Media Deal | ~$1.1 - $1.2B/yr | Big Ten | High | [CBS Sports](https://www.cbssports.com/college-football/news/big-ten-reaches-seven-year-media-rights-deal-with-cbs-fox-and-nbc-worth-more-than-7-billion/) |
| Big 12 Media Deal | ~$380M/yr | Big 12 | High | [ESPN](https://www.espn.com/college-football/story/_/id/34907937/big-12-agrees-new-media-rights-deal-espn-fox-sports) |
| USC / UCLA B1G Share | Full Share (~$65M+) | USC, UCLA | High | [LA Times](https://www.latimes.com/sports/ucla/story/2022-06-30/ucla-usc-big-ten-conference-move) |
| Oregon / UW B1G Share | $30M, +$1M/yr | Oregon, Washington | High | [ESPN](https://www.espn.com/college-football/story/_/id/38135860/oregon-washington-join-big-ten-2024) |
| Increased Travel Costs | $4.6M to $5.8M | UCLA | High | [LA Times](https://www.latimes.com/sports/ucla/story/2022-12-14/ucla-big-ten-move-uc-regents-approval-travel-costs) |

#### The other schools that moved

| School | Move | Effective | Revenue change | Point margin change |
| --- | --- | ---: | ---: | ---: |
| Army | FBS Independents to American | 2024 | not yet filed | +8.5 |
| Oklahoma | Big 12 to SEC | 2024 | +1.1% | -15.4 |
| SMU | American to ACC | 2024 | +41.8% | -8.9 |
| Texas | Big 12 to SEC | 2024 | -14.4% | -3.7 |
| Massachusetts | FBS Independents to MAC | 2025 | not yet filed | +2.8 |
| Louisiana Tech | Conference USA to Sun Belt | 2026 | not yet filed | +11.6 |
| Northern Illinois | MAC to Mountain West | 2026 | not yet filed | -22.3 |
| UTEP | Conference USA to Mountain West | 2026 | not yet filed | -12.9 |

![pac12 diaspora](figures/pac12_diaspora.png)

![realignment money vs margin](figures/realignment_money_vs_margin.png)

### Travel, time zones and the cost of flying east

Realignment moved miles as well as money. A team flying east loses hours: a noon kickoff on the east coast is a 9am body clock for a team from California. The table below pools every completed game from 2023 to 2026 by how many time zones the team crossed.

| Travel | Games | Mean margin | Win rate |
| --- | ---: | ---: | ---: |
| 3 zones west | 65 | -1.6 | 42% |
| 2 zones west | 84 | -6.2 | 40% |
| 1 zone west | 459 | -5.6 | 37% |
| same zone | 1480 | -5.2 | 41% |
| 1 zone east | 445 | -3.7 | 42% |
| 2 zones east | 91 | -8.1 | 36% |
| 3 zones east | 67 | -8.5 | 36% |

> [!IMPORTANT]
> The raw split above is confounded. The teams that fly two or more zones east are disproportionately Group of Five programs taking a paycheque game at a blue blood, so they would have lost anyway. Comparing each team against **itself** - its own margin on long eastward trips versus its own margin on every other away game - the penalty is **-0.9 points** across 75 team-seasons (-4.7 on long eastward trips versus -3.9 on other away games).

#### Who now travels further

Average time zones crossed per away game, before and after the move. The old Pac-12 fit inside two zones; the Big Ten and ACC do not. Home margin is the control: a tougher new league lowers both, while a travel burden should only show up on the road.

| School | Move | Zones before | Zones after | Away margin change | Home margin change | Road gap change |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Stanford | Pac-12 to ACC | -0.20 | +2.12 | -9.5 | +17.6 | -27.1 |
| Arizona State | Pac-12 to Big 12 | -0.75 | +0.79 | +12.7 | +24.2 | -11.5 |
| California | Pac-12 to ACC | +0.50 | +2.00 | -5.6 | +3.1 | -8.7 |
| Colorado | Pac-12 to Big 12 | -0.33 | +1.00 | +7.3 | +3.3 | +4.0 |
| UCLA | Pac-12 to Big Ten | +0.33 | +1.47 | -10.3 | -11.5 | +1.2 |
| Colorado State | Mountain West to Pac-12 | -0.44 | +0.67 | -12.6 | +3.5 | -16.1 |
| Utah | Pac-12 to Big 12 | -0.40 | +0.67 | +18.2 | +5.7 | +12.5 |
| Arizona | Pac-12 to Big 12 | -0.33 | +0.71 | -15.6 | -2.8 | -12.8 |
| Washington | Pac-12 to Big Ten | +0.80 | +1.85 | -14.7 | -2.4 | -12.3 |
| USC | Pac-12 to Big Ten | +1.00 | +2.00 | +1.5 | +3.4 | -1.8 |
| Oregon | Pac-12 to Big Ten | +0.80 | +1.69 | -6.1 | -14.4 | +8.3 |
| Texas | Big 12 to SEC | +0.00 | +0.60 | -10.9 | -0.6 | -10.3 |
| San Diego State | Mountain West to Pac-12 | +0.41 | +1.00 | -16.3 | -0.5 | -15.7 |

Pooled over these 13 schools, away margin moved **-4.8** and home margin **+2.2** points per game. The road gap averaged -6.9 with 9 of 13 schools negative, and a one-sample t-test gives p = 0.04. Few games per school and different opponents each year keep the estimate rough, but the sign is now hard to dismiss.

![travel timezone penalty](figures/travel_timezone_penalty.png)

## 6. Roster economics: NIL and revenue sharing

Under the *House v. NCAA* settlement, schools may share up to ~$20.5M in athletics revenue with athletes in 2025-26 (~$21.32M in 2026-27).

> [!IMPORTANT]
> Revenue-sharing caps and 247Sports talent composites are public, but **per-school football allocations and NIL collective payrolls remain undisclosed.** Rather than fabricating synthetic estimates, per-school allocation (`football_allocation_est`) and roster payroll (`roster_payroll_est`) columns remain blank (`n/a`) until audited disclosures exist.

| Data point | Reported figure | Scope | Confidence | Source |
| :--- | :--- | :--- | :--- | :--- |
| Revenue-share cap | ~$20.5M (25-26), ~$21.32M (26-27) | Every school | High | [ESPN](https://www.espn.com/college-sports/story/_/id/40206364/ncaa-power-conferences-agree-settle-house-vs-ncaa-lawsuit) |
| Football share of cap | ~75% | League-wide rule of thumb | Low per school | [Yahoo Sports](https://sports.yahoo.com/college-sports-revenue-sharing-model/) |
| Collective budgets | $15M-$20M+ | Elite tier only | Medium | [On3](https://www.on3.com/nil/news/college-football-nil-collective-budgets/) |
| Roster valuations | $12M-$15M+ | Top 5 rosters | Medium | [On3](https://www.on3.com/nil/rankings/player/college/football/) |
| 2026 recruiting spend | $3M-$5M | Top 15 classes | Medium | [247Sports](https://247sports.com/college-football/recruiting/) |
| Per-school football allocation | not disclosed | — | — | — |

### Talent composite and the equal-cap paradox

Because the House revenue-share cap is uniform across institutions, nearly every Power 4 program will max out the same ~$16M football share. Competitive differentiation therefore shifts to third-party NIL collectives ($15M-$20M+ at top programs) and uncapped coaching, recruiting, and support budgets.

247Sports Team Talent Composite ratings are on file for **19 elite programs** only. Among them, talent tracks scoring (r = +0.461 with points per game, p = 0.047). With so few schools, all from the top of the sport, treat this as a hint rather than a result.

## 7. Reference tables

### The richest programs and what they have done

| # | Program | Conf | Football rev | Football exp | Dept rev | Record | Win% | Margin/g |
| ---: | --- | --- | ---: | ---: | ---: | :---: | ---: | ---: |
| 1 | Notre Dame | FBS Independents | $195.7M | $93.3M | $289.6M | 7-1 | 87.5% | +27.0 |
| 2 | Michigan | Big Ten | $175.3M | $61.7M | $236.4M | 5-3 | 62.5% | +4.9 |
| 3 | Texas | SEC | $171.9M | $70.4M | $343.1M | 6-2 | 75.0% | +13.6 |
| 4 | Tennessee | SEC | $162.5M | $61.2M | $285.4M | 6-2 | 75.0% | +16.0 |
| 5 | Ohio State | Big Ten | $160.5M | $92.4M | $295.3M | 6-2 | 75.0% | +21.1 |
| 6 | Penn State | Big Ten | $150.3M | $77.4M | $254.4M | 4-4 | 50.0% | +10.4 |
| 7 | Georgia | SEC | $149.3M | $71.1M | $233.5M | 7-1 | 87.5% | +26.1 |
| 8 | Alabama | SEC | $146.3M | $81.5M | $244.6M | 6-2 | 75.0% | +17.0 |
| 9 | Oklahoma | SEC | $126.2M | $71.2M | $234.4M | 4-4 | 50.0% | +1.2 |
| 10 | Nebraska | Big Ten | $122.3M | $70.6M | $205.8M | 5-3 | 62.5% | +16.8 |
| 11 | Auburn | SEC | $121.4M | $58.7M | $205.3M | 4-4 | 50.0% | -2.6 |
| 12 | Washington | Big Ten | $121.0M | $68.9M | $178.4M | 5-3 | 62.5% | +5.4 |
| 13 | Oregon | Big Ten | $119.6M | $60.8M | $167.1M | 5-3 | 62.5% | +11.9 |
| 14 | LSU | SEC | $117.6M | $50.7M | $223.5M | 6-2 | 75.0% | +24.1 |
| 15 | Florida | SEC | $113.4M | $51.8M | $199.2M | 5-3 | 62.5% | +7.5 |
| 16 | Wisconsin | Big Ten | $112.3M | $40.9M | $190.5M | 5-3 | 62.5% | +6.5 |
| 17 | Texas A&M | SEC | $108.5M | $60.2M | $235.5M | 4-4 | 50.0% | +9.4 |
| 18 | Iowa | Big Ten | $105.2M | $50.9M | $180.0M | 6-2 | 75.0% | +15.8 |
| 19 | Minnesota | Big Ten | $101.7M | $45.5M | $156.8M | 5-3 | 62.5% | +4.8 |
| 20 | Miami | ACC | $99.9M | $88.1M | $230.5M | 8-0 | 100.0% | +29.9 |

### Conference summary

| Conference | Teams | Median football exp | Median football rev | Median dept rev | Mean win% | Mean margin |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SEC | 16 | $58.0M | $110.9M | $204.9M | 64.1% | +8.8 |
| FBS Independents | 2 | $56.9M | $108.1M | $193.3M | 68.8% | +18.1 |
| Big Ten | 18 | $53.0M | $94.8M | $176.5M | 60.6% | +8.2 |
| ACC | 17 | $42.7M | $64.0M | $151.6M | 58.2% | +6.1 |
| Big 12 | 16 | $38.2M | $49.0M | $130.7M | 62.5% | +8.9 |
| Pac-12 | 8 | $21.9M | $23.1M | $72.8M | 49.1% | +1.6 |
| American | 14 | $19.5M | $19.5M | $62.8M | 51.1% | +1.4 |
| Mountain West | 10 | $13.1M | $13.2M | $50.4M | 48.5% | -0.2 |
| Sun Belt | 14 | $12.8M | $12.9M | $39.9M | 50.0% | +1.4 |
| Conference USA | 10 | $11.6M | $11.6M | $38.5M | 45.0% | -0.8 |
| MAC | 13 | $11.0M | $11.0M | $38.9M | 46.3% | -3.8 |

![football expenses by conference 2026](figures/football_expenses_by_conference_2026.png)

## Data sources

| Side | Source | Vintage |
| --- | --- | --- |
| Results, scores, stats | ESPN public API | live, 2026 |
| Football revenue/expenses, department revenue, average coach salaries | US Dept of Education EADA filings | report year 2025 |
| Head coach total pay | hand-compiled, per-row citations | 2026 |
| Revenue-share cap, roster payroll, team talent | House settlement reporting, 247Sports | 2026 |

> [!NOTE]
> Federal athletics finances are published on a lag, so the 2025 filings (academic year 2024-25) are the newest available. That is a feature here rather than a bug: past spending is a *leading* indicator of present results, so the direction of causation runs the right way.

## Caveats worth repeating

- **Public vs. private accounting**: EADA filings are self-reported, and many private schools book revenue to exactly equal expenses.
- **Reverse causation**: Football revenue partly reflects winning (tickets, donations, playoff payouts), so correlations are bidirectional.
- **Unrecorded NIL & revenue-share splits**: The House cap is public, but per-school football allocations and third-party NIL collectives are private.
- **Realignment labels**: Fixed effects use each school's 2026 conference; conference games are matched from same-season membership.
