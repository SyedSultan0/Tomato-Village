import httpx


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


async def get_weather(latitude: float, longitude: float):

    params = {
        "latitude": latitude,
        "longitude": longitude,

        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "dew_point_2m,"
            "precipitation,"
            "rain,"
            "showers,"
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
            "precipitation_probability,"
            "precipitation,"
            "rain,"
            "showers,"
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
        "forecast_days": 2
    }

    async with httpx.AsyncClient(
        timeout=20.0
    ) as client:

        response = await client.get(
            OPEN_METEO_URL,
            params=params
        )

        response.raise_for_status()

        return response.json()