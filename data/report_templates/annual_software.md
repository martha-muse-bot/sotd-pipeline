# {{year}} Lather Log: Year-End Wrap-Up

Welcome to your {{year}} Lather Log. {{total_shaves}} shave reports from {{unique_shavers}} distinct shavers during {{year}} were analyzed to produce this report. Collectively, these shavers used {{unique_soaps}} distinct soaps from {{unique_brands}} distinct brands. {{total_samples}} of those shaves used samples or smushes of {{unique_sample_soaps}} unique soaps. {{total_mashup_shaves}} of those shaves used mashup/mix soaps ({{mashup_users}} users).

## Observations

* [Observations will be generated based on data analysis]

## Notes & Caveats

* Tables show all entries with 5 or more shaves to provide comprehensive coverage without artificial row limits.

* The unique user column shows the number of different users who used a given brand/soap/etc during the year.

* The Brand Diversity table details the number of distinct soaps used during the year from that particular brand, showing all brands with 5+ unique soaps.

* The change Δ vs columns show how an item has moved up or down the rankings since the previous year. = means no change in position, up or down arrows indicate how many positions up or down the rankings an item has moved compared to the previous year. n/a means the item was not present in the previous year.

* An **exclusive soap** is a matched brand+scent used by only one shaver during the year. That shaver earns one point for that soap, no matter how many times they logged it.

## Soap Brands

{{tables.soap-makers|shaves:50|columns:rank, name=brand, shaves, unique_users, avg_shaves_per_user, median_shaves_per_user|deltas:true}}

## Soaps

{{tables.soaps|ranks:100|columns:rank, name=soap, shaves, unique_users, avg_shaves_per_user, median_shaves_per_user|deltas:true|wsdb:true}}

## Brand Diversity

{{tables.brand-diversity|unique_soaps:10|deltas:true}}

## Top Mashup Users

{{tables.soap-mashup-users|shaves:10|columns:rank, user, shaves, unique_users|deltas:true}}

## Soap Diversity by User

{{tables.user-soap-brand-scent-diversity|ranks:50|columns:rank, user, unique_combinations=unique_soaps, shaves, avg_shaves_per_combination=avg_shaves_per_soap|deltas:true}}

## Exclusive Soaps

{{tables.user-single-use-soaps|ranks:50|columns:rank, user, single_use_soaps=exclusive_soaps, shaves|deltas:true}}

## Most Boring Shaver
Boring Score is the chance that two shaves picked at random from a user used the same soap (higher means more repetitive). Effective Soaps converts that into an equivalent even-rotation count: the number of soaps they would need to use equally often to produce the same score. Example: someone can log 20 soaps but still have ~2 Effective Soaps if one soap dominates roughly 70% of their shaves and the rest are just occassional. 

For the mathematically inclined: Boring Score is a diversity/concentration index (HHI in economics, Simpson’s index in ecology). More detail at [Wikipedia: Diversity index](https://en.wikipedia.org/wiki/Diversity_index).

{{tables.user-soap-brand-scent-diversity|ranks:50|columns:rank, user, hhi=boring score desc, shaves desc, effective_soaps, unique_combinations=unique_soaps|deltas:true|shaves:50}}
