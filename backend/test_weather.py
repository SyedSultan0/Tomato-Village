import asyncio

from weather import get_weather


async def main():

    latitude = 19.076
    longitude = 72.8777

    weather = await get_weather(
        latitude,
        longitude
    )

    print("\n===== WEATHER TEST =====")

    print("Latitude:", weather["latitude"])
    print("Longitude:", weather["longitude"])

    print("\nCurrent weather:")
    print(weather["current"])

    print("\nHourly data available:")
    print(weather["hourly"].keys())


if __name__ == "__main__":
    asyncio.run(main())