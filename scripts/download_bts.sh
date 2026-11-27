#!/bin/bash
# Download 12 months of BTS Reporting Carrier On-Time Performance data (Oct 2025 - Sep 2026).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/raw
BASE=https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present
for ym in 2025_10 2025_11 2025_12 2026_1 2026_2 2026_3 2026_4 2026_5 2026_6 2026_7 2026_8 2026_9; do
  f="data/raw/ontime_${ym}.zip"
  [ -s "$f" ] || curl -fsSL --retry 3 -A "Mozilla/5.0" -o "$f" "${BASE}_${ym}.zip"
  unzip -tq "$f" >/dev/null && echo "ok $ym $(du -h "$f" | cut -f1)"
done
# Lookups: BTS airline names and OurAirports locations (public domain)
curl -fsSL --retry 3 -A "Mozilla/5.0" -o data/raw/carriers.csv "https://www.transtats.bts.gov/Download_Lookup.asp?Y11x72=Y_haVdhR_PNeeVRef"
curl -fsSL --retry 3 -A "Mozilla/5.0" -o data/raw/ourairports.csv "https://davidmegginson.github.io/ourairports-data/airports.csv"
