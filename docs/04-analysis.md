# Analysis

*Wording note: "traced" in these notes means knock-on delay (delay passed from one flight to the next on the same plane) followed back to where it started. Spread per minute × 15 gives the dashboard's "minutes per 15-minute delay" (0.60 → 9.0 in the morning, 0.17 → 2.5 in the evening).*

Script: `src/analysis.py` → `outputs/*.csv`, full run in `outputs/analysis_run.txt`.

## 1. How much delay is in the airline's control?

| Cause | Official share | Traced to where it started |
|---|--:|--:|
| Carrier | 32.6% | **44.8%** |
| National Airspace System | 21.3% | 32.5% |
| Weather | 6.0% | 7.8% |
| Security | 0.1% | 0.2% |
| Late aircraft | 40.1% | reassigned |
| Untraceable | – | 14.6% |

Controllable (carrier) delay is **at least 45%** of delay minutes. If the untraceable minutes split like the traceable ones it is about **52%**; at most 59%. *(Agreed headline: "at least 45%, likely about half".)*

## 2. When does delay start, and when does it spread?

| Departure time | Flights | New delay | Spread to later flights | Spread per minute of new delay |
|---|--:|--:|--:|--:|
| Morning (5-11) | 42.3% | 33.2% | **46.7%** | **0.60** |
| Afternoon (12-16) | 29.3% | 32.1% | 39.7% | 0.52 |
| Evening/night (17-4) | 28.4% | **34.7%** | 13.7% | 0.17 |

Evening flights pick up the most new delay, but it rarely spreads because aircraft stop overnight. Each minute of new delay from 7 to 11 a.m. causes about 0.6 to 0.7 minutes on the aircraft's later flights; after 7 p.m., under 0.15. This is partly built in (a morning flight has more flights after it), which is exactly why morning delay is the costly kind.

## 3. Airlines

Traced carrier share ranges from 27% (Envoy) to 58% (Delta), excluding Hawaiian (86%, small and inter-island). American has the largest untraceable share (27%), so its controllable share is the least certain. Frontier, Allegiant and PSA spread the most minutes per flight (7 to 8); SkyWest the least (2.5).

## 4. Airports and routes

The ten busiest airports handle 33.8% of flights and cause 34.4% of spread minutes, in line with their size. Relative to size, Washington National (1.54x), Chicago Midway (1.52x), Philadelphia (1.47x), Dallas Love Field (1.45x) and LaGuardia (1.35x) spread the most; Chicago O'Hare spreads the most in total (7.5%). The top routes for spread are Southwest's California and Las Vegas legs and the LaGuardia shuttles to Chicago, Washington and Boston; the shuttles' spread is mostly airspace delay (only 12 to 22% carrier).

## 5. First flight of the day

The first flight of the day is 25.2% of flights and causes 25.6% of spread minutes, but its spread is the most controllable: 56% carrier, against 45% for later flights.

## Prediction check

| Prediction | Result |
|---|---|
| Carrier delay is the biggest controllable cause | Right, and larger than reported (32.6% official, 44.8% traced) |
| Chains start on evening flights | Mostly wrong: evening delay is common but rarely spreads |
| ...at big hubs | Partly: the biggest hubs spread in line with their size; smaller congested airports spread more for their size |
