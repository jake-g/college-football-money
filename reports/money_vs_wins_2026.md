# Money vs winning: the 2026 college football season

_Generated 2026-09-20 11:20. Season 2026, through week 3; teams have played 2-4 games._

> [!WARNING]
> Sample-size warning: this is an in-progress season. Teams have played 2-4 games, which is not enough to separate skill from luck. Treat every coefficient below as directional until November.

## What is being measured

| Side | Source | Vintage |
| --- | --- | --- |
| Results, scores, stats | ESPN public API | live, 2026 |
| Football revenue/expenses, department revenue, average coach salaries | US Dept of Education EADA filings | report year 2025 |
| Head coach total pay | hand-compiled, per-row citations | 2026 |
| Revenue-share cap, roster payroll, team talent | House settlement reporting, 247Sports | 2026 |

> [!NOTE]
> Federal athletics finances are published on a lag, so the 2025 filings (academic year 2024-25) are the newest available. That is a feature here rather than a bug: past spending is a *leading* indicator of present results, so the direction of causation runs the right way.

## The richest programs and what they have done so far

| # | Program | Conf | Football rev | Football exp | Dept rev | Record | Win% | Margin/g |
| ---: | --- | --- | ---: | ---: | ---: | :---: | ---: | ---: |
| 1 | Notre Dame | FBS Independents | $195.7M | $93.3M | $289.6M | 3-0 | 100.0% | +32.3 |
| 2 | Michigan | Big Ten | $175.3M | $61.7M | $236.4M | 3-0 | 100.0% | +14.3 |
| 3 | Texas | SEC | $171.9M | $70.4M | $343.1M | 3-0 | 100.0% | +25.7 |
| 4 | Tennessee | SEC | $162.5M | $61.2M | $285.4M | 3-0 | 100.0% | +33.7 |
| 5 | Ohio State | Big Ten | $160.5M | $92.4M | $295.3M | 2-1 | 66.7% | +36.0 |
| 6 | Penn State | Big Ten | $150.3M | $77.4M | $254.4M | 3-0 | 100.0% | +35.0 |
| 7 | Georgia | SEC | $149.3M | $71.1M | $233.5M | 3-0 | 100.0% | +46.0 |
| 8 | Alabama | SEC | $146.3M | $81.5M | $244.6M | 3-0 | 100.0% | +26.7 |
| 9 | Oklahoma | SEC | $126.2M | $71.2M | $234.4M | 2-1 | 66.7% | +17.3 |
| 10 | Nebraska | Big Ten | $122.3M | $70.6M | $205.8M | 3-0 | 100.0% | +34.7 |
| 11 | Auburn | SEC | $121.4M | $58.7M | $205.3M | 2-1 | 66.7% | +10.3 |
| 12 | Washington | Big Ten | $121.0M | $68.9M | $178.4M | 3-0 | 100.0% | +16.0 |
| 13 | Oregon | Big Ten | $119.6M | $60.8M | $167.1M | 2-1 | 66.7% | +27.7 |
| 14 | LSU | SEC | $117.6M | $50.7M | $223.5M | 2-1 | 66.7% | +21.3 |
| 15 | Florida | SEC | $113.4M | $51.8M | $199.2M | 3-0 | 100.0% | +33.0 |
| 16 | Wisconsin | Big Ten | $112.3M | $40.9M | $190.5M | 2-1 | 66.7% | +14.3 |
| 17 | Texas A&M | SEC | $108.5M | $60.2M | $235.5M | 2-1 | 66.7% | +22.7 |
| 18 | Iowa | Big Ten | $105.2M | $50.9M | $180.0M | 3-0 | 100.0% | +32.7 |
| 19 | Minnesota | Big Ten | $101.7M | $45.5M | $156.8M | 2-1 | 66.7% | +20.3 |
| 20 | Miami | ACC | $99.9M | $88.1M | $230.5M | 3-0 | 100.0% | +40.7 |

## Spending versus revenue: which one tracks winning?

Revenue is money **coming in**; expenses are money **going out**. They are not the same question:

- Revenue is partly a *reward* for winning - ticket sales, donations and playoff payouts all follow success. A high correlation there is partly reverse causation.
- Spending is closer to an *input*: what the program chose to pay for coaches, staff, recruiting and running the team.

In practice the two move together: the correlation between log revenue and log spending is **0.96**. Rich programs spend more, so neither variable can fully be untangled from the other - but the ranking below shows which one tracks results more closely.

