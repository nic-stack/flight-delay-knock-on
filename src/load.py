"""Combine the 12 monthly BTS files into one Parquet file with the columns this project uses.
Usage: python src/load.py data/raw data/interim/flights.parquet"""
import glob, os, sys, tempfile, zipfile, duckdb
raw, out = sys.argv[1:3]
zips = sorted(glob.glob(os.path.join(raw, "ontime_*.zip")))
assert len(zips) == 12, f"expected 12 monthly files, found {len(zips)}"
COLS = """FlightDate::date as flight_date, Reporting_Airline as airline, Tail_Number as tail, Flight_Number_Reporting_Airline as flight_no,
 Origin as origin, OriginCityName as origin_city, Dest as dest, DestCityName as dest_city,
 CRSDepTime::int as crs_dep, try_cast(DepTime as int) as dep_time, DepTimeBlk as dep_block, CRSArrTime::int as crs_arr, try_cast(ArrTime as int) as arr_time,
 try_cast(DepDelayMinutes as double) as dep_delay, try_cast(ArrDelayMinutes as double) as arr_delay, try_cast(ArrDel15 as double)::int as arr_late15,
 Cancelled::double::int as cancelled, CancellationCode as cancel_code, Diverted::double::int as diverted,
 try_cast(CarrierDelay as double) as carrier, try_cast(WeatherDelay as double) as weather, try_cast(NASDelay as double) as nas,
 try_cast(SecurityDelay as double) as security, try_cast(LateAircraftDelay as double) as late_aircraft,
 try_cast(Distance as double) as distance"""
con = duckdb.connect()
with tempfile.TemporaryDirectory() as tmp:
    parts = []
    for z in zips:
        with zipfile.ZipFile(z) as zf:
            name = [n for n in zf.namelist() if n.endswith(".csv")][0]
            zf.extract(name, tmp)
        part = os.path.join(tmp, os.path.basename(z).replace(".zip", ".parquet"))
        con.sql(f"copy (select {COLS} from read_csv('{os.path.join(tmp, name)}', all_varchar=true, header=true)) to '{part}' (format parquet)")
        os.remove(os.path.join(tmp, name)); parts.append(part)
        print(os.path.basename(z), con.sql(f"select count(*) from '{part}'").fetchall()[0][0])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    con.sql(f"copy (select * from read_parquet({parts!r}) order by flight_date, airline, tail, dep_time) to '{out}' (format parquet)")
print("total", con.sql(f"select count(*) from '{out}'").fetchall()[0][0])
