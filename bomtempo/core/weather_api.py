import unicodedata
from typing import Any, Dict, Optional

import httpx

from bomtempo.core.logging_utils import get_logger

logger = get_logger(__name__)

# Recife Coordinates
LAT = -8.05428
LON = -34.8813
TIMEZONE = "America/Sao_Paulo"


async def get_forecast(lat: float = LAT, lon: float = LON) -> Optional[Dict[str, Any]]:
    """
    Fetches weather data from Open-Meteo API.
    Returns structured data for widget or None if fails.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,precipitation,weather_code,wind_speed_10m",
        "daily": "precipitation_sum,precipitation_probability_max,temperature_2m_max,temperature_2m_min",
        "timezone": TIMEZONE,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=5.0)
            response.raise_for_status()
            data = response.json()

            # Process data for UI
            return {
                "temp": int(data["current"]["temperature_2m"]),
                "rain": data["current"]["precipitation"],
                "wind": data["current"]["wind_speed_10m"],
                "code": data["current"]["weather_code"],
                # Daily arrays
                "daily_time": data["daily"]["time"],  # ['2023-10-27', ...]
                "daily_rain_sum": data["daily"]["precipitation_sum"],
                "daily_rain_prob": data["daily"]["precipitation_probability_max"],
                "daily_max": data["daily"]["temperature_2m_max"],
                "daily_min": data["daily"]["temperature_2m_min"],
            }

    except Exception as e:
        logger.error(f"Weather API Error: {e}")
        return None


async def get_coordinates(city_name: str) -> Optional[Dict[str, Any]]:
    """
    Geocodes a city name to Lat/Lon using Open-Meteo Geocoding API.
    """
    url = "https://geocoding-api.open-meteo.com/v1/search"
    logger.info(f"Fetching coordinates for: {city_name}")

    params = {"count": 1, "language": "pt", "format": "json"}

    try:
        # 1. Split state code (e.g. "Recife, PE" -> "Recife")
        search_name = city_name.split(",")[0].strip() if "," in city_name else city_name

        # 2. Remove " - " if present
        search_name = search_name.split(" - ")[0].strip()

        # 3. Normalize accents (e.g. "São Paulo" -> "Sao Paulo")
        # This helps API matching significantly
        nfkd_form = unicodedata.normalize("NFKD", search_name)
        search_name = "".join([c for c in nfkd_form if not unicodedata.combining(c)])

        # 4. Specific Fixes for known bad data
        if "Joo Pessoa" in search_name or "Joo Pessoa" in city_name:
            search_name = "Joao Pessoa"

        logger.debug(f"Geocoding search: '{city_name}' -> '{search_name}'")

        params["name"] = search_name

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            if "results" in data and len(data["results"]) > 0:
                result = data["results"][0]
                return {
                    "lat": result["latitude"],
                    "lon": result["longitude"],
                    "name": f"{result['name']}, {result.get('admin1', '')}",
                }

            logger.warning(
                f"Geocoding API returned 0 results for '{search_name}' (original: '{city_name}')"
            )
            return None

    except Exception as e:
        logger.error(f"Geocoding API Error: {e}")
        return None


def get_risk_level(data: Dict[str, Any]) -> str:
    """Calculates risk level based on precipitation."""
    if not data:
        return "Unknown"

    today_rain = data.get("daily_rain_sum", [0])[0]
    today_prob = data.get("daily_rain_prob", [0])[0]
    current_rain = data.get("rain", 0)

    if current_rain > 5 or today_rain > 15 or today_prob > 80:
        return "High"
    if current_rain > 0.5 or today_rain > 5 or today_prob > 50:
        return "Medium"
    return "Low"
