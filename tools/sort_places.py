PRICE_ORDER = {
    "PRICE_LEVEL_FREE": 0,
    "PRICE_LEVEL_INEXPENSIVE": 1,
    "PRICE_LEVEL_MODERATE": 2,
    "PRICE_LEVEL_EXPENSIVE": 3,
    "PRICE_LEVEL_VERY_EXPENSIVE": 4,
}


def sort_places(places: list[dict], sort_by: str) -> dict:
    if sort_by == "relevance":
        return {"sort_by": sort_by, "places": list(places), "missing_values": []}

    fields = {"rating": "rating", "review_count": "userRatingCount",
              "distance": "distance_km", "price": "priceLevel"}
    field = fields[sort_by]

    def value(place):
        raw = place.get(field)
        return PRICE_ORDER.get(raw) if sort_by == "price" else raw

    known = [place for place in places if value(place) is not None]
    missing = [place for place in places if value(place) is None]
    if sort_by == "rating":
        known.sort(key=lambda place: (value(place), place.get("userRatingCount") or 0), reverse=True)
    else:
        known.sort(key=value, reverse=sort_by == "review_count")
    return {
        "sort_by": sort_by,
        "places": known + missing,
        "missing_values": [place["id"] for place in missing],
    }
