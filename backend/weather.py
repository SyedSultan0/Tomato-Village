# ============================================================
# WEATHER LAYER
# ============================================================
#
# Open-Meteo integration with:
#   - in-process TTL cache (10 min) for repeated lat/lon hits
#   - explicit timeout
#   - deterministic fallback when the provider is unavailable
#     (e.g. rate-limited from shared-IP cloud hosts)
#
# The fallback returns plausible values so the risk engine
# still runs. It is used only when the live fetch fails.
# ============================================================

import os
import time
from datetime import datetime

import httpx


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

REQUEST_TIMEOUT_SECONDS = 10.0

CACHE_TTL_SECONDS = 600  # 10 minutes

WEATHER_FALLBACK_ENABLED = os.getenv(
    "WEATHER_FALLBACK_ENABLED", "true"
).strip().lower() in ("1", "true", "yes", "on")


_WEATHER_CACHE: dict[tuple[float, float], tuple[float, dict]] = {}


# ============================================================
# FALLBACK
# ============================================================
#
# Returns a realistic Open-Meteo-shaped response so the
# downstream risk engine has something to work with.
#
# Values are chosen to be "neutral" — mid-range temperature,
# moderate humidity, no rain — so the risk score doesn't
# artificially spike. Adjust if needed.
# ============================================================

def _fallback_weather(latitude: float, longitude: float) -> dict:
    now = datetime.utcnow().replace(microsecond=0).isoformat()

    # 24 hours of neutral hourly data
    hours = [now] * 24

    return {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "UTC",
        "current": {
            "time": now,
            "temperature_2m": 25.0,
            "relative_humidity_2m": 70.0,
            "dew_point_2m": 19.0,
            "precipitation": 0.0,
            "weather_code": 1,
            "cloud_cover": 40.0,
            "wind_speed_10m": 8.0,
            "wind_gusts_10m": 12.0,
            "shortwave_radiation": 200.0,
            "et0_fao_evapotranspiration": 3.0,
            "vapour_pressure_deficit": 1.0,
        },
        "hourly": {
            "time": hours,
            "temperature_2m": [25.0] * 24,
            "relative_humidity_2m": [70.0] * 24,
            "dew_point_2m": [19.0] * 24,
            "precipitation": [0.0] * 24,
            "precipitation_probability": [10.0] * 24,
            "cloud_cover": [40.0] * 24,
            "wind_speed_10m": [8.0] * 24,
            "soil_temperature_0cm": [24.0] * 24,
            "soil_temperature_6cm": [22.0] * 24,
            "soil_moisture_0_to_1cm": [0.25] * 24,
            "soil_moisture_1_to_3cm": [0.25] * 24,
            "soil_moisture_3_to_9cm": [0.25] * 24,
            "vapour_pressure_deficit": [1.0] * 24,
            "et0_fao_evapotranspiration": [3.0] * 24,
        },
    }


# ============================================================
# PUBLIC
# ============================================================

def get_weather(latitude: float, longitude: float) -> dict:
    """
    Fetch current + nearest-hour weather from Open-Meteo.

    Falls back to a deterministic snapshot if the provider
    is unreachable or rate-limiting.
    """

    cache_key = (
        round(float(latitude), 4),
        round(float(longitude), 4),
    )

    now = time.monotonic()

    cached = _WEATHER_CACHE.get(cache_key)

    if cached is not None:
        cached_at, cached_value = cached
        if (now - cached_at) < CACHE_TTL_SECONDS:
            return cached_value

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "dew_point_2m,"
            "precipitation,"
            "weather_code,"
            "cloud_cover,"
            "wind_speed_10m,"
            "wind_gusts_10m,"
            "shortwave_radiation,"
            "et0_fao_evapotranspiration,"
            "vapour_pressure_deficit"
        ),
        "hourly": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "dew_point_2m,"
            "precipitation,"
            "precipitation_probability,"
            "cloud_cover,"
            "wind_speed_10m,"
            "soil_temperature_0cm,"
            "soil_temperature_6cm,"
            "soil_moisture_0_to_1cm,"
            "soil_moisture_1_to_3cm,"
            "soil_moisture_3_to_9cm,"
            "vapour_pressure_deficit,"
            "et0_fao_evapotranspiration"
        ),
        "timezone": "auto",
        "forecast_days": 1,
    }

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = client.get(OPEN_METEO_URL, params=params)
            response.raise_for_status()
            data = response.json()

        _WEATHER_CACHE[cache_key] = (now, data)
        return data

    except Exception as e:
        print(f"[weather] Live fetch failed ({e}); using fallback")

        if not WEATHER_FALLBACK_ENABLED:
            raise

        fallback = _fallback_weather(latitude, longitude)
        _WEATHER_CACHE[cache_key] = (now, fallback)
        return fallback


def clear_weather_cache() -> None:
    _WEATHER_CACHE.clear()