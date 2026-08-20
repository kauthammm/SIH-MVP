"""
Standalone Open-Meteo fetch script for KrishiVoice.
REAL DATA from https://open-meteo.com

Usage:
  pip install openmeteo-requests requests-cache retry-requests numpy pandas
  python fetch_openmeteo_weather.py
  python fetch_openmeteo_weather.py --lat 10.7867 --lon 79.1378
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from data/scripts/
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry

from app.services.openmeteo_weather import (
    HOURLY_VARIABLES,
    FORECAST_URL,
    aggregate_daily,
    _extract_hourly_dataframe,
)

# Demo: Thanjavur parcel P0187
DEFAULT_LAT = 10.7867
DEFAULT_LON = 79.1378


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Open-Meteo hourly weather for KrishiVoice")
    parser.add_argument("--lat", type=float, default=DEFAULT_LAT, help="Latitude")
    parser.add_argument("--lon", type=float, default=DEFAULT_LON, help="Longitude")
    parser.add_argument("--days", type=int, default=7, help="Forecast days")
    args = parser.parse_args()

    cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    params = {
        "latitude": args.lat,
        "longitude": args.lon,
        "hourly": HOURLY_VARIABLES,
        "forecast_days": args.days,
        "timezone": "Asia/Kolkata",
    }

    print(f"Fetching Open-Meteo forecast for ({args.lat}, {args.lon})...")
    responses = openmeteo.weather_api(FORECAST_URL, params=params)
    response = responses[0]

    print(f"Coordinates: {response.Latitude()}°N {response.Longitude()}°E")
    print(f"Elevation: {response.Elevation()} m asl")
    print(f"Timezone offset: {response.UtcOffsetSeconds()}s from UTC")

    hourly_dataframe = _extract_hourly_dataframe(response)
    print("\nHourly data (first 24 rows)\n", hourly_dataframe.head(24).to_string())

    daily = aggregate_daily(hourly_dataframe)
    print("\nDaily summary\n", daily.to_string())

    out_dir = Path(__file__).resolve().parent.parent / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    hourly_path = out_dir / "openmeteo_hourly.csv"
    daily_path = out_dir / "openmeteo_daily.csv"
    hourly_dataframe.to_csv(hourly_path, index=False)
    daily.to_csv(daily_path, index=False)
    print(f"\nSaved: {hourly_path}")
    print(f"Saved: {daily_path}")


if __name__ == "__main__":
    main()