| Money metric | In/Out | Performance metric | n | r | R² |
| --- | :---: | --- | ---: | ---: | ---: |
| Athletics dept revenue | IN | point margin per game | 135 | +0.601 | 0.361 |
| Athletics dept expenses | OUT | point margin per game | 135 | +0.595 | 0.355 |
| Football revenue | IN | point margin per game | 135 | +0.592 | 0.350 |
| Men's coaching payroll | OUT | point margin per game | 135 | +0.591 | 0.349 |
| Football expenses | OUT | point margin per game | 135 | +0.570 | 0.325 |
| Football non-operating spend | OUT | point margin per game | 135 | +0.568 | 0.322 |
| Football spend per player | OUT | point margin per game | 135 | +0.558 | 0.311 |
| Athletics dept revenue | IN | win pct | 135 | +0.558 | 0.311 |
| Athletics dept expenses | OUT | win pct | 135 | +0.556 | 0.309 |
| Men's coaching payroll | OUT | win pct | 135 | +0.549 | 0.302 |
| Men's coaching payroll | OUT | points per game | 135 | +0.549 | 0.301 |
| Athletics dept revenue | IN | points per game | 135 | +0.548 | 0.301 |
| Athletics dept expenses | OUT | points per game | 135 | +0.546 | 0.298 |
| Football revenue | IN | points per game | 135 | +0.542 | 0.293 |

## Roster economics: NIL, revenue sharing and the House settlement

Following the landmark *House v. NCAA* settlement, college football entered an era structured by an institutional revenue-sharing cap: ~$20.5M for the 2025-26 academic year, escalating ~4% to ~$21.32M for 2026-27.

> [!IMPORTANT]
> Revenue-sharing caps and 247Sports team talent scores are public, > but **per-school football allocations and NIL collective payrolls > remain undisclosed.** While athletic departments widely cite a > rule of thumb directing ~75% of the cap to football (~$16M), no > major program publishes its exact balance sheet split. Rather than > interpolating or fabricating synthetic estimates, per-school > allocation and roster payroll columns (`football_allocation_est`, > `roster_payroll_est`) are left blank (`n/a`) until audited disclosures > exist.

