from schemas import AgentState, ConstraintCheck
from .parse_query import DEFAULT_LOCATION


def check_constraints(state: AgentState) -> AgentState:

    parsed = state.get("parsed_query")

    if parsed is None:
        return {
            "constraint_check": ConstraintCheck(
                status="invalid",
                issues=["The parsed query is missing."],
            )
        }

    if parsed.intent is None:
        return {
            "constraint_check": ConstraintCheck(
                            status="invalid",
                            issues=["The user intent is missing."],
                        )
        }

    if parsed.intent == "out_of_scope":
        return {
            "constraint_check": ConstraintCheck(
                status="invalid",
                issues=["Only restaurant query please."],
            )
        }

    issues: list[str] = []
    questions: list[str] = []

    if not parsed.location or not parsed.location.strip():
        parsed.location = DEFAULT_LOCATION

    if (parsed.intent in {"recommendation", "restaurant_search", "dish_search"}
            and parsed.max_distance_km is None):
        parsed.max_distance_km = 3.0

    if parsed.intent == "dish_search":
        if not parsed.dish or not parsed.dish.strip():
            issues.append("The dish search has no dish name.")
            questions.append("Which dish are you looking for?")

    elif parsed.intent == "comparison":
        unique_names = {
            name.strip().casefold() for name in parsed.restaurant_names if name.strip()
        }

        if len(unique_names) < 2:
            issues.append("A named restaurant comparison requires at least two restaurants.")
            questions.append("What restaurants would you like to compare?")

    elif parsed.intent == "info_check":
        if not any(name.strip() for name in parsed.restaurant_names):
            issues.append("The information check has no restaurant name.")
            questions.append("Which restaurant would you like information about?")

    check = ConstraintCheck(
        status="needs_clarification" if issues else "passed",
        issues=issues,
        questions=questions,
    )

    return {
        "constraint_check": check,
        "parsed_query": parsed,
    }

