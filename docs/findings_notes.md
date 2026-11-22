# Findings notes (working draft for the report & slides)

All numbers come from `outputs/tables/` after `python run_pipeline.py`. If you re-run with new data, update this file from those tables, don't type numbers from memory.

## The question
To what extent can online attention, engagement and sentiment around *Avengers: Endgame* (2019) and *Avengers: Doomsday* (17-Dec-2026) help anticipate Indian theatrical demand - and how should release timing, genre, show availability and inflation be handled when deciding screens and promotion?

## Draft 3-sentence answer for the Head of Distribution
1. Online attention is a good *thermometer* but a weak *forecast*: for Endgame, daily Wikipedia attention and India collections moved almost in lockstep (r = 0.97 over 28 days, n = 28), but mostly because both are driven by the release itself - the signal arrives the same day as the money.
2. The signals that actually lead are advance bookings and the first-Monday hold: Doomsday has already sold ₹20.77 Cr gross for Day 1 (22 % of Endgame's Day-1 gross in today's rupees) 26 days out, growing ~₹1.6 Cr/day, and southern states are 60-84 % full on fewer shows.
3. Recommendation for release weekend: add standard-format shows first in Kerala, Tamil Nadu and Telangana, then decide week-2 screens on the first Monday (keep/add if it holds ≥ 58 % of opening day like Endgame; cut ~25-30 % of week-2 shows if it falls toward 31 % like the 2026 re-release), and keep promo money for value messaging, because "not worth the price" is the one complaint that drags ratings down (5.9/10 vs 8.9).

## Evidence → chart
| # | Chart | Finding |
|---|---|---|
| c1 | `c1_trailer_attention_14d.png` | Doomsday's trailer peak was a bit higher (173.7K vs 165.0K launch-day views; 1.03 M vs 0.85 M over 14 days), but faded faster: day 3 = 33 % of launch day vs 50 % for Endgame. Second bump on day 6 (26-Jul-2026). |
| c2 | `c2_buzz_vs_boxoffice_endgame.png` (2 sources) | r = 0.97 same day, 0.94 with views lagged 1 day, 0.89 after week 1. Both series fall together - correlation, not cause. |
| c3 | `c3_inflation_effect.png` | CPI factor Apr-2019 → Oct-2026 = 1.48 (MoSPI, linked series). Opening day ₹53.6 Cr ≈ ₹79 Cr today; lifetime ₹370-373 Cr ≈ ₹548-552 Cr today. |
| c4 | `c4_ticket_price_vs_cpi.png` | CPI would take a ₹215 ticket (PVR 2019 average) to ₹318; Doomsday's Day-1 advance ATP is ₹699. Cinema prices ≠ CPI (indicative: different scopes). |
| c5 | `c5_daily_decay_original_vs_rerelease.png` | Monday test: 58 % (Endgame) vs 31 % (Encore). 2nd weekend: 33 % vs 13 % of the first. |
| c6 | `c6_review_themes.png` | Encore-period reviews: extra scenes most discussed (27 %); price/value complaints in 10 % of reviews with avg 5.9/10. |
| c7 | `c7_doomsday_advance_by_state.png` | Kerala 72 %, Telangana 62 %, Tamil Nadu 84 % occupancy; Karnataka/Maharashtra/West Bengal earn most per show. |

## Opening-day scenarios (India net) - `outputs/tables/doomsday_opening_scenarios.csv`
Low ₹53.6 Cr (same nominal rupees as Endgame) · Mid ₹79.3 Cr (same real money) · High ₹94.0 Cr (Endgame's advance multiple - upper reference only). Use as a range to plan show counts, not as a prediction.

## Limitations to state honestly
- One historical film + one re-release + one upcoming film = not enough for a statistical model. Thresholds are benchmarks, not fitted parameters.
- English Wikipedia = global attention, not Indian audiences specifically. YouTube counters are cumulative snapshots, not daily history.
- Review sample (145) is small and all RT reviews are from the 2026 re-release period; RT / IMDb reviewers are not representative of Indian moviegoers. IMDb hides most reviews behind login; Reddit could not be reached.
- Trade figures are estimates and disagree (Endgame lifetime 370.05 / 373.05 / 373.22; BH's own week totals don't match its days).
- CPI is a general price index; ticket prices rose much faster. Nov-2026 CPI not out yet.
- Doomsday's week 2 contains Christmas/New-Year; Endgame's didn't - hold ratios are not like-for-like.
- Paid promotion / bots: no duplicate long reviews found in our sample, but 145 reviews cannot rule it out.
