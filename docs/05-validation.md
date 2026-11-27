# Validation against BTS's published figures

BTS publishes national monthly totals on its "Airline On-Time Statistics and Delay Causes" page. `scripts/fetch_bts_published.py` saves them (`data/raw/bts_published_national.json`, the page for each month, checked by its month label) and `src/validate.py` compares them with our file (`outputs/validation_bts.csv`).

## Why flight counts differ

BTS's page counts marketing, reporting and codeshare carriers. Our file has only the 14 airlines that report their own flights, so it holds 90 to 91% of BTS's flights in every month. Because the gap is steady, rates and shares are the right comparison.

## Results (12 months)

| Measure | Largest monthly gap |
|---|--:|
| On-time rate | 0.35 points |
| Cancelled | 0.17 points |
| Diverted | 0.02 points |
| Carrier share of delay minutes | 1.05 points (ours higher) |
| Late-aircraft share | 1.40 points (ours lower) |
| Airspace share | 0.48 points |
| Weather share | 0.15 points |

Example, September 2026: on time 76.56% (BTS) vs 76.24% (ours); carrier share of delay minutes 29.29% vs 29.64%.

## What this does and doesn't show

- It confirms that loading and filtering are right, and that the 14 reporting airlines represent the national picture closely.
- It is not an independent check of the delay causes themselves: both come from the airlines' own reports.
- The tracing has no external benchmark. It is checked internally (every minute accounted for, forward and backward passes agree; see `03-tracing-method.md`).
