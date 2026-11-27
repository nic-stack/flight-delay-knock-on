# Tracing method

Script: `src/trace.py` → `data/interim/traced.parquet`. Checks: `outputs/trace_checks.txt`.

## Rules

| Step | Rule |
|---|---|
| Flights used | Completed flights with a tail number: 6,922,507 (cancelled flights have no delay minutes) |
| Order | Each aircraft's flights in order of actual departure (scheduled if missing), local time, across midnight. A departure more than 12 hours before its scheduled time is treated as after midnight |
| Traceable | A flight's late-aircraft minutes are traceable when the previous flight landed at this flight's origin, wasn't diverted, was 15+ minutes late, and has cause minutes recorded |
| Split | Traceable minutes take the previous flight's traced cause mix (carrier, airspace system, weather, security, untraceable). Applied in order, this carries each minute back to where the chain started |
| Untraceable | Late-aircraft minutes that fail the traceable test, plus any untraceable share inherited from earlier flights |
| Spread | The backward pass credits each flight with the minutes its own new delay caused on the aircraft's later flights |

## Checks

- All 117,300,493 delay minutes on completed flights are accounted for after tracing.
- Of 46,994,298 late-aircraft minutes, 29,846,374 trace back to a cause and 17,147,924 are untraceable.
- The forward and backward passes agree exactly: 29,846,374 spread minutes and 17,147,924 untraceable minutes in both.
- Untraceable is 36.5% of late-aircraft minutes, higher than the 25.7% that can't be followed one step back, because minutes also inherit untraceable shares from earlier in the chain.

## Limits

- Times are local and BTS doesn't give time zones, so ordering relies on departure order; the previous flight lands at the next origin 98.3% of the time.
- Causes are self-reported by airlines, and delays under 15 minutes have no cause, so small delays can't be followed.
- The split rule is a proportional assumption, not a measurement of which minute caused which.
