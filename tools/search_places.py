import math
import os
import requests
from schemas import ParsedQuery


FEATURE_FIELDS = {
    "outdoor_seating": "outdoorSeating",
    "takeout": "takeout",
    "delivery": "delivery",
    "dine_in": "dineIn",
    "reservable": "reservable",
    "serves_vegetarian_food": "servesVegetarianFood",
    "serves_breakfast": "servesBreakfast",
    "serves_brunch": "servesBrunch",
    "serves_lunch": "servesLunch",
    "serves_dinner": "servesDinner",
    "good_for_children": "goodForChildren",
    "good_for_groups": "goodForGroups",
}


def search_places(parsed: ParsedQuery, center: tuple[float, float] | None = None) -> list[dict]:

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is not configured.")

    names = list(dict.fromkeys(name.strip() for name in parsed.restaurant_names if name.strip()))

    queries = []

    for name in names or [None]:
        parts = [
            name or "restaurants",
            parsed.cuisine,
            parsed.dish,
        ]

        query = " ".join(
            part.strip() for part in parts
            if part and part.strip()
        )

        # Use coordinates when available; otherwise use the location text.
        if center is None and parsed.location:
            query += f" in {parsed.location.strip()}"

        queries.append(query)

    fields = [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.rating",
        "places.userRatingCount",
        "places.priceLevel",
        "places.currentOpeningHours",
        "places.websiteUri",
        "places.googleMapsUri",
        "places.attributions",
    ]

    for feature in parsed.features:
        fields.append(f"places.{FEATURE_FIELDS[feature]}")

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": ",".join(fields),
    }

    body = {
        "pageSize": 10,
        "languageCode": "en",
    }

    if parsed.min_rating is not None:
        body["minRating"] = math.floor(parsed.min_rating * 2) / 2

    if parsed.price_levels:
        body["priceLevels"] = parsed.price_levels

    if parsed.open_now is not None:
        body["openNow"] = parsed.open_now

    if parsed.sort_by in {"relevance", "distance"}:
        body["rankPreference"] = parsed.sort_by.upper()

    if center is not None:
        latitude, longitude = center

        if not (
            math.isfinite(latitude)
            and math.isfinite(longitude)
            and -90 <= latitude <= 90
            and -180 <= longitude <= 180
        ):
            raise ValueError("Invalid search coordinates.")

        radius_m = (
            parsed.max_distance_km * 1000
            if parsed.max_distance_km is not None
            else 3000.0
        )

        if not math.isfinite(radius_m) or not 0 < radius_m <= 50000:
            raise ValueError(
                "The search bias radius must be between 0 and 50 km."
            )

        body["locationBias"] = {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude,
                },
                "radius": radius_m,
            }
        }

    places_by_id = {}

    for query in queries:
        response = requests.post(
            "https://places.googleapis.com/v1/places:searchText",
            headers=headers,
            json={**body, "textQuery": query},
            timeout=20,
        )
        response.raise_for_status()

        for place in response.json().get("places", []):
            places_by_id[place["id"]] = place

    return list(places_by_id.values())
