"""Profile the year of flights: coverage, delays, causes, and whether aircraft can be followed flight to flight.
Usage: python src/profile.py data/interim/flights.parquet > outputs/profile.txt"""
import sys, duckdb
con = duckdb.connect()
con.sql(f"create view f as select * from read_parquet('{sys.argv[1]}')")
def show(title, q):
    print(f"## {title}"); print(con.sql(q).df().to_string(index=False)); print()
show("Coverage", """select count(*) flights, min(flight_date) first_day, max(flight_date) last_day, count(distinct airline) airlines,
  count(distinct tail) aircraft, count(distinct origin) airports, round(100*avg(cancelled),2) pct_cancelled, round(100*avg(diverted),2) pct_diverted,
  count(*) filter (tail is null or tail = '') no_tail from f""")
show("By month", """select strftime(flight_date, '%Y-%m') as year_month, count(*) flights, round(100*avg(cancelled),2) pct_cancelled,
  round(100*avg(arr_late15) filter (cancelled = 0 and diverted = 0),1) pct_late15 from f group by 1 order by 1""")
show("Cancellation reasons (A carrier, B weather, C airspace system, D security)", "select cancel_code, count(*) flights from f where cancelled = 1 group by 1 order by 1")
show("Cause minutes add up to arrival delay (flights 15+ min late)", """select count(*) late15, count(*) filter (carrier is null) causes_missing,
  count(*) filter (abs(carrier + weather + nas + security + late_aircraft - arr_delay) <= 0.5) causes_add_up from f where arr_late15 = 1""")
show("Causes recorded on flights under 15 min late", "select count(*) filter (carrier is not null) rows from f where coalesce(arr_late15, 0) = 0")
show("Delay minutes by official cause", """select round(sum(carrier)/1e6,2) carrier_m, round(sum(late_aircraft)/1e6,2) late_aircraft_m, round(sum(nas)/1e6,2) nas_m,
  round(sum(weather)/1e6,2) weather_m, round(sum(security)/1e6,3) security_m,
  round(100*sum(carrier)/sum(carrier+late_aircraft+nas+weather+security),1) carrier_pct, round(100*sum(late_aircraft)/sum(carrier+late_aircraft+nas+weather+security),1) late_aircraft_pct,
  round(100*sum(nas)/sum(carrier+late_aircraft+nas+weather+security),1) nas_pct, round(100*sum(weather)/sum(carrier+late_aircraft+nas+weather+security),1) weather_pct from f""")
show("By airline", """select airline, count(*) flights, round(100*avg(arr_late15) filter (cancelled = 0 and diverted = 0),1) pct_late15, round(100*avg(cancelled),2) pct_cancelled,
  round(100*sum(late_aircraft)/sum(carrier+late_aircraft+nas+weather+security),1) late_aircraft_pct, count(distinct tail) aircraft from f group by 1 order by flights desc""")
# Following each aircraft across days, in order of departure (local times; wrap past midnight)
con.sql("""create table legs as select *, flight_date + to_minutes((((coalesce(dep_time, crs_dep) % 2400) // 100) * 60 + (coalesce(dep_time, crs_dep) % 100))::bigint)
  + case when dep_time is not null and dep_time < crs_dep - 1200 then interval 1 day else interval 0 day end as dep_ts
  from f where cancelled = 0 and tail is not null and tail <> ''""")
con.sql("""create table chained as select *, lag(dest) over w prev_dest, lag(arr_delay) over w prev_arr_delay, lag(flight_date) over w prev_date, lag(diverted) over w prev_diverted
  from legs window w as (partition by tail order by dep_ts, crs_dep)""")
show("Following aircraft flight to flight", """select count(*) legs, count(*) filter (prev_dest is not null) with_previous,
  round(100*avg(case when prev_dest = origin then 1 else 0 end) filter (prev_dest is not null),2) pct_previous_lands_at_this_origin,
  round(100*avg(case when prev_date < flight_date then 1 else 0 end) filter (prev_dest is not null),1) pct_previous_on_earlier_day from chained""")
show("Late-aircraft delays: is the previous flight traceable?", """select count(*) late_aircraft_flights, round(sum(late_aircraft)/1e6,2) minutes_m,
  round(100*sum(late_aircraft) filter (prev_dest = origin) / sum(late_aircraft),1) pct_min_previous_connects,
  round(100*sum(late_aircraft) filter (prev_dest = origin and prev_arr_delay >= 15) / sum(late_aircraft),1) pct_min_previous_15plus_late,
  round(100*sum(late_aircraft) filter (prev_dest = origin and prev_date < flight_date) / sum(late_aircraft),1) pct_min_previous_was_overnight
  from chained where late_aircraft > 0""")