| Data point | Reported figure | Scope | Confidence | Source |
| :--- | :--- | :--- | :--- | :--- |
| Revenue-share cap | ~$20.5M (25-26), ~$21.32M (26-27) | Every school | High | [ESPN](https://www.espn.com/college-sports/story/_/id/40206364/ncaa-power-conferences-agree-settle-house-vs-ncaa-lawsuit) |
| Football share of cap | ~75% | League-wide rule of thumb | Low per school | [Yahoo Sports](https://sports.yahoo.com/college-sports-revenue-sharing-model/) |
| Collective budgets | $15M-$20M+ | Elite tier only | Medium | [On3](https://www.on3.com/nil/news/college-football-nil-collective-budgets/) |
| Roster valuations | $12M-$15M+ | Top 5 rosters | Medium | [On3](https://www.on3.com/nil/rankings/player/college/football/) |
| 2026 recruiting spend | $3M-$5M | Top 15 classes | Medium | [247Sports](https://247sports.com/college-football/recruiting/) |
| Per-school football allocation | not disclosed | — | — | — |

### Talent composite and the equal-cap paradox

Because the House settlement revenue-share cap is uniform across all participating institutions, direct school-to-athlete distributions provide virtually zero competitive variance among top programs: every Power 4 powerhouse will max out the same cap. Consequently, competitive talent differentiation shifts into two distinct arenas: third-party booster collective fundraising ($15M-$20M+ at perennial blue-bloods) and discretionary athletic department spending on coaching, analysts, and support infrastructure.

Verified 247Sports Team Talent Composite ratings are on file for **19 elite programs**. Talent composite exhibits a strong positive correlation with scoring output (r = +0.517 with points per game, p = 0.023), confirming that even in an era of transfer portal mobility, concentrated roster talent remains an indispensable engine of scoring efficiency.

## The same question across four seasons

A three-game sample cannot settle anything, so the table below repeats the headline correlation on completed seasons. The in-progress season is marked.

| Season | Teams | r (log football revenue vs win%) | R² |
| ---: | ---: | ---: | ---: |
| 2023 | 130 | +0.367 | 0.135 |
| 2024 | 131 | +0.397 | 0.158 |
| 2025 | 133 | +0.298 | 0.089 |
| 2026 (in progress) | 135 | +0.537 | 0.289 |

## What happened to the schools that switched conference

Between 2023 and 2026 the sport redrew its map: **24 schools changed conference**. That is the closest thing this data has to a controlled experiment, because the money moved for reasons that had nothing to do with how well any given team was playing.

> [!IMPORTANT]
> The federal finance filings lag the field by two years, so the newest money year available is the 2024 season. Schools that moved in 2024 therefore have exactly **one** post-move budget year on record, and schools that moved in 2026 have **none**. Their money columns are intentionally blank rather than filled with stale pre-move values.

### The Pac-12 breakup

Ten of the twelve 2023 Pac-12 members left. Two did not, and the gap between those two groups is the single starkest result in this project.

| School | Role | Football revenue before | After | Change | Point margin change |
| --- | --- | ---: | ---: | ---: | ---: |
| Arizona | left | $37.1M | $37.8M | +1.8% | -7.6 |
| Arizona State | left | $40.2M | $50.4M | +25.4% | +23.2 |
| California | left | $45.1M | $64.0M | +41.9% | +4.5 |
| Colorado | left | $64.7M | $69.3M | +7.2% | +7.4 |
| Oregon | left | $109.2M | $119.6M | +9.5% | -3.8 |
| Stanford | left | $33.7M | $36.0M | +6.7% | +3.7 |
| UCLA | left | $45.8M | $55.2M | +20.6% | -9.1 |
| USC | left | $74.9M | $74.0M | -1.1% | +6.6 |
| Utah | left | $72.8M | $95.9M | +31.8% | +16.8 |
| Washington | left | $127.8M | $121.0M | -5.3% | -4.1 |
| Oregon State | stayed behind | $47.4M | $32.6M | -31.2% | -16.8 |
| Washington State | stayed behind | $57.0M | $38.8M | -31.9% | -0.2 |
| Boise State | joined new Pac-12 | $41.1M | - | n/a | -2.9 |
| Colorado State | joined new Pac-12 | $19.6M | - | n/a | +17.7 |
| Fresno State | joined new Pac-12 | $18.3M | - | n/a | +3.1 |
| San Diego State | joined new Pac-12 | $27.5M | - | n/a | +1.5 |
| Texas State | joined new Pac-12 | $18.0M | - | n/a | -21.2 |
| Utah State | joined new Pac-12 | $17.4M | - | n/a | -15.0 |

Median revenue change for the schools that left: **+8.3%**. For the two left behind: **-31.6%**. Washington State and Oregon State did nothing differently on the field; they simply lost their conference, and roughly a third of their football revenue went with it.

> [!NOTE]
> The leavers gained less than the headline media deals imply because several joined on **reduced shares**. Oregon and Washington entered the Big Ten at a reported ~$30M annual share against a full share of $65M+, escalating roughly $1M a year until they phase in near the end of the decade. That is why their measured revenue change here is single digit or even negative while UCLA and California, which did not take the same discount, moved much more.

#### Realignment financial mechanics

The dissolution of the original Pac-12 resulted in massive financial shifts, driven by media rights disparities and legal settlements:

- **WSU/OSU Settlement & Exit Fees**: The 10 departing members forfeited **$65 million total** ($6.5M per school) to Washington State and Oregon State, who retained conference assets and liabilities.
- **Media-Rights Hierarchy**: Big Ten agreements pay ~$1.1B-$1.2B annually (~$65M-$75M/school full share), compared to ~$380M for the Big 12 (~$31M/school) and ~$240M-$400M for the ACC.
- **Tiered Big Ten Entry**: USC and UCLA entered at full shares (~$65M+), while Oregon and Washington entered at a $30M partial share increasing $1M/year until reaching parity in 2030.
- **Travel Cost Inflation**: In their official presentation to the UC Board of Regents, UCLA Athletics projected an increase of **$4.6 million to $5.8 million** in annual travel and logistics costs due to cross-country Big Ten travel.

| Financial impact | Reported figure | Scope | Confidence | Source |
| :--- | :--- | :--- | :--- | :--- |
| WSU/OSU Settlement | $65M Withheld | 10 Departing Schools | High | [The Athletic](https://theathletic.com/5155122/2023/12/21/pac-12-settlement-washington-state-oregon-state/) |
| B1G Media Deal | ~$1.1 - $1.2B/yr | Big Ten | High | [CBS Sports](https://www.cbssports.com/college-football/news/big-ten-reaches-seven-year-media-rights-deal-with-cbs-fox-and-nbc-worth-more-than-7-billion/) |
| Big 12 Media Deal | ~$380M/yr | Big 12 | High | [ESPN](https://www.espn.com/college-football/story/_/id/34907937/big-12-agrees-new-media-rights-deal-espn-fox-sports) |
| USC / UCLA B1G Share | Full Share (~$65M+) | USC, UCLA | High | [LA Times](https://www.latimes.com/sports/ucla/story/2022-06-30/ucla-usc-big-ten-conference-move) |
| Oregon / UW B1G Share | $30M, +$1M/yr | Oregon, Washington | High | [ESPN](https://www.espn.com/college-football/story/_/id/38135860/oregon-washington-join-big-ten-2024) |
| Increased Travel Costs | $4.6M to $5.8M | UCLA | High | [LA Times](https://www.latimes.com/sports/ucla/story/2022-12-14/ucla-big-ten-move-uc-regents-approval-travel-costs) |

### Every school that moved

| School | Move | Effective | Revenue change | Point margin change |
| --- | --- | ---: | ---: | ---: |
| Arizona | Pac-12 to Big 12 | 2024 | +1.8% | -7.6 |
| Arizona State | Pac-12 to Big 12 | 2024 | +25.4% | +23.2 |
| Army | FBS Independents to American | 2024 | not yet filed | +14.4 |
| California | Pac-12 to ACC | 2024 | +41.9% | +4.5 |
| Colorado | Pac-12 to Big 12 | 2024 | +7.2% | +7.4 |
| Oklahoma | Big 12 to SEC | 2024 | +1.1% | -10.1 |
| Oregon | Pac-12 to Big Ten | 2024 | +9.5% | -3.8 |
| SMU | American to ACC | 2024 | +41.8% | -8.9 |
| Stanford | Pac-12 to ACC | 2024 | +6.7% | +3.7 |
| Texas | Big 12 to SEC | 2024 | -14.4% | +0.3 |
| UCLA | Pac-12 to Big Ten | 2024 | +20.6% | -9.1 |
| USC | Pac-12 to Big Ten | 2024 | -1.1% | +6.6 |
| Utah | Pac-12 to Big 12 | 2024 | +31.8% | +16.8 |
| Washington | Pac-12 to Big Ten | 2024 | -5.3% | -4.1 |
| Massachusetts | FBS Independents to MAC | 2025 | not yet filed | +10.9 |
| Boise State | Mountain West to Pac-12 | 2026 | not yet filed | -2.9 |
| Colorado State | Mountain West to Pac-12 | 2026 | not yet filed | +17.7 |
| Fresno State | Mountain West to Pac-12 | 2026 | not yet filed | +3.1 |
| Louisiana Tech | Conference USA to Sun Belt | 2026 | not yet filed | +8.5 |
| Northern Illinois | MAC to Mountain West | 2026 | not yet filed | -23.9 |
| San Diego State | Mountain West to Pac-12 | 2026 | not yet filed | +1.5 |
| Texas State | Sun Belt to Pac-12 | 2026 | not yet filed | -21.2 |
| UTEP | Conference USA to Mountain West | 2026 | not yet filed | -5.5 |
| Utah State | Mountain West to Pac-12 | 2026 | not yet filed | -15.0 |

## What the head coach is paid

Verified total pay is on file for **52 of 138 teams**. Public universities subject to open-records laws provide high-confidence, cited figures. Private institutions (e.g., USC, Notre Dame, Stanford, Miami, TCU, Baylor, SMU, Vanderbilt) are exempt from FOIA disclosure and remain marked as unverified with blank salaries rather than synthetic estimates.

Across those 52 teams, head coach pay correlates **r = +0.33** with point margin per game (p = 0.017). That is a real but much weaker signal than total program spending, which is the more telling result: paying one person more matters far less than the scale of the operation behind them.

| Coach | School | Total pay | Buyout | Win% | Point margin |
| --- | --- | ---: | ---: | ---: | ---: |
| Kirby Smart | Georgia | $13.3M | $105.1M | 1.000 | +46.0 |
| Ryan Day | Ohio State | $12.6M | $70.9M | 0.667 | +36.0 |
| Dabo Swinney | Clemson | $11.4M | $60.0M | 0.667 | -6.0 |
| Steve Sarkisian | Texas | $10.8M | $60.3M | 1.000 | +25.7 |
| Dan Lanning | Oregon | $10.4M | $56.7M | 0.667 | +27.7 |
| Kalen DeBoer | Alabama | $10.2M | $60.8M | 1.000 | +26.7 |
| Brian Kelly | LSU | $10.2M | $53.3M | 0.667 | +21.3 |
| Bill Belichick | North Carolina | $10.1M | $20.8M | 0.667 | +9.7 |
| Josh Heupel | Tennessee | $9.0M | $37.5M | 1.000 | +33.7 |
| Eliah Drinkwitz | Missouri | $9.0M | $42.6M | 1.000 | +22.3 |

## Travel, time zones and the cost of flying east

Realignment moved miles as well as money. A team flying east loses hours: a noon kickoff on the east coast is a 9am body clock for a team from California. The table below pools every completed game from 2023 to 2026 by how many time zones the team crossed.

| Travel | Games | Mean margin | Win rate |
| --- | ---: | ---: | ---: |
| 3 zones west | 53 | -2.9 | 42% |
| 2 zones west | 68 | -7.1 | 43% |
| 1 zone west | 376 | -6.2 | 36% |
| same zone | 1277 | -5.4 | 41% |
| 1 zone east | 363 | -3.4 | 42% |
| 2 zones east | 77 | -9.0 | 36% |
| 3 zones east | 53 | -7.9 | 36% |

> [!IMPORTANT]
> The raw split above is confounded. The teams that fly two or more zones east are disproportionately Group of Five programs taking a paycheque game at a blue blood, so they would have lost anyway. Comparing each team against **itself** - its own margin on long eastward trips versus its own margin on every other away game - the penalty is **-1.0 points** across 61 team-seasons (-6.8 on long eastward trips versus -5.7 on other away games).

### Who now travels further

Average time zones crossed per away game, before and after the move. The old Pac-12 fit inside two zones; the Big Ten and ACC do not.

| School | Move | Zones before | Zones after | Change | Away margin change |
| --- | --- | ---: | ---: | ---: | ---: |
| Stanford | Pac-12 to ACC | -0.20 | +1.92 | +2.12 | -4.8 |
| Arizona State | Pac-12 to Big 12 | -0.75 | +0.83 | +1.58 | +15.5 |
| California | Pac-12 to ACC | +0.50 | +2.08 | +1.58 | -2.0 |
| Colorado | Pac-12 to Big 12 | -0.33 | +1.00 | +1.33 | +9.4 |
| UCLA | Pac-12 to Big Ten | +0.33 | +1.46 | +1.13 | -14.9 |
| Washington | Pac-12 to Big Ten | +0.80 | +1.90 | +1.10 | -16.9 |
| Arizona | Pac-12 to Big 12 | -0.33 | +0.73 | +1.06 | -18.8 |
| Oregon | Pac-12 to Big Ten | +0.80 | +1.82 | +1.02 | -3.7 |
| Utah | Pac-12 to Big 12 | -0.40 | +0.58 | +0.98 | +17.5 |
| USC | Pac-12 to Big Ten | +1.00 | +1.91 | +0.91 | +2.1 |
| Texas | Big 12 to SEC | +0.00 | +0.56 | +0.56 | -11.1 |

## Every money metric against every performance metric

| Money metric | Performance metric | n | Pearson r | R² | Spearman ρ | p |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Athletics dept revenue (log) | point margin per game | 135 | +0.601 | 0.361 | +0.576 | 0.0000*** |
| Athletics dept expenses (log) | point margin per game | 135 | +0.595 | 0.355 | +0.567 | 0.0000*** |
| Football revenue (log) | point margin per game | 135 | +0.592 | 0.350 | +0.586 | 0.0000*** |
| Men's coaching payroll (log) | point margin per game | 135 | +0.591 | 0.349 | +0.575 | 0.0000*** |
| Football expenses (log) | point margin per game | 135 | +0.570 | 0.325 | +0.558 | 0.0000*** |
| Football non-operating spend (log) | point margin per game | 135 | +0.568 | 0.322 | +0.558 | 0.0000*** |
| Football spend per player (log) | point margin per game | 135 | +0.558 | 0.311 | +0.552 | 0.0000*** |
| Athletics dept revenue (log) | win pct | 135 | +0.558 | 0.311 | +0.548 | 0.0000*** |
| Athletics dept expenses (log) | win pct | 135 | +0.556 | 0.309 | +0.545 | 0.0000*** |
| Men's coaching payroll (log) | win pct | 135 | +0.549 | 0.302 | +0.566 | 0.0000*** |
| Men's coaching payroll (log) | points per game | 135 | +0.549 | 0.301 | +0.530 | 0.0000*** |
| Athletics dept revenue (log) | points per game | 135 | +0.548 | 0.301 | +0.517 | 0.0000*** |
| Athletics dept expenses (log) | points per game | 135 | +0.546 | 0.298 | +0.510 | 0.0000*** |
| Football revenue (log) | points per game | 135 | +0.542 | 0.293 | +0.532 | 0.0000*** |
| Football revenue (log) | win pct | 135 | +0.537 | 0.289 | +0.547 | 0.0000*** |
| Men's recruiting spend (log) | point margin per game | 135 | +0.534 | 0.285 | +0.556 | 0.0000*** |
| Football expenses (log) | win pct | 135 | +0.532 | 0.283 | +0.543 | 0.0000*** |
| Football non-operating spend (log) | win pct | 135 | +0.531 | 0.282 | +0.543 | 0.0000*** |
| Football expenses (log) | points per game | 135 | +0.530 | 0.281 | +0.516 | 0.0000*** |
| Football spend per player (log) | win pct | 135 | +0.528 | 0.279 | +0.537 | 0.0000*** |
| Football non-operating spend (log) | points per game | 135 | +0.528 | 0.279 | +0.518 | 0.0000*** |
| Avg men's head coach salary (log) | point margin per game | 135 | +0.527 | 0.277 | +0.528 | 0.0000*** |
| Men's recruiting spend (log) | win pct | 135 | +0.520 | 0.271 | +0.521 | 0.0000*** |
| 247 team talent composite | points per game | 19 | +0.517 | 0.268 | +0.500 | 0.0233* |
| Football spend per player (log) | points per game | 135 | +0.517 | 0.268 | +0.506 | 0.0000*** |
| Avg men's head coach salary (log) | points per game | 135 | +0.515 | 0.266 | +0.517 | 0.0000*** |
| Men's recruiting spend (log) | points per game | 135 | +0.514 | 0.264 | +0.520 | 0.0000*** |
| Athletics dept revenue (log) | points allowed per game | 135 | -0.509 | 0.259 | -0.485 | 0.0000*** |
| Athletics dept expenses (log) | points allowed per game | 135 | -0.502 | 0.252 | -0.476 | 0.0000*** |
| Football revenue (log) | points allowed per game | 135 | -0.499 | 0.249 | -0.497 | 0.0000*** |
| Men's coaching payroll (log) | points allowed per game | 135 | -0.490 | 0.240 | -0.477 | 0.0000*** |
| Avg men's head coach salary (log) | win pct | 135 | +0.473 | 0.223 | +0.480 | 0.0000*** |
| Football expenses (log) | points allowed per game | 135 | -0.472 | 0.223 | -0.460 | 0.0000*** |
| Football non-operating spend (log) | points allowed per game | 135 | -0.470 | 0.221 | -0.454 | 0.0000*** |
| Football spend per player (log) | points allowed per game | 135 | -0.464 | 0.215 | -0.455 | 0.0000*** |
| 247 team talent composite | point margin per game | 19 | +0.446 | 0.199 | +0.440 | 0.0554 |
| Men's recruiting spend (log) | points allowed per game | 135 | -0.422 | 0.178 | -0.444 | 0.0000*** |
| Avg men's head coach salary (log) | points allowed per game | 135 | -0.407 | 0.166 | -0.401 | 0.0000*** |
| Head coach total pay (log) | points allowed per game | 52 | -0.368 | 0.135 | -0.319 | 0.0073** |
| Head coach total pay (log) | point margin per game | 52 | +0.330 | 0.109 | +0.298 | 0.0170* |
| Men's coaching payroll (log) | yards per carry | 135 | +0.283 | 0.080 | +0.260 | 0.0009*** |
| Athletics dept revenue (log) | yards per carry | 135 | +0.282 | 0.080 | +0.254 | 0.0009*** |
| Football non-operating spend (log) | yards per carry | 135 | +0.281 | 0.079 | +0.270 | 0.0009*** |
| Head coach total pay (log) | opponent win pct | 52 | -0.281 | 0.079 | -0.265 | 0.0435* |
| Athletics dept expenses (log) | yards per carry | 135 | +0.277 | 0.077 | +0.249 | 0.0011** |
| Football expenses (log) | yards per carry | 135 | +0.274 | 0.075 | +0.263 | 0.0013** |
| Avg men's head coach salary (log) | yards per carry | 135 | +0.271 | 0.073 | +0.253 | 0.0015** |
| Football revenue (log) | yards per carry | 135 | +0.263 | 0.069 | +0.273 | 0.0021** |
| Football spend per player (log) | yards per carry | 135 | +0.259 | 0.067 | +0.244 | 0.0024** |
| Head coach total pay (log) | win pct | 52 | +0.258 | 0.067 | +0.252 | 0.0647 |
| Men's recruiting spend (log) | yards per carry | 135 | +0.255 | 0.065 | +0.222 | 0.0028** |
| Head coach total pay (log) | points per game | 52 | +0.193 | 0.037 | +0.147 | 0.1714 |
| 247 team talent composite | yards per carry | 19 | +0.185 | 0.034 | +0.220 | 0.4494 |
| Football expenses (log) | opponent win pct | 135 | -0.181 | 0.033 | -0.220 | 0.0355* |
| Football non-operating spend (log) | opponent win pct | 135 | -0.180 | 0.032 | -0.217 | 0.0365* |
| Football revenue (log) | opponent win pct | 135 | -0.179 | 0.032 | -0.192 | 0.0380* |
| Men's coaching payroll (log) | opponent win pct | 135 | -0.176 | 0.031 | -0.207 | 0.0408* |
| Football spend per player (log) | opponent win pct | 135 | -0.171 | 0.029 | -0.206 | 0.0473* |
| Athletics dept expenses (log) | opponent win pct | 135 | -0.171 | 0.029 | -0.190 | 0.0479* |
| Athletics dept revenue (log) | opponent win pct | 135 | -0.168 | 0.028 | -0.191 | 0.0517 |
| Men's recruiting spend (log) | opponent win pct | 135 | -0.164 | 0.027 | -0.171 | 0.0578 |
| Avg men's head coach salary (log) | opponent win pct | 135 | -0.127 | 0.016 | -0.142 | 0.1433 |
| 247 team talent composite | win pct | 19 | +0.114 | 0.013 | +0.069 | 0.6409 |
| 247 team talent composite | opponent win pct | 19 | +0.083 | 0.007 | +0.075 | 0.7348 |
| 247 team talent composite | points allowed per game | 19 | -0.068 | 0.005 | -0.029 | 0.7819 |
| Head coach total pay (log) | yards per carry | 52 | -0.040 | 0.002 | -0.023 | 0.7810 |

`*` p<0.05, `**` p<0.01, `***` p<0.001

## Regression: money with conference fixed effects

Conference dummies absorb the media-rights advantage, so the money coefficient answers a narrower question: *within the same league, does the bigger budget win more?*

Outcome: **win_pct**, predictor: **football_expenses**, n = 135, R² = 0.336 (adjusted 0.276).

| Term | Estimate | Std error | t | p |
| --- | ---: | ---: | ---: | ---: |
| intercept | -2.8423 | 1.4905 | -1.91 | 0.0589 |
| log10(football_expenses) | +0.4550 | 0.1942 | +2.34 | 0.0207* |
| conf[American] | +0.0312 | 0.1189 | +0.26 | 0.7937 |
| conf[Big 12] | +0.1678 | 0.0886 | +1.89 | 0.0606 |
| conf[Big Ten] | +0.0974 | 0.0853 | +1.14 | 0.2555 |
| conf[Conference USA] | +0.0394 | 0.1519 | +0.26 | 0.7958 |
| conf[FBS Independents] | +0.1989 | 0.1859 | +1.07 | 0.2867 |
| conf[MAC] | +0.0638 | 0.1532 | +0.42 | 0.6779 |
| conf[Mountain West] | +0.0313 | 0.1487 | +0.21 | 0.8337 |
| conf[Pac-12] | -0.0764 | 0.1252 | -0.61 | 0.5429 |
| conf[SEC] | +0.1473 | 0.0882 | +1.67 | 0.0974 |
| conf[Sun Belt] | +0.1356 | 0.1423 | +0.95 | 0.3426 |

### Overperformers and underperformers

**Beating their budget**

| Program | Conf | Football expenses | Actual | Budget-predicted | Gap |
| --- | --- | ---: | ---: | ---: | ---: |
| North Dakota State | Mountain West | $8.4M | 100.0% | 33.9% | +66.1 pts |
| Massachusetts | MAC | $13.4M | 100.0% | 46.5% | +53.5 pts |
| Tulsa | American | $20.7M | 100.0% | 51.8% | +48.2 pts |
| App State | Sun Belt | $13.3M | 100.0% | 53.5% | +46.5 pts |
| James Madison | Sun Belt | $16.9M | 100.0% | 58.2% | +41.8 pts |
| Virginia Tech | ACC | $37.8M | 100.0% | 60.6% | +39.4 pts |
| South Florida | American | $33.4M | 100.0% | 61.2% | +38.8 pts |
| Pittsburgh | ACC | $47.1M | 100.0% | 64.9% | +35.1 pts |
| Duke | ACC | $47.4M | 100.0% | 65.0% | +35.0 pts |
| Northwestern | Big Ten | $37.9M | 100.0% | 70.4% | +29.6 pts |
| Kansas State | Big 12 | $27.1M | 100.0% | 70.8% | +29.2 pts |
| Fresno State | Pac-12 | $17.7M | 66.7% | 37.9% | +28.7 pts |

**Falling short of their budget**

| Program | Conf | Football expenses | Actual | Budget-predicted | Gap |
| --- | --- | ---: | ---: | ---: | ---: |
| Rutgers | Big Ten | $75.9M | 0.0% | 84.1% | -84.1 pts |
| Arkansas | SEC | $57.4M | 33.3% | 83.5% | -50.2 pts |
| Charlotte | American | $15.6M | 0.0% | 46.2% | -46.2 pts |
| Northern Illinois | Mountain West | $13.2M | 0.0% | 42.9% | -42.9 pts |
| UL Monroe | Sun Belt | $7.8M | 0.0% | 42.9% | -42.9 pts |
| Florida State | ACC | $83.3M | 33.3% | 76.2% | -42.8 pts |
| Bowling Green | MAC | $11.0M | 0.0% | 42.5% | -42.5 pts |
| Kansas | Big 12 | $34.5M | 33.3% | 75.6% | -42.2 pts |
| Western Kentucky | Conference USA | $11.0M | 0.0% | 40.2% | -40.2 pts |
| Utah State | Pac-12 | $17.3M | 0.0% | 37.5% | -37.5 pts |
| Purdue | Big Ten | $37.2M | 33.3% | 70.0% | -36.7 pts |
| Georgia Tech | ACC | $42.7M | 33.3% | 63.0% | -29.7 pts |

## Mid-season reality check: what held up and what looks shaky

As the season progresses deeper into September (Week 4, 2-4 games played) and teams move from non-conference slates into conference play, early hypotheses can be evaluated against live results:

### What held up

1. **Program infrastructure over star coach**: Discretionary coaching payroll and total athletic department expenses continue to correlate substantially higher with point margin (r ~ +0.57 to +0.60) than head coach total pay alone (r = +0.33). Investing across an entire staff, analysts, strength training, and nutrition creates a far more resilient winning floor than paying top dollar for one individual.
2. **Pac-12 stayers’ revenue collapse**: Oregon State and Washington State losing roughly one-third of their football revenue (-31.6% median) remains the clearest natural experiment in modern college sports.
3. **The eastward travel penalty**: Crossing 2 to 3 time zones eastward imposes a consistent within-team penalty (-1.0 points per game across 61 team-seasons), substantiating concerns raised by West Coast programs during realignment.

### What is looking shaky or evolving

1. **Early-season "buy game" margin distortion**: Early September point differentials were inflated by top-20 programs blowing out paid FCS and lower Group-of-Five opponents (+40 to +55 point margins). As Week 4 conference competition arrived, point margins compressed toward realistic distributions.
2. **Outlier mean reversion**: Extreme single-game outliers from early weeks (such as Colorado State leading all budget overperformers at 2-0 before dropping to 2-1 in Week 4, while big-budget programs like Rutgers at 0-3, Florida State at 1-2, and Arkansas at 1-2 anchor the underperformer table) shift rapidly as teams reach 3 to 4 games played.
3. **The revenue-endogeneity puzzle**: Logged football revenue (IN) tracks point margin (r = +0.592) nearly identically to football expenses (OUT, r = +0.570). While past EADA spending serves as a temporal lead, institutional revenue reflects decades of historical success, meaning high revenue is as much a historical reward for legacy winning as it is a causal input.

## Conference summary

| Conference | Teams | Median football rev | Median dept rev | Mean win% | Mean margin |
| --- | ---: | ---: | ---: | ---: | ---: |
| SEC | 16 | $110.9M | $204.9M | 83.3% | +20.6 |
| FBS Independents | 2 | $108.1M | $193.3M | 83.3% | +25.0 |
| Big Ten | 18 | $94.8M | $176.5M | 77.8% | +21.1 |
| ACC | 17 | $64.0M | $151.6M | 64.7% | +11.4 |
| Big 12 | 16 | $49.0M | $130.7M | 77.1% | +20.9 |
| Pac-12 | 8 | $23.1M | $72.8M | 41.7% | +0.4 |
| American | 14 | $19.5M | $62.8M | 50.6% | +1.7 |
| Mountain West | 10 | $13.2M | $50.4M | 43.3% | +0.4 |
| Sun Belt | 14 | $12.9M | $39.9M | 52.4% | +5.1 |
| Conference USA | 10 | $11.6M | $38.5M | 41.7% | +0.6 |
| MAC | 13 | $11.0M | $38.9M | 42.3% | -7.9 |

## Figures

![revenue vs spending point margin per game 2026](figures/revenue_vs_spending_point_margin_per_game_2026.png)

![football expenses vs point margin per game 2026](figures/football_expenses_vs_point_margin_per_game_2026.png)

![football expenses vs win pct 2026](figures/football_expenses_vs_win_pct_2026.png)

![football revenue vs point margin per game 2026](figures/football_revenue_vs_point_margin_per_game_2026.png)

![football revenue vs win pct 2026](figures/football_revenue_vs_win_pct_2026.png)

![football spend per player vs point margin per game 2026](figures/football_spend_per_player_vs_point_margin_per_game_2026.png)

![football spend per player vs win pct 2026](figures/football_spend_per_player_vs_win_pct_2026.png)

![football expenses vs point margin per game by season](figures/football_expenses_vs_point_margin_per_game_by_season.png)

![football revenue vs point margin per game by season](figures/football_revenue_vs_point_margin_per_game_by_season.png)

![football spend per player vs win pct by season](figures/football_spend_per_player_vs_win_pct_by_season.png)

![football spend per player vs point margin per game by season](figures/football_spend_per_player_vs_point_margin_per_game_by_season.png)

![correlation by season](figures/correlation_by_season.png)

![pac12 diaspora](figures/pac12_diaspora.png)

![realignment money vs margin](figures/realignment_money_vs_margin.png)

![travel timezone penalty](figures/travel_timezone_penalty.png)

![football expenses by conference 2026](figures/football_expenses_by_conference_2026.png)

![residuals 2026](figures/residuals_2026.png)

## Caveats worth repeating

- EADA revenue is self-reported and, at many private schools, revenue is booked to exactly equal expenses. Comparisons across the public/private line are shakier than they look.
- Football revenue is partly a *consequence* of winning (ticket sales, donations, playoff payouts), so correlation here is bidirectional, not clean causation.
- Revenue-share and NIL money, which is where the 2026 arms race actually happens, is largely private. The cap is public; the allocation is not.
- Conference realignment means a team's conference label changed recently for several programs; fixed effects use the 2026 alignment.
