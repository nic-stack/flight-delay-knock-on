"""Trace late-aircraft delay back to where it started.

For each aircraft, completed flights are put in order of departure (across midnight). A flight's late-aircraft
minutes are traceable when the previous flight landed at this flight's origin and was itself 15+ minutes late
(so its causes are recorded). Traceable minutes are split in the same proportions as the previous flight's traced
causes; minutes that can't be traced are labelled untraceable.

Forward pass:  traced cause minutes for every flight (carrier, weather, nas, security, untraceable).
Backward pass: minutes each flight's own delay caused on the aircraft's later flights ("downstream" minutes).
The two passes must agree.

Usage: python src/trace.py data/interim/flights.parquet data/interim/traced.parquet
"""
import sys, duckdb, numpy as np
src, out = sys.argv[1:3]
con = duckdb.connect()
df = con.sql(f"""
  with legs as (
    select *, flight_date + to_minutes((((coalesce(dep_time, crs_dep) % 2400) // 100) * 60 + (coalesce(dep_time, crs_dep) % 100))::bigint)
      + case when dep_time is not null and dep_time < crs_dep - 1200 then interval 1 day else interval 0 day end as dep_ts
    from read_parquet('{src}') where cancelled = 0 and tail is not null and tail <> '')
  select row_number() over () as flight_id, *, lag(dest) over w as prev_dest, lag(arr_late15) over w as prev_late15, lag(diverted) over w as prev_diverted
  from legs window w as (partition by tail order by dep_ts, crs_dep)
  order by tail, dep_ts, crs_dep""").df()
n = len(df)
C = ["carrier", "weather", "nas", "security"]
late = (df.arr_late15.fillna(0).to_numpy() == 1) & (df.diverted.to_numpy() == 0)
direct = np.where(late[:, None], df[C].fillna(0).to_numpy(), 0.0)          # own non-late-aircraft minutes
la = np.where(late, df.late_aircraft.fillna(0).to_numpy(), 0.0)            # own late-aircraft minutes
total = direct.sum(1) + la
traceable = (df.prev_dest.to_numpy() == df.origin.to_numpy()) & (df.prev_late15.fillna(0).to_numpy() == 1) & (df.prev_diverted.fillna(1).to_numpy() == 0)
newtail = np.r_[True, df["tail"].to_numpy()[1:] != df["tail"].to_numpy()[:-1]]
traceable &= ~newtail
traceable &= np.r_[0.0, total[:-1]] > 0   # previous flight must have recorded cause minutes

# Forward: traced[i] = direct[i] + la[i] * share(prev) ; columns carrier, weather, nas, security, untraceable
traced = np.zeros((n, 5))
traced[:, :4] = direct
prev_share = np.zeros(5)
for i in range(n):
    if la[i] > 0:
        if traceable[i]:
            traced[i] += la[i] * prev_share
        else:
            traced[i, 4] += la[i]
    prev_share = traced[i] / total[i] if total[i] > 0 else np.zeros(5)

# Backward: minutes passed back from later flights, credited to each flight's own causes
down = np.zeros((n, 5))            # downstream minutes caused, by this flight's own cause (untraceable column unused here)
carry = 0.0
for i in range(n - 1, -1, -1):
    incoming = carry
    carry = 0.0
    if total[i] > 0:
        down[i, :4] = incoming * direct[i] / total[i]
        passing = (la[i] + incoming * la[i] / total[i])
        if traceable[i]:
            carry = passing
        else:
            down[i, 4] = passing   # reached a dead end: untraceable
    # a flight with no delay can't receive minutes (the next flight would not be traceable to it)

out_df = df[["flight_id", "flight_date", "airline", "tail", "flight_no", "origin", "dest", "crs_dep", "dep_time", "dep_block", "arr_delay", "arr_late15", "late_aircraft"]].copy()
for k, c in enumerate(C + ["untraceable"]):
    out_df[f"traced_{c}"] = traced[:, k]
    out_df[f"caused_{c}"] = down[:, k]
out_df["la_traceable"] = np.where(la > 0, traceable, None)
con.register("o", out_df)
con.sql(f"copy (select * from o) to '{out}' (format parquet)")

# Checks
own_all = direct.sum() + la.sum()
print(f"flights traced: {n:,}")
print(f"delay minutes: {own_all:,.0f}  traced total: {traced.sum():,.0f}  (must match)")
print(f"late-aircraft minutes: {la.sum():,.0f}  -> traceable part reassigned: {traced[:, :4].sum() - direct.sum():,.0f}, untraceable: {traced[:, 4].sum():,.0f}")
print(f"backward check: downstream credited {down[:, :4].sum():,.0f} vs forward reassigned {traced[:, :4].sum() - direct.sum():,.0f}; untraceable {down[:, 4].sum():,.0f} vs {traced[:, 4].sum():,.0f}")
