"""
Open-Meteo weather integration for KrishiVoice.
REAL DATA source: https://open-meteo.com (free, no API key).

Uses openmeteo_requests with requests-cache and retry-requests.
"""
from __future__ import annotations

import logging
import time
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import numpy as np
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry

from app.config import get_settings

logger = logging.getLogger(__name__)

# In-memory cache — avoids slow Open-Meteo call on every voice message
_WEATHER_CTX_CACHE: dict[tuple[float, float], tuple[float, dict]] = {}
WEATHER_CACHE_SECONDS = 1800  # 30 minutes

# Order matters — must match Open-Meteo hourly parameter list
HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "wind_direction_180m",
    "wind_gusts_10m",
    "temperature_80m",
    "temperature_120m",
    "temperature_180m",
    "wind_speed_10m",
    "wind_speed_80m",
    "wind_speed_180m",
    "wind_speed_120m",
    "wind_direction_10m",
    "wind_direction_80m",
    "wind_direction_120m",
    "surface_pressure",
    "rain",
    "showers",
    "soil_temperature_0cm",
    "soil_temperature_6cm",
    "soil_temperature_18cm",
    "soil_temperature_54cm",
    "soil_moisture_0_to_1cm",
    "soil_moisture_1_to_3cm",
    "soil_moisture_3_to_9cm",
    "soil_moisture_9_to_27cm",
    "soil_moisture_27_to_81cm",
]

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

ARCHIVE_DAILY_VARS = [
    "temperature_2m_mean",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "rain_sum",
    "showers_sum",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "relative_humidity_2m_mean",
    "et0_fao_evapotranspiration",
]


@lru_cache
def _get_client() -> openmeteo_requests.Client:
    settings = get_settings()
    cache_dir = Path(settings.openmeteo_cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_session = requests_cache.CachedSession(
        str(cache_dir / "openmeteo"),
        expire_after=settings.openmeteo_cache_seconds,
    )
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    return openmeteo_requests.Client(session=retry_session)


def _extract_hourly_dataframe(response) -> pd.DataFrame:
    """Parse Open-Meteo hourly response into a pandas DataFrame."""
    hourly = response.Hourly()
    hourly_data: dict[str, Any] = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left",
        )
    }
    for i, var in enumerate(HOURLY_VARIABLES):
        hourly_data[var] = hourly.Variables(i).ValuesAsNumpy()

    df = pd.DataFrame(hourly_data)
    # Local date for Tamil Nadu (IST = UTC+5:30)
    df["local_date"] = df["date"].dt.tz_convert("Asia/Kolkata").dt.date
    return df


