"""Small tables for the Tableau dashboard (outputs/tb_*.csv). Each has an 'All airlines' version plus one per airline,
so a single airline dropdown can switch every chart. Run after src/trace.py."""
import duckdb
con = duckdb.connect(config={"threads": 1})   # single thread: sums come out identical on every run
con.sql("""create view t as select t.*, a.airline_name, caused_carrier + caused_nas + caused_weather + caused_security as knock_min,
  case when arr_late15 = 1 then traced_carrier + traced_nas + traced_weather + traced_security + traced_untraceable - coalesce(late_aircraft, 0) else 0 end as new_min,
  crs_dep // 100 as dep_hour from 'data/interim/traced.parquet' t join read_csv('data/lookup/airlines.csv') a using (airline)""")
con.sql("""create view f as select f.*, a.airline_name, case when arr_late15 = 1 and diverted = 0 then 1 else 0 end as late,
  case when arr_late15 = 1 and diverted = 0 then carrier else 0 end oc, case when arr_late15 = 1 and diverted = 0 then nas else 0 end onas,
  case when arr_late15 = 1 and diverted = 0 then weather + security else 0 end owx, case when arr_late15 = 1 and diverted = 0 then late_aircraft else 0 end ola
  from 'data/interim/flights.parquet' f join read_csv('data/lookup/airlines.csv') a using (airline)""")
def both(q):   # q uses {g} for the grouping column: airline_name, or the constant 'All airlines'
    return f"select * from ({q.format(g='airline_name')}) union all select * from ({q.format(g=chr(39) + 'All airlines' + chr(39))})"
def save(name, q):
    con.sql(f"copy (select * from ({q}) order by all) to 'outputs/{name}.csv' (header, delimiter ',')"); print(name, con.sql(f"select count(*) from ({q})").fetchall()[0][0])
save("tb_kpi", both("""select {g} as airline_name, count(*) flights, sum(late) / sum(1 - cancelled - diverted) late_share, avg(cancelled) cancelled_share,
  sum(oc + onas + owx + ola) delay_min from f group by all"""))
save("tb_cause", both("""with o as (select {g} as airline_name, sum(oc) oc, sum(onas) onas, sum(owx) owx, sum(oc + onas + owx + ola) tot from f group by all),
  tr as (select {g} as airline_name, sum(traced_carrier) tc, sum(traced_nas) tn, sum(traced_weather + traced_security) tw, sum(traced_untraceable) tu from t group by all)
  select airline_name, c.* from o join tr using (airline_name), lateral (values
    (1, 'Caused by the airline', 'Airline''s own (reported)', oc / tot), (1, 'Caused by the airline', 'Airline''s own (knock-on)', (tc - oc) / tot),
    (2, 'Air traffic system', 'Other causes (reported)', onas / tot), (2, 'Air traffic system', 'Other causes (knock-on)', (tn - onas) / tot),
    (3, 'Weather', 'Other causes (reported)', owx / tot), (3, 'Weather', 'Other causes (knock-on)', (tw - owx) / tot),
    (4, 'Start unknown*', 'Start unknown (knock-on)', tu / tot)) c(cause_order, cause, part, share)"""))
save("tb_hour", both("""select {g} as airline_name, dep_hour, sum(knock_min) / nullif(sum(new_min), 0) * 15 as knock_per_15 from t where dep_hour between 5 and 22 group by all"""))
save("tb_airline", """with o as (select airline_name, sum(oc) / sum(oc + onas + owx + ola) reported from f group by 1),
  tr as (select airline_name, sum(traced_carrier) / sum(traced_carrier + traced_nas + traced_weather + traced_security + traced_untraceable) knock from t group by 1)
  select airline_name, 'Reported' as measure, reported as share from o where airline_name <> 'Hawaiian'
  union all select airline_name, 'With knock-on delay', knock from tr where airline_name <> 'Hawaiian'""")
save("tb_airport", both("""with a as (select iata_code, any_value(latitude_deg) lat, any_value(longitude_deg) lon from read_csv('data/raw/ourairports.csv')
     where iata_code is not null and iso_country = 'US' group by 1),
  s as (select {g} as airline_name, origin, sum(knock_min) knock_min, sum(caused_carrier) / nullif(sum(knock_min), 0) own_share from t group by all)
  select s.*, a.lat, a.lon, case when own_share > 0.5 then 'Mostly the airline''s own' else 'Mostly air traffic / weather' end as who
  from s join a on a.iata_code = s.origin where knock_min > 0 qualify row_number() over (partition by airline_name order by knock_min desc) <= 30"""))
save("tb_position", both("""select {g} as airline_name, case when leg = 1 then 'First flight' when leg <= 3 then '2nd-3rd' else '4th or later' end as position,
  sum(caused_carrier) / sum(knock_min) as airline_share
  from (select *, row_number() over (partition by tail, flight_date order by dep_time, crs_dep) leg from t) group by all"""))

# text helpers for the charts
con.sql("""copy (select c.*, case when cause = 'Start unknown*' then round(100 * sum(share) over w)::int || '%  (knock-on, start unknown)'
    else round(100 * sum(share) filter (where part like '%(reported)') over w)::int || '% reported + ' || round(100 * sum(share) filter (where part like '%(knock-on)') over w)::int
    || '% knock-on = ' || round(100 * sum(share) over w)::int || '%' end as label
  from 'outputs/tb_cause.csv' c window w as (partition by airline_name, cause) order by all) to 'outputs/tb_cause.csv' (header, delimiter ',')""")
con.sql("""copy (select *, case when dep_hour < 12 then dep_hour || 'a' when dep_hour = 12 then '12p' else (dep_hour - 12) || 'p' end as hour_label
  from 'outputs/tb_hour.csv' order by all) to 'outputs/tb_hour.csv' (header, delimiter ',')""")
print("labels added")
