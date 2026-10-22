# Lather Log - {{month_year}}

**Total Shaves:** {{total_shaves}}
**Unique Shavers:** {{unique_shavers}}

Welcome to your SOTD Lather Log for {{month_year}}

* {{total_shaves}} shave reports from {{unique_shavers}} distinct shavers during the month of {{month_year}} were analyzed to produce this report. Collectively, these shavers used {{unique_soaps}} distinct soaps from {{unique_brands}} distinct brands. {{total_samples}} of those shaves used samples or smushes of {{unique_sample_soaps}} unique soaps, and {{total_mashup_shaves}} used mashups.

## Observations

* [Observations will be generated based on data analysis]

## Notes & Caveats

* Tables show all entries with 5 or more shaves to provide comprehensive coverage without artificial row limits.

* The unique user column shows the number of different users who used a given brand/soap/etc in the month.

* The Brand Diversity table details the number of distinct soaps used during the month from that particular brand, showing all brands with 5+ unique soaps.

* The change Δ vs columns show how an item has moved up or down the rankings since that month. = means no change in position, up or down arrows indicate how many positions up or down the rankings an item has moved compared to that month. n/a means the item was not present in that month.

* When available, soap names in the Soaps table link to their entry on Wet Shaving Database, where you can see scent notes, descriptions, and ingredient lists.

* An **exclusive soap** is a matched brand+scent used by only one shaver in the month. That shaver earns one point for that soap, no matter how many times they logged it.

## Soap Brands

{{tables.soap-makers|shaves:5|deltas:true}}

## Soaps

{{tables.soaps|shaves:5|columns:rank, name=soap, shaves, unique_users|deltas:true|wsdb:true}}

## Brand Diversity

{{tables.brand-diversity|unique_soaps:5|deltas:true}}

## Top Mashup Users

{{tables.soap-mashup-users|shaves:5|columns:rank, user, shaves, unique_users|deltas:true}}

## Soap Diversity by User

{{tables.user-soap-brand-scent-diversity|ranks:20|columns:rank, user, unique_combinations=unique_soaps, shaves, avg_shaves_per_combination=avg_shaves_per_soap|deltas:true}}

## Exclusive Soaps

{{tables.user-single-use-soaps|ranks:20|columns:rank, user, single_use_soaps=exclusive_soaps, shaves|deltas:true}}

## Most Boring Shaver
Boring Score is the chance that two shaves picked at random from a user used the same soap (higher means more repetitive). Effective Soaps converts that into an equivalent even-rotation count: the number of soaps they would need to use equally often to produce the same score. Example: someone can log 20 soaps but still have ~2 Effective Soaps if one soap dominates roughly 70% of their shaves and the rest are just occasional. In the case of tied HHI, Shaves descending is the tie breaker, since it's clearly more boring to use the same soap for 20 shaves than it is for 10.

For the mathematically inclined: Boring Score is a diversity/concentration index (HHI in economics, Simpson’s index in ecology). More detail at [Wikipedia: Diversity index](https://en.wikipedia.org/wiki/Diversity_index).

{{tables.user-soap-brand-scent-diversity|ranks:10|columns:rank, user, hhi desc, shaves desc, effective_soaps, unique_combinations=unique_soaps|deltas:true|shaves:5}}
