from langchain_core.utils.function_calling import convert_to_openai_function
from openai import OpenAIError
from pydantic import BaseModel, ConfigDict, Field
from requests import RequestException
from typing import Literal

from schemas import AgentState, ParsedQuery
from .geo_location import geocode_location
from .search_places import search_places
from .web_search import web_search
from .filter_places import filter_places
from .sort_places import sort_places


class ToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GeocodeArguments(ToolArguments):
    location: str = Field(min_length=1)


class Coordinates(ToolArguments):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class SearchArguments(ToolArguments):
    parsed: ParsedQuery
    center: Coordinates | None = None


class WebSearchArguments(ToolArguments):
    query: str = Field(min_length=1)


class SortArguments(ToolArguments):
    sort_by: Literal["relevance", "rating", "review_count", "distance", "price"]


def remove_schema_defaults(schema):
    if isinstance(schema, dict):
        schema.pop("default", None)
        for value in schema.values():
            remove_schema_defaults(value)
    elif isinstance(schema, list):
        for value in schema:
            remove_schema_defaults(value)


TOOLS = [
    {
        "type": "function",
        **convert_to_openai_function(GeocodeArguments, strict=True),
        "name": "geocode_location",
        "description": "Resolve the search origin to coordinates. Use the exact parsed_query.location text to save it for distance checks.",
    },
    {
        "type": "function",
        **convert_to_openai_function(SearchArguments, strict=True),
        "name": "search_places",
        "description": (
            "Search Google Places for restaurants using structured requirements. "
            "Returns addresses, ratings, price levels, hours, website links and "
            "requested features. Use null for center to search by location text."
        ),
    },
    {
        "type": "function",
        **convert_to_openai_function(WebSearchArguments, strict=True),
        "name": "web_search",
        "description": "Search the web for menus, dishes and general information. Returns plain text.",
    },
    {
        "type": "function",
        "name": "filter_places",
        "strict": True,
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        "description": (
            "Check stored candidates against the original user's rating, review count, "
            "price, opening status, features and straight-line distance requirements. "
            "Returns matched, rejected and unknown candidates with reasons. "
            "Uses stored data; do not pass restaurant facts or change constraints."
        ),
    },
    {
        "type": "function",
        **convert_to_openai_function(SortArguments, strict=True),
        "name": "sort_places",
        "description": (
            "Sort the already filtered candidates. Rating/review_count descend; "
            "distance/price ascend; relevance preserves search order; missing values go last. "
            "Named comparison/info targets are retained even when constraints fail."
        ),
    },
]

for tool in TOOLS:
    remove_schema_defaults(tool["parameters"])


def available_tools(state: AgentState) -> list[dict]:
    ready = {"geocode_location", "search_places", "web_search"}
    if state.get("candidates") and state.get("filter_result") is None:
        ready.add("filter_places")
    if state.get("filter_result") is not None and state.get("sort_result") is None:
        ready.add("sort_places")
    return [tool for tool in TOOLS if tool["name"] in ready]


def execute_tool(name: str, arguments: dict, *, state: AgentState | None = None) -> dict | list | str:
    try:
        if name == "geocode_location":
            args = GeocodeArguments.model_validate(arguments)
            return geocode_location(args.location)

        if name == "search_places":
            args = SearchArguments.model_validate(arguments)
            if state is not None:
                original = state["parsed_query"]
                # Fetch the fields needed for later checks even if the model omits them.
                args.parsed.features = list(dict.fromkeys(args.parsed.features + original.features))
                if original.intent in {"comparison", "info_check"}:
                    args.parsed = args.parsed.model_copy(update={
                        "min_rating": None, "price_levels": [], "open_now": None,
                    })
            center = (
                (args.center.latitude, args.center.longitude)
                if args.center is not None else None
            )
            return search_places(args.parsed, center)

        if name == "web_search":
            args = WebSearchArguments.model_validate(arguments)
            return web_search(args.query)

        if name == "filter_places":
            ToolArguments.model_validate(arguments)
            return filter_places(state["candidates"], state["parsed_query"], state.get("origin"))

        if name == "sort_places":
            args = SortArguments.model_validate(arguments)
            original = state["parsed_query"]
            if original.sort_by != "relevance" and args.sort_by != original.sort_by:
                return {"error": f"Use the user's requested sort_by: {original.sort_by}."}
            filtered = state["filter_result"]
            places = filtered["matched"]
            if original.intent in {"comparison", "info_check"}:
                # Keep original search order for relevance, including nonmatching targets.
                checked = {p["id"]: p for p in places}
                for group in ("rejected", "unknown"):
                    checked.update({item["place"]["id"]: item["place"] for item in filtered[group]})
                places = [checked[p["id"]] for p in state["candidates"]]
            return sort_places(places, args.sort_by)

        return {"error": "Unknown tool."}
    except (RequestException, OpenAIError) as exc:
        return {"error": f"{name} failed: {type(exc).__name__}."}
    except (ValueError, RuntimeError) as exc:
        return {"error": str(exc)}
