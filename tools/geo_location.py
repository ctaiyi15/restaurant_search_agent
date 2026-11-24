import os
import requests


def geocode_location(location: str) -> dict:

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is not configured.")

    if not location or not location.strip():
        raise ValueError("A location is required.")

    response = requests.get(
        "https://maps.googleapis.com/maps/api/geocode/json",
        params={
            "address": location.strip(),
            "key": api_key,
            "language": "en",
        },
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()
    status = data.get("status")

    if status == "ZERO_RESULTS":
        raise ValueError("No matching location was found.")

    if status != "OK":
        raise RuntimeError(f"Geocoding failed: {status}.")

    results = data.get("results", [])

    if not results:
        raise ValueError("No matching location was found.")

    if len(results) > 1 or results[0].get("partial_match"):
        raise ValueError(
            "The location is ambiguous. Provide a more specific address."
        )

    result = results[0]
    geometry = result["geometry"]
    coordinates = geometry["location"]

    return {
        "latitude": coordinates["lat"],
        "longitude": coordinates["lng"],
        "formatted_address": result["formatted_address"],
        "location_type": geometry["location_type"],
    }
