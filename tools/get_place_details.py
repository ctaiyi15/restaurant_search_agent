import os
from urllib.parse import quote

import requests


DEFAULT_FIELDS = [
    "id",
    "displayName",
    "formattedAddress",
    "location",
    "businessStatus",
    "rating",
    "userRatingCount",
    "priceLevel",
    "currentOpeningHours",
    "regularOpeningHours",
    "nationalPhoneNumber",
    "websiteUri",
    "googleMapsUri",
    "attributions",
]


def get_place_details(place_id: str, fields: list[str] | None = None) -> dict:

    if not place_id or not place_id.strip():
        raise ValueError("A place ID is required.")
    if fields is not None and not fields:
        raise ValueError("At least one field is required.")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is not configured.")

    response = requests.get(
        f"https://places.googleapis.com/v1/places/{quote(place_id.strip(), safe='')}",
        headers={
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": ",".join(DEFAULT_FIELDS if fields is None else fields),
        },
        params={"languageCode": "en"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()
