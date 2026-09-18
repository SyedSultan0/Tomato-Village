# ============================================================
# WEATHER LAYER — M4.5
# ============================================================
#
# Single synchronous implementation using httpx.Client.
#
# What changed vs. previous version:
#   - async → sync (httpx.Client instead of httpx.AsyncClient)
#   - forecast_days: 2 → 1 (risk engine only reads the hourly
#     index closest to current.time, which with timezone=auto
#     is index 0)
#   - dropped rain and showers from both current and hourly
#     (neither is read anywhere in the codebase)
#   - added a 10-minute in-process TTL cache keyed by
#     (rounded lat, rounded lon)
#   - explicit request timeout reduced to 10s (was 20s)
#
# What was NOT changed:
#   - Every field read by risk_engine.extract_weather_values
#     is still requested, including wind_gusts_10m and
#     shortwave_radiation (which feed weather_snapshot).
#   - timezone: auto is preserved, since
#     risk_engine.find_relevant_hour_index depends on it.
# ============================================================

import time

import httpx


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

REQUEST_TIMEOUT_SECONDS = 10.0

CACHE_TTL_SECONDS = 600  # 10 minutes

_WEATHER_CACHE: dict[tuple[float, float], tuple[float, dict]] = {}


# ============================================================
# PUBLIC
# ============================================================

def get_weather(latitude: float, longitude: float) -> dict:
    """
    Fetch current + nearest-hour weather from Open-Meteo.

    Returns the raw JSON response dict.
    Cached for 10 minutes per (lat, lon) pair.
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

        # ----------------------------------------------------
        # current — fields read by risk_engine, main.py, or
        # advisory_engine environmental modifiers
        # ----------------------------------------------------
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

        # ----------------------------------------------------
        # hourly — every field read by
        # risk_engine.extract_weather_values
        # ----------------------------------------------------
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

    with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        response = client.get(OPEN_METEO_URL, params=params)
        response.raise_for_status()
        data = response.json()

    _WEATHER_CACHE[cache_key] = (now, data)

    return data


def clear_weather_cache() -> None:
    """Empty the weather cache. For tests and demo resets."""
    _WEATHER_CACHE.clear()