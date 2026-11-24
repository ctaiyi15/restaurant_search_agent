import math
from schemas import ParsedQuery
from .search_places import FEATURE_FIELDS


def distance_km(location: dict | None, origin: dict | None) -> float | None:
    if not location or not origin:
        return None
    coordinates = [origin.get("latitude"), origin.get("longitude"), location.get("latitude"), location.get("longitude")]
    if any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in coordinates):
        return None
    lat1, lon1, lat2, lon2 = map(math.radians, coordinates)
    a = (math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 6371.0088 * 2 * math.asin(math.sqrt(min(1.0, max(0.0, a))))


def filter_places(
    places: list[dict], requirements: ParsedQuery, origin: dict | None = None,
) -> dict:
    result = {"matched": [], "rejected": [], "unknown": []}
    for candidate in places:
        place = {**candidate, "distance_km": distance_km(candidate.get("location"), origin)}
        failed, missing = [], []

        def check(field, value, passes, requirement):
            if value is None:
                missing.append(f"{field}: missing; required {requirement}")
            elif not passes(value):
                failed.append(f"{field}: {value}; required {requirement}")

        if requirements.min_rating is not None:
            check("rating", place.get("rating"),
                  lambda value: value >= requirements.min_rating,
                  f">= {requirements.min_rating}")
        if requirements.min_review_count is not None:
            check("userRatingCount", place.get("userRatingCount"),
                  lambda value: value >= requirements.min_review_count,
                  f">= {requirements.min_review_count}")
        if requirements.price_levels:
            level = place.get("priceLevel")
            if level == "PRICE_LEVEL_UNSPECIFIED":
                level = None
            check("priceLevel", level, lambda value: value in requirements.price_levels,
                  str(requirements.price_levels))
        if requirements.open_now is not None:
            check("openNow", (place.get("currentOpeningHours") or {}).get("openNow"),
                  lambda value: value is requirements.open_now, str(requirements.open_now))
        for feature in requirements.features:
            field = FEATURE_FIELDS[feature]
            check(field, place.get(field), lambda value: value is True, "True")
        if requirements.max_distance_km is not None:
            check("distance_km (straight-line)", place["distance_km"],
                  lambda value: value <= requirements.max_distance_km,
                  f"<= {requirements.max_distance_km}")

        if failed:
            result["rejected"].append({"place": place, "reasons": failed, "unknown": missing})
        elif missing:
            result["unknown"].append({"place": place, "reasons": missing})
        else:
            result["matched"].append(place)
    return result
