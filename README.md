# coe-quota-premium

> **When COE premiums jump, is the quota tighter — or are more bids chasing the same quota?**

**Status:** scaffolded — question, data and approach are locked; analysis, figures and reproduce steps pending. Part of a six-repo series on Singapore's public data.

## The question

COE prices come out of an auction: a fixed quota meets however many bids show up. When premiums jump, the cause can be a tighter quota (supply) or more bids competing for the same certificates (demand). This repo separates the two, category by category, bidding exercise by bidding exercise, since 2010.

## The data

- **COE Bidding Results / Prices** — LTA, via [data.gov.sg](https://data.gov.sg/datasets/d_69b3380ad7e51aff3a7dcc84eba52b8a/view): month, bidding exercise, vehicle category (A–E), quota, bids received, successful bids, quota premium.
- Licence: Singapore Open Data Licence (© Land Transport Authority).
- Definition caveat carried from the source: Category A/B rules changed from the May 2022 first exercise (EU-style power limits; electric cars up to 110 kW moved into Category A). The series is not one unbroken definition, and the analysis treats it that way.

## Planned approach

- Pressure metrics: bids per quota and success rate, per category per exercise.
- Premium vs quota over time with the May 2022 rule change annotated on every timeline.
- Where premiums move, attribute the move to quota changes vs bid pressure, in plain language.
- One-page memo: the answer per category, and what the data cannot say (why bidders show up; intent; dealer behaviour).

## Done when

The README's chart is reproducible from code; the memo's claims cite the same numbers; the May 2022 boundary is handled explicitly; no forecast.

## Out of scope

Price predictions, dealer-level analysis, and anything treating the series as one consistent definition.

## Licence

Code: MIT. Data: Singapore Open Data Licence — © Land Transport Authority, via data.gov.sg. This is an independent, unofficial analysis.

---

*Part of a six-repo series on Singapore's public data.* **The others:** [hdb-resale-mart](https://github.com/faizsaifulnizam/hdb-resale-mart) · [card-book-quality](https://github.com/faizsaifulnizam/card-book-quality) · [retail-sales-split](https://github.com/faizsaifulnizam/retail-sales-split) · [coe-category-break](https://github.com/faizsaifulnizam/coe-category-break) · [hdb-lease-slope](https://github.com/faizsaifulnizam/hdb-lease-slope)
