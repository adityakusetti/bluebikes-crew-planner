## 11. Analysis, key decisions, and results

**Headline.** The base plan staffs Greater Boston for a total 2026 crew cost of **$944,700**. Seasonal crews peak at the system-wide cap of **8** in summer. Against the forecast, the plan has no unmet rebalancing need, but the backtest on real January–September 2026 trips shows it would have fallen short by about **23,300 bikes**, roughly **$133,000** in lost revenue at $5.70 per unmet trip.

**How we measured need.** We aggregated every trip to arrivals and departures per station per hour (96.9% of station-hours matched the station list by name), then simulated each station starting the day half full and counted bikes that would push it below empty or above its dock count. Cambridge and Boston carry almost all the rebalancing load; Brookline, Somerville, and the other cities need only one crew or less most of the year.

**Key staffing decisions.**
- *Full-time for the base, seasonal for the peak.* A full-time crew costs about $6,000 per month and a seasonal crew $7,800, so full-time is cheaper for any crew needed about 9 or more months a year. We set each city's full-time level to the crews it needs in at least 9 months, and filled the rest with seasonal contracts (signed a month ahead, at least 3 months, at most 8 system-wide).
- *Boston and Cambridge drive the plan.* Boston's need rises from about 1,800 bikes in January to about 17,400 in September; Cambridge peaks at about 16,100 in September. Both need 6 crews at peak.
- *Releasing Boston drivers was the costliest choice.* Because Boston's forecast winter need is low, the rule cut Boston from 6 to 2 full-time crews in January, which costs $54,000 in severance and then relies on seasonal crews from April to November.

**What the backtest taught us.** Real 2026 need was higher than forecast in Boston from April to September and in Cambridge from June to August, with the largest gap in Boston in August (about 5,300 bikes). The cause is our growth factor: measured 2024→2025 growth in rebalancing need was below 1 (for example 0.85 for Boston and 0.81 for Cambridge), even though trip volume grew. Scaling 2025 down by those factors under-forecast 2026. In practice we would (1) use a growth factor of at least 1.0, or base it on trip growth, and (2) keep more Boston drivers full-time instead of releasing four, which also avoids the severance.

**Events.** The LLM extracted 10 event-days (Boston Marathon, Head of the Charles, college move-in). Measured event days needed *less* rebalancing than normal days in the same month (0.59x), likely because events such as the Marathon close nearby stations and change riding patterns. The sample is small, so we treat this as a finding rather than a rule; a production version would floor the uplift at 1.0 and add more event history.

**Sensitivity.**
| Scenario | Crew cost | Lost revenue | Peak seasonal crews |
|---|---|---|---|
| Base | $944,700 | $0 | 8 |
| Ridership −20% | $746,100 | $0 | 5 |
| Ridership +20% | $1,203,600 | $80,074 | 8 |
| E-bike trips +30% | $989,400 | $0 | 8 |

At +20% ridership, the 8-crew seasonal cap binds and unmet need appears, which is the strongest argument for hiring more full-time drivers before peak season. E-bike growth adds about 5% to cost.

**Operations assistant.** The tool-calling assistant answers what-if questions from the plan itself. Asked about adding a Cambridge crew in September, it correctly reported the $23,400 cost (3-month minimum) and warned that it would exceed the 8-crew seasonal cap. Because it reads the forecast plan, it reported Boston as fully covered in July, while the backtest shows a real shortfall; connecting the assistant to backtest results is a clear next step.

**Assumptions and limitations.** Each station starts the day half full; within-hour order is ignored, so need is a lower bound. Each unmoved bike is treated as one lost trip. About 3% of station-hours did not match the station list by name. Crew costs and rules are the planning assumptions given in the brief.

**Other recommendations.** Add docks at stations that are consistently full (several Cambridge and Kendall stations), and offer rider rewards for returning bikes to stations that run empty, since both reduce the need for crews at peak.
