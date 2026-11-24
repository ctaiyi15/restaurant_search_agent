from typing import TypedDict, List, Literal
from pydantic import BaseModel, Field


PriceLevel = Literal[
    "PRICE_LEVEL_INEXPENSIVE",
    "PRICE_LEVEL_MODERATE",
    "PRICE_LEVEL_EXPENSIVE",
    "PRICE_LEVEL_VERY_EXPENSIVE"
]

RestaurantFeature = Literal[
    "outdoor_seating",
    "takeout",
    "delivery",
    "dine_in",
    "reservable",
    "serves_vegetarian_food",
    "serves_breakfast",
    "serves_brunch",
    "serves_lunch",
    "serves_dinner",
    "good_for_children",
    "good_for_groups"
]

ToolName = Literal[
    "search_places",
    "web_search",
    "geocode_location",
    "filter_places",
    "sort_places",
]

class ParsedQuery(BaseModel):

    intent: Literal[
        "recommendation",
        "restaurant_search",
        "dish_search",
        "comparison",
        "info_check",
        "out_of_scope"
    ]

    # Search targets
    location: str | None = None
    restaurant_names: list[str] = Field(default_factory=list)
    cuisine: str | None = None
    dish: str | None = None

    # Hard constraints
    min_rating: float | None = Field(default=None, ge=0, le=5)
    min_review_count: int | None = Field(default=None, ge=0)
    price_levels: list[PriceLevel] = Field(default_factory=list)
    open_now: bool | None = None
    max_distance_km: float | None = Field(default=None, gt=0)
    features: list[RestaurantFeature] = Field(default_factory=list)

    # Ranking and preferences
    sort_by: Literal[
        "relevance",
        "rating",
        "review_count",
        "distance",
        "price"
    ] = "relevance"

    preferences: list[str] = Field(default_factory=list)

class ConstraintCheck(BaseModel):
    status: Literal["passed", "needs_clarification", "invalid"]
    issues: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)

class ToolCallResult(BaseModel):
    call_id: str
    tool: str
    arguments: dict
    output: str
    status: Literal["success", "error"] = "success"


class Assessment(BaseModel):
    decision: Literal["generate", "replan"]
    confirmed: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    reason: str


class AgentState(TypedDict, total=False):
    messages: list[str]
    max_tool_calls: int
    current_task: str
    parsed_query: ParsedQuery
    constraint_check: ConstraintCheck
    model_input: list[dict]
    pending_tool_calls: list[dict]
    tool_history: list[ToolCallResult]
    candidates: list[dict]
    origin: dict
    filter_result: dict | None
    sort_result: dict | None
    tool_budget_exhausted: bool
    assessment: Assessment
    final_answer: str