def fetch_hourly_forecast(
    latitude: float,
    longitude: float,
    forecast_days: int = 7,
    timezone: str = "Asia/Kolkata",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Fetch full hourly forecast from Open-Meteo.
    Returns (hourly_dataframe, metadata).
    """
    client = _get_client()
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": HOURLY_VARIABLES,
        "forecast_days": min(forecast_days, 16),
        "timezone": timezone,
    }
    responses = client.weather_api(FORECAST_URL, params=params)
    response = responses[0]

    meta = {
        "source": "open-meteo",
        "latitude": response.Latitude(),
        "longitude": response.Longitude(),
        "elevation_m": response.Elevation(),
        "utc_offset_seconds": response.UtcOffsetSeconds(),
        "timezone": timezone,
    }
    df = _extract_hourly_dataframe(response)
    return df, meta


def aggregate_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate hourly Open-Meteo data to daily summaries for dashboard/advisory."""
    daily = df.groupby("local_date").agg(
        temperature=("temperature_2m", "mean"),
        humidity=("relative_humidity_2m", "mean"),
        wind_speed=("wind_speed_10m", "mean"),
        rainfall=("rain", "sum"),
        showers=("showers", "sum"),
        soil_moisture_rootzone=("soil_moisture_9_to_27cm", "mean"),
        soil_moisture_surface=("soil_moisture_0_to_1cm", "mean"),
        soil_temp_0cm=("soil_temperature_0cm", "mean"),
    ).reset_index()

    daily.rename(columns={"local_date": "date"}, inplace=True)
    daily["rainfall"] = daily["rainfall"] + daily["showers"]
    daily["rainfall"] = daily["rainfall"].round(1)
    daily["temperature"] = daily["temperature"].round(1)
    daily["humidity"] = daily["humidity"].round(1)
    daily["wind_speed"] = daily["wind_speed"].round(1)
    # Open-Meteo soil moisture is m³/m³ (0–1) → convert to % for display
    daily["soil_moisture_pct"] = (daily["soil_moisture_rootzone"] * 100).round(1)
    return daily


def fetch_daily_weather(
    latitude: float,
    longitude: float,
    days: int = 7,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch daily weather list compatible with WeatherOut schema."""
    hourly_df, meta = fetch_hourly_forecast(latitude, longitude, forecast_days=days)
    daily_df = aggregate_daily(hourly_df).tail(days)
    records = []
    for _, row in daily_df.iterrows():
        d = row["date"]
        if isinstance(d, pd.Timestamp):
            d = d.date()
        records.append({
            "date": d,
            "rainfall": float(row["rainfall"]),
            "temperature": float(row["temperature"]),
            "humidity": float(row["humidity"]),
            "wind_speed": float(row["wind_speed"]),
            "source": "open-meteo",
            "soil_moisture_pct": float(row["soil_moisture_pct"]),
        })
    return records, meta


def get_weather_context_for_parcel(
    latitude: float,
    longitude: float,
) -> Optional[dict[str, Any]]:
    """
    Build weather context for advisory engine from Open-Meteo.
    Cached 30 min per location for fast voice responses.
    """
    key = (round(latitude, 4), round(longitude, 4))
    now = time.time()
    cached = _WEATHER_CTX_CACHE.get(key)
    if cached and (now - cached[0]) < WEATHER_CACHE_SECONDS:
        return cached[1]

    try:
        hourly_df, meta = fetch_hourly_forecast(latitude, longitude, forecast_days=7)
        daily_df = aggregate_daily(hourly_df)
        today = date.today()
        today_rows = daily_df[daily_df["date"] == today]
        tomorrow_rows = daily_df[daily_df["date"] == today + timedelta(days=1)]

        past_7d = daily_df[
            (daily_df["date"] <= today) & (daily_df["date"] >= today - timedelta(days=7))
        ]
        recent_rainfall = float(past_7d["rainfall"].sum()) if len(past_7d) else 0.0

        today_row = today_rows.iloc[-1] if len(today_rows) else daily_df.iloc[-1]
        forecast_row = tomorrow_rows.iloc[0] if len(tomorrow_rows) else None

        class WeatherRow:
            def __init__(self, rainfall, temperature, humidity, wind_speed, d):
                self.rainfall = rainfall
                self.temperature = temperature
                self.humidity = humidity
                self.wind_speed = wind_speed
                self.date = d

        openmeteo_soil_pct = float(today_row["soil_moisture_pct"])

        today_hourly = hourly_df[hourly_df["local_date"] == today]
        max_gust = float(today_hourly["wind_gusts_10m"].max()) if len(today_hourly) and "wind_gusts_10m" in today_hourly else float(today_row["wind_speed"])
        max_wind = float(today_hourly["wind_speed_10m"].max()) if len(today_hourly) else float(today_row["wind_speed"])

        result = {
            "weather_today": WeatherRow(
                float(today_row["rainfall"]),
                float(today_row["temperature"]),
                float(today_row["humidity"]),
                max_wind,
                today,
            ),
            "weather_forecast_tomorrow": WeatherRow(
                float(forecast_row["rainfall"]) if forecast_row is not None else 0.0,
                float(forecast_row["temperature"]) if forecast_row is not None else float(today_row["temperature"]),
                float(forecast_row["humidity"]) if forecast_row is not None else float(today_row["humidity"]),
                float(forecast_row["wind_speed"]) if forecast_row is not None else float(today_row["wind_speed"]),
                today + timedelta(days=1),
            ) if forecast_row is not None else None,
            "recent_rainfall_7d": recent_rainfall,
            "forecast_rainfall_mm": float(forecast_row["rainfall"]) if forecast_row is not None else 0.0,
            "openmeteo_soil_moisture_pct": openmeteo_soil_pct,
            "max_wind_kmh": max_wind,
            "max_wind_gust_kmh": max_gust,
            "weather_source": "open-meteo",
            "weather_meta": meta,
            "hourly_available": True,
        }
        _WEATHER_CTX_CACHE[key] = (now, result)
        return result
    except Exception as exc:
        logger.warning("Open-Meteo fetch failed: %s", exc)
        return None


def enrich_context_with_openmeteo(context: dict[str, Any]) -> dict[str, Any]:
    """Merge Open-Meteo live weather into parcel context; CSV/DB remains fallback."""
    settings = get_settings()
    if not settings.use_openmeteo:
        return context

    parcel = context.get("parcel")
    if not parcel:
        return context

    lat = float(getattr(parcel, "latitude", None) or parcel.get("latitude"))
    lon = float(getattr(parcel, "longitude", None) or parcel.get("longitude"))

    om = get_weather_context_for_parcel(lat, lon)
    if not om:
        context["weather_source"] = "synthetic_fallback"
        return context

    context.update(om)
    # Prefer field irrigation moisture; use Open-Meteo root-zone if field data missing
    if context.get("soil_moisture") is None and om.get("openmeteo_soil_moisture_pct") is not None:
        context["soil_moisture"] = om["openmeteo_soil_moisture_pct"]
        context["soil_moisture_source"] = "open-meteo"

    return context


def fetch_archive_daily(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch historical daily weather from Open-Meteo Archive API (actual recorded data)."""
    client = _get_client()
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": ARCHIVE_DAILY_VARS,
        "timezone": "Asia/Kolkata",
    }
    try:
        responses = client.weather_api(ARCHIVE_URL, params=params)
        response = responses[0]
        daily = response.Daily()
        dates = pd.date_range(
            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=daily.Interval()),
            inclusive="left",
        )
        var_names = ARCHIVE_DAILY_VARS
        arrays = [daily.Variables(i).ValuesAsNumpy() for i in range(len(var_names))]
        records = []
        for i, dt in enumerate(dates):
            d = dt.date()
            records.append({
                "date": d,
                "rainfall_mm": round(float(arrays[3][i]), 1),
                "temp_mean_c": round(float(arrays[0][i]), 1),
                "temp_max_c": round(float(arrays[1][i]), 1),
                "temp_min_c": round(float(arrays[2][i]), 1),
                "wind_max_kmh": round(float(arrays[6][i]), 1),
                "wind_gust_max_kmh": round(float(arrays[7][i]), 1),
                "humidity_pct": round(float(arrays[8][i]), 1),
                "et0_mm": round(float(arrays[9][i]), 2),
                "source": "open-meteo-archive",
            })
        meta = {
            "source": "open-meteo-archive",
            "latitude": response.Latitude(),
            "longitude": response.Longitude(),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": len(records),
        }
        return records, meta
    except Exception as exc:
        logger.warning("Open-Meteo archive fetch failed: %s", exc)
        return [], {"source": "open-meteo-archive", "error": str(exc)}


