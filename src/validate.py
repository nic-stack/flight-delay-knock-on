"""Compare our monthly figures with BTS's published national figures (data/raw/bts_published_national.json,
from scripts/fetch_bts_published.py). BTS's page also counts codeshare partners that don't report their own flights,
so flight counts differ; rates and delay-minute shares should be close.
Usage: python src/validate.py"""
import json, datetime, duckdb, pandas as pd
pub = json.load(open("data/raw/bts_published_national.json"))
rows = []
for label, v in pub.items():
    d = datetime.datetime.strptime(label, "%B, %Y")
    tot_min = int(v["Total Operations"][2].replace(",", ""))
    m = lambda k: int(v[k][2].replace(",", "")) / tot_min
    rows.append(dict(year_month=d.strftime("%Y-%m"), bts_flights=v["Total Operations"][0], bts_on_time=v["On Time"][1] / 100, bts_cancelled=v["Cancelled"][1] / 100,
                     bts_diverted=v["Diverted"][1] / 100, bts_delay_min=tot_min, bts_carrier=m("Air Carrier Delay"), bts_late_aircraft=m("Aircraft Arriving Late"),
                     bts_nas=m("National Aviation System Delay"), bts_weather=m("Weather Delay")))
pub = pd.DataFrame(rows)
ours = duckdb.sql("""select strftime(flight_date, '%Y-%m') as year_month, count(*) our_flights,
  avg(case when cancelled = 0 and diverted = 0 and coalesce(arr_late15, 0) = 0 then 1 else 0 end) our_on_time, avg(cancelled) our_cancelled, avg(diverted) our_diverted,
  sum(case when arr_late15 = 1 and diverted = 0 then carrier + weather + nas + security + late_aircraft end) our_delay_min,
  sum(carrier) / sum(carrier + weather + nas + security + late_aircraft) our_carrier, sum(late_aircraft) / sum(carrier + weather + nas + security + late_aircraft) our_late_aircraft,
  sum(nas) / sum(carrier + weather + nas + security + late_aircraft) our_nas, sum(weather) / sum(carrier + weather + nas + security + late_aircraft) our_weather
  from 'data/interim/flights.parquet' group by 1""").df()
v = pub.merge(ours, on="year_month").sort_values("year_month")
v["flights_ratio"] = v.our_flights / v.bts_flights
for k in ["on_time", "cancelled", "diverted", "carrier", "late_aircraft", "nas", "weather"]:
    v[f"diff_{k}_pts"] = 100 * (v[f"our_{k}"] - v[f"bts_{k}"])
v.to_csv("outputs/validation_bts.csv", index=False, float_format="%.6g")
show = v[["year_month", "bts_flights", "our_flights", "flights_ratio", "bts_on_time", "our_on_time"] + [c for c in v if c.startswith("diff_")]]
print(show.round(3).to_string(index=False))
print("\nlargest gap in percentage points:", {c: round(v[c].abs().max(), 2) for c in v if c.startswith("diff_")})
