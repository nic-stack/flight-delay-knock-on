"""Analysis tables from the traced flights. Writes CSVs to outputs/ and prints a summary.
Usage: python src/analysis.py"""
import duckdb, pathlib
out = pathlib.Path("outputs"); out.mkdir(exist_ok=True)
con = duckdb.connect()
con.sql("""create view t as select t.*, a.airline_name,
  traced_carrier + traced_nas + traced_weather + traced_security + traced_untraceable as delay_min,
  caused_carrier + caused_nas + caused_weather + caused_security as spread_min,
  crs_dep // 100 as dep_hour,
  case when crs_dep // 100 between 5 and 11 then 'Morning (5-11)' when crs_dep // 100 between 12 and 16 then 'Afternoon (12-16)' else 'Evening/night (17-4)' end as period
  from 'data/interim/traced.parquet' t join read_csv('data/lookup/airlines.csv') a using (airline)""")
con.sql("""create view f as select * from 'data/interim/flights.parquet'""")
con.sql("""create view own as select *, case when arr_late15 = 1 and diverted = 0 then coalesce(carrier,0) + coalesce(nas,0) + coalesce(weather,0) + coalesce(security,0) else 0 end as new_min,
  case when arr_late15 = 1 and diverted = 0 then coalesce(carrier,0) + coalesce(nas,0) + coalesce(weather,0) + coalesce(security,0) + coalesce(late_aircraft,0) else 0 end as official_min,
  case when arr_late15 = 1 and diverted = 0 then coalesce(carrier,0) else 0 end as official_carrier from f where cancelled = 0 and tail <> ''""")
def save(name, q):
    df = con.sql(q).df(); df.to_csv(out / f"{name}.csv", index=False, float_format="%.6g")
    print(f"## {name}"); print(df.to_string(index=False)); print()
save("cause_official_vs_traced", """
  with o as (select sum(official_min) tot, sum(official_carrier) car, sum(case when arr_late15=1 and diverted=0 then nas end) nas, sum(case when arr_late15=1 and diverted=0 then weather end) wx,
     sum(case when arr_late15=1 and diverted=0 then security end) sec, sum(case when arr_late15=1 and diverted=0 then late_aircraft end) la from own),
  tr as (select sum(delay_min) tot, sum(traced_carrier) car, sum(traced_nas) nas, sum(traced_weather) wx, sum(traced_security) sec, sum(traced_untraceable) un from t)
  select 'Carrier' cause, o.car/o.tot official_share, tr.car/tr.tot traced_share from o, tr union all
  select 'National Airspace System', o.nas/o.tot, tr.nas/tr.tot from o, tr union all
  select 'Weather', o.wx/o.tot, tr.wx/tr.tot from o, tr union all
  select 'Security', o.sec/o.tot, tr.sec/tr.tot from o, tr union all
  select 'Late aircraft', o.la/o.tot, 0 from o, tr union all
  select 'Untraceable', 0, tr.un/tr.tot from o, tr""")
save("controllable_range", """
  with s as (select sum(delay_min) tot, sum(traced_carrier) car, sum(traced_untraceable) un,
    sum(caused_carrier) cc, sum(caused_carrier + caused_nas + caused_weather + caused_security) ct from t)
  select car/tot as lower_bound, (car + un * cc / ct)/tot as proportional_estimate, (car + un)/tot as upper_bound from s""")
save("by_period", """
  with a as (select period, count(*) flights, sum(new_min) new_min from (select *, case when crs_dep // 100 between 5 and 11 then 'Morning (5-11)' when crs_dep // 100 between 12 and 16 then 'Afternoon (12-16)' else 'Evening/night (17-4)' end period from own) group by 1),
  b as (select period, sum(spread_min) spread_min from t group by 1)
  select period, flights / sum(flights) over () as share_flights, new_min / sum(new_min) over () as share_new_delay,
    spread_min / sum(spread_min) over () as share_spread, spread_min / new_min as spread_per_new_minute from a join b using (period) order by period desc""")
save("by_hour", """
  with a as (select crs_dep // 100 dep_hour, count(*) flights, sum(new_min) new_min from own group by 1), b as (select dep_hour, sum(spread_min) spread_min from t group by 1)
  select dep_hour, flights, new_min, spread_min, spread_min / nullif(new_min, 0) spread_per_new_minute from a join b using (dep_hour) order by 1""")
save("by_airline", """
  with o as (select airline, count(*) flights, avg(arr_late15) filter (diverted = 0) late15, sum(official_carrier) / sum(official_min) official_carrier_share from own group by 1),
  tr as (select airline, airline_name, sum(traced_carrier)/sum(delay_min) traced_carrier_share, sum(traced_untraceable)/sum(delay_min) untraceable_share,
    sum(delay_min)/count(*) delay_min_per_flight, sum(spread_min)/count(*) spread_min_per_flight from t group by 1, 2)
  select airline_name, airline, flights, late15 share_late15, official_carrier_share, traced_carrier_share, untraceable_share, delay_min_per_flight, spread_min_per_flight
  from o join tr using (airline) order by flights desc""")
save("by_airport", """
  with s as (select origin, count(*) flights, sum(spread_min) spread_min, sum(caused_carrier) spread_carrier from t group by 1)
  select origin, flights, flights / sum(flights) over () share_flights, spread_min / sum(spread_min) over () share_spread,
    (spread_min / sum(spread_min) over ()) / (flights / sum(flights) over ()) spread_index, spread_carrier / spread_min carrier_share_of_spread
  from s where flights >= 20000 order by spread_min desc""")
save("top_routes", """
  select airline_name, origin || '-' || dest route, count(*) flights, sum(spread_min) spread_min, sum(spread_min)/count(*) spread_per_flight, sum(caused_carrier)/sum(spread_min) carrier_share
  from t group by 1, 2 having count(*) >= 300 order by spread_min desc limit 15""")
save("first_flight_of_day", """
  with s as (select *, row_number() over (partition by tail, flight_date order by dep_time, crs_dep) leg from t)
  select case when leg = 1 then 'First flight of the day' when leg <= 3 then '2nd-3rd' else '4th or later' end as position,
    count(*) flights, count(*) / sum(count(*)) over () share_flights, sum(spread_min) / sum(sum(spread_min)) over () share_spread, sum(caused_carrier) / sum(spread_min) carrier_share
  from s group by 1 order by 1""")