def fetch_forecast_daily_extended(latitude: float, longitude: float, days: int = 14) -> list[dict[str, Any]]:
    records, _ = fetch_daily_weather(latitude, longitude, days=min(days, 16))
    return records


def summarize_weather_period(latitude: float, longitude: float, period: str = "weekly") -> dict[str, Any]:
    """Aggregate actual weather for weekly (7d), monthly (30d), yearly (365d) from Open-Meteo Archive."""
    today = date.today()
    period_days = {"weekly": 7, "monthly": 30, "yearly": 365, "daily": 1}.get(period, 7)
    start = today - timedelta(days=period_days - 1)

    daily, meta = fetch_archive_daily(latitude, longitude, start, today)
    if not daily:
        return {"period": period, "source": "open-meteo-archive", "error": "no_data", "days": 0}

    total_rain = sum(d["rainfall_mm"] for d in daily)
    rain_days = sum(1 for d in daily if d["rainfall_mm"] >= 1.0)
    heavy_rain_days = sum(1 for d in daily if d["rainfall_mm"] >= 20.0)

    forecast_next = fetch_forecast_daily_extended(latitude, longitude, days=7) if period == "weekly" else []
    forecast_rain = sum(r.get("rainfall", 0) for r in forecast_next[:7])

    return {
        "period": period,
        "period_days": period_days,
        "start_date": start.isoformat(),
        "end_date": today.isoformat(),
        "source": "open-meteo-archive",
        "meta": meta,
        "total_rainfall_mm": round(total_rain, 1),
        "rain_days": rain_days,
        "heavy_rain_days": heavy_rain_days,
        "avg_temperature_c": round(sum(d["temp_mean_c"] for d in daily) / len(daily), 1),
        "max_temperature_c": round(max(d["temp_max_c"] for d in daily), 1),
        "min_temperature_c": round(min(d["temp_min_c"] for d in daily), 1),
        "max_wind_kmh": round(max(d["wind_max_kmh"] for d in daily), 1),
        "max_wind_gust_kmh": round(max(d["wind_gust_max_kmh"] for d in daily), 1),
        "avg_humidity_pct": round(sum(d["humidity_pct"] for d in daily) / len(daily), 1),
        "total_evapotranspiration_mm": round(sum(d["et0_mm"] for d in daily), 1),
        "forecast_rain_next_7d_mm": round(forecast_rain, 1),
        "daily_records": daily[-14:],
        "forecast_records": forecast_next[:7],
    }
