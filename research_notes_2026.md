# 2026 Financial Research Notes

## 1. Coach Pay and NIL Coverage Update

We have expanded our coverage of the 2026 financial landscape, specifically focusing on verified head coach compensation and Revenue-Share / NIL valuations.

### Coach Pay
- The `coach_pay_2026.csv` dataset has been significantly expanded beyond the original 10 verified rows.
- Priority was given to the Big Ten, SEC, Big 12, ACC, and the specific Pac-12 realignment/G5 schools (e.g., Washington State, Oregon State, Boise State, Colorado State).
- Public universities subject to open-records laws have high-confidence, cited figures. Private institutions (e.g., USC, Notre Dame, Stanford, Miami) remain marked as `unverified` with blank salaries to strictly adhere to data integrity rules against fabricating numbers. A `buyout` column was also populated where publicly available.

### NIL & Revenue Share

> [!IMPORTANT]
> These figures are **league-wide ranges reported in the press, not
> per-school disclosures.** An earlier pass wrote a flat ~$16.5M
> football allocation onto every school in
> `nil_revshare_2026.csv`. That was a rule of thumb (75% of the cap)
> applied uniformly, not observed data: the column had a single
> distinct value across all 19 schools and was cited to a 247Sports
> talent-ranking URL that does not support the claim. Those columns
> have been **cleared back to blank**. Only the settlement cap and the
> 247Sports talent composite remain populated, because only those are
> genuinely public per school.

- Following the *House v. NCAA* settlement, the revenue-sharing cap is
  ~$20.5M for 2025-26, escalating ~4% to ~$21.32M for 2026-27.
- Athletic departments have *generally* said they intend to direct
  roughly **75% of the cap to football**, but almost none publish their
  actual split, and the few public statements are not directly
  comparable.
- Elite collectives reportedly operate in the **$15M-$20M** range, and
  an elite 2026 recruiting class is estimated at **$3M-$5M** in NIL
  commitments. Both are journalistic estimates for the top tier, not a
  per-school series.

| Data point | Reported figure | Scope | Confidence | Source |
| :--- | :--- | :--- | :--- | :--- |
| Revenue-share cap | ~$20.5M (25-26), ~$21.32M (26-27) | Every school | High | [ESPN](https://www.espn.com/college-sports/story/_/id/40206364/ncaa-power-conferences-agree-settle-house-vs-ncaa-lawsuit) |
| Football share of cap | ~75% | League-wide rule of thumb | Low per school | [Yahoo Sports](https://sports.yahoo.com/college-sports-revenue-sharing-model/) |
| Collective budgets | $15M-$20M+ | Elite tier only | Medium | [On3](https://www.on3.com/nil/news/college-football-nil-collective-budgets/) |
| Roster valuations | $12M-$15M+ | Top 5 rosters | Medium | [On3](https://www.on3.com/nil/rankings/player/college/football/) |
| 2026 recruiting spend | $3M-$5M | Top 15 classes | Medium | [247Sports](https://247sports.com/college-football/recruiting/) |
| **Per-school football allocation** | **not disclosed** | — | — | — |

---

## 2. Pac-12 Breakup Financial Impact

The dissolution of the original Pac-12 resulted in massive financial shifts, particularly regarding media rights, settlement fees, and increased travel costs.

### WSU/OSU Settlement & Exit Fees
Because the Pac-12's Grant of Rights expired in 2024, traditional "exit fees" did not apply. Instead, a legal settlement was reached.
- The 10 departing schools agreed to forfeit **$65 million total** (effectively **$6.5 million per school**) to Washington State and Oregon State, who retained control of the conference's assets and liabilities.

### Conference Media-Rights Deals
The vast gap in media revenue drove the realignment. For the new cycle (2024+):
- **Big Ten (B1G):** ~$1.1 Billion to $1.2 Billion annually.
- **Big 12:** ~$380 Million annually.
- **ACC:** ~$240 Million to $400 Million annually.
- **New Pac-12:** Currently negotiating new media deals; industry estimates project significantly lower valuations compared to the Power 4.

### Reduced-Share Arrangements (Big Ten)
Not all incoming Big Ten schools receive equal payouts immediately, which explains why revenue jumps for some programs were lower than expected.
- **USC & UCLA:** Entered the Big Ten receiving **full media revenue shares** (estimated at $65M–$75M+ per year).
- **Oregon & Washington:** Entered at a **reduced partial share**. They receive **$30 million** for the 2024–2025 academic year, with the payout increasing by **$1 million annually** ($31M in 2025, $32M in 2026). They do not phase up to a full share until the next media rights cycle begins in **2030**.

### Increased Travel Costs
Transitioning to the B1G and ACC requires extensive, costly coast-to-coast travel.
- **UCLA Travel Impact:** In their official presentation to the UC Board of Regents, UCLA Athletics projected an increase of **$4.6 million to $5.8 million** in annual travel and logistics costs due to joining the Big Ten.

| Financial Impact | Exact Figure | School/Conference | Confidence | Source URL |
| :--- | :--- | :--- | :--- | :--- |
| WSU/OSU Settlement | $65M Withheld | 10 Departing Schools | High | [The Athletic](https://theathletic.com/5155122/2023/12/21/pac-12-settlement-washington-state-oregon-state/) |
| B1G Media Deal | ~$1.1 - $1.2B/yr | Big Ten | High | [CBS Sports](https://www.cbssports.com/college-football/news/big-ten-reaches-seven-year-media-rights-deal-with-cbs-fox-and-nbc-worth-more-than-7-billion/) |
| Big 12 Media Deal | ~$380M/yr | Big 12 | High | [ESPN](https://www.espn.com/college-football/story/_/id/34907937/big-12-agrees-new-media-rights-deal-espn-fox-sports) |
| USC / UCLA B1G Share | Full Share (~$65M+) | USC, UCLA | High | [LA Times](https://www.latimes.com/sports/ucla/story/2022-06-30/ucla-usc-big-ten-conference-move) |
| Oregon / UW B1G Share | $30M, +$1M/yr | Oregon, Washington | High | [ESPN](https://www.espn.com/college-football/story/_/id/38135860/oregon-washington-join-big-ten-2024) |
| Increased Travel Costs | $4.6M to $5.8M | UCLA | High | [LA Times](https://www.latimes.com/sports/ucla/story/2022-12-14/ucla-big-ten-move-uc-regents-approval-travel-costs) |
