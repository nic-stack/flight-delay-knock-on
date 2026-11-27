"""Small tables for the dashboard (outputs/dash_*.csv). Run after src/trace.py.
Airport locations come from OurAirports (public domain), data/raw/ourairports.csv."""
import duckdb
con = duckdb.connect()
con.sql("""create view t as select t.*, a.airline_name, caused_carrier + caused_nas + caused_weather + caused_security as spread_min,
  case when arr_late15 = 1 then traced_carrier + traced_nas + traced_weather + traced_security + traced_untraceable else 0 end as delay_min,
  crs_dep // 100 as dep_hour,
  case when arr_late15 = 1 then traced_carrier + traced_nas + traced_weather + traced_security + traced_untraceable - coalesce(late_aircraft, 0) else 0 end as new_min, strftime(flight_date, '%Y-%m') as year_month
  from 'data/interim/traced.parquet' t join read_csv('data/lookup/airlines.csv') a using (airline)""")
con.sql("create view f as select f.*, a.airline_name, strftime(flight_date, '%Y-%m') as year_month from 'data/interim/flights.parquet' f join read_csv('data/lookup/airlines.csv') a using (airline)")
def save(name, q):
    con.sql(f"copy ({q}) to 'outputs/{name}.csv' (header, delimiter ',')"); print(name, con.sql(f"select count(*) from ({q})").fetchall()[0][0])
# KPI and airline tables at airline x month grain so the dashboard filters work
save("dash_airline_month", """
  with o as (select airline_name, year_month, count(*) flights, sum(cancelled) cancelled, sum(diverted) diverted,
      sum(case when cancelled = 0 and diverted = 0 and coalesce(arr_late15, 0) = 0 then 1 else 0 end) on_time,
      sum(case when arr_late15 = 1 and diverted = 0 then 1 else 0 end) late15,
      sum(case when arr_late15 = 1 and diverted = 0 then carrier else 0 end) official_carrier_min,
      sum(case when arr_late15 = 1 and diverted = 0 then carrier + weather + nas + security + late_aircraft else 0 end) official_delay_min from f group by 1, 2),
  tr as (select airline_name, year_month, sum(traced_carrier) traced_carrier_min, sum(traced_nas) traced_nas_min, sum(traced_weather) traced_weather_min,
      sum(traced_security) traced_security_min, sum(traced_untraceable) traced_untraceable_min, sum(spread_min) spread_min from t group by 1, 2)
  select * from o join tr using (airline_name, year_month) order by 1, 2""")
save("dash_hour", """select airline_name, year_month, dep_hour, count(*) flights,
  sum(new_min) as new_delay_min,
  sum(spread_min) spread_min, sum(caused_carrier) spread_carrier_min from t group by 1, 2, 3 order by 1, 2, 3""")
save("dash_airport", """
  with a as (select ident, iata_code, name, latitude_deg as lat, longitude_deg as lon from read_csv('data/raw/ourairports.csv') where iata_code is not null and iso_country in ('US', 'PR', 'VI', 'GU', 'AS', 'MP'))
  select airline_name, year_month, origin, any_value(a.name) airport_name, any_value(a.lat) lat, any_value(a.lon) lon, count(*) flights, sum(spread_min) spread_min, sum(caused_carrier) spread_carrier_min
  from t left join a on a.iata_code = t.origin group by 1, 2, 3 order by 1, 2, 3""")
save("dash_position", """select airline_name, year_month, case when leg = 1 then 'First flight of the day' when leg <= 3 then '2nd-3rd flight' else '4th or later' end as position,
  count(*) flights, sum(spread_min) spread_min, sum(caused_carrier) spread_carrier_min
  from (select *, row_number() over (partition by tail, flight_date order by dep_time, crs_dep) leg from t) group by 1, 2, 3""")
print("airports without a location:", con.sql("select count(distinct origin) from read_csv('outputs/dash_airport.csv') where lat is null").fetchall()[0][0])
