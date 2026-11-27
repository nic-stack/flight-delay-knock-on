# Data profile

Source: BTS Reporting Carrier On-Time Performance, October 2025 to September 2026. `src/load.py` combines the 12 monthly files into `data/interim/flights.parquet`; `src/profile.py` writes `outputs/profile.txt`. Airline names come from the BTS carrier lookup (`data/raw/carriers.csv`).

## What's in the data

| | |
|---|---|
| Flights | 7,057,696 |
| Airlines | 14 (Southwest is the largest with 1.39M flights; Hawaiian the smallest with 20K) |
| Coverage gaps | Hawaiian reports only October to December 2025, and Spirit only October 2025 to May 2026 |
| Aircraft | 6,347 tail numbers; none appears under two airlines |
| Airports | 361 |
| Cancelled / diverted | 1.92% / 0.30% |
| Arrived 15+ min late | 1,604,186 flights (about 23% of completed flights) |

One row is one scheduled flight. Times are local to each airport, and causes are reported by the airline.

## Checks

- **Delay causes add up.** On 1,604,027 of 1,604,186 late flights, the five cause columns sum to the arrival delay (within half a minute). One late flight has no causes.
- **Causes exist only for flights 15+ minutes late.** No cause minutes appear on flights under 15 minutes late.
- **Missing tail numbers:** 18,465 flights.
- **Seasonality:** the late share ranges from 19.8% (February) to 28.3% (July). Cancellations peak in January (4.71%).
- **Cancellations** are mostly weather (81,628), then carrier (29,678) and the airspace system (23,767).

## Delay minutes by official cause

| Cause | Minutes | Share |
|---|--:|--:|
| Late aircraft | 46.99M | 40.1% |
| Carrier | 38.19M | 32.6% |
| National Airspace System | 24.97M | 21.3% |
| Weather | 6.98M | 6.0% |
| Security | 0.17M | 0.1% |

Late aircraft is the largest cause overall and ranges from 22% (SkyWest) to 52% (Frontier) by airline.

## Can we follow each aircraft?

Completed flights for each tail number are put in order of departure time, across midnight.

- The previous flight landed at this flight's origin **98.3%** of the time, so the order is reliable even though times are local.
- For late-aircraft minutes: **93.3%** have a connecting previous flight, and **74.3%** have a previous flight that was 15+ minutes late, so its causes can be followed. **3.2%** come from a previous flight on an earlier day.
- The remaining **25.7%** can't be traced: either the chain is broken (6.7%) or the previous flight was under 15 minutes late, so it has no recorded cause. These are reported as **untraceable**.

## Method decisions (agreed)

1. Chains continue across midnight.
2. Inherited minutes that can't be traced are labelled untraceable, not guessed.
3. Late-aircraft minutes are split in the same proportions as the previous flight's (already traced) causes, back to the start of the chain.

## Prediction recorded before analysis

The biggest controllable cause is carrier delay, and delay chains start mostly on evening flights at big hubs.
