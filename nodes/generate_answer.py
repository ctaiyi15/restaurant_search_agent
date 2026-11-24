import json

from schemas import AgentState
from .parse_query import client, model


GENERATE_INSTRUCTIONS = """
Answer the user's restaurant request concisely in the user's language.
Use only the supplied evidence. Explain unmet requirements, missing facts,
conflicts, and remaining limitations. Do not invent information.
If the tool budget limit was reached, clearly state what could not be verified.
Do not request more tools.
Use the latest filter_result and sort_result; earlier tool results may be stale.
Follow sort_result order. Do not recommend rejected/unknown candidates as meeting
all requirements. Explain missing fields and any uncompleted filtering or sorting.
For comparison/info requests, retain named targets and explain their check results.
Distances are straight-line, not walking/driving distances. Price levels are not
exact per-person prices. Semantic requirements still need supporting evidence.
"""


def generate_answer(state: AgentState) -> AgentState:
    """Integrate the evidence and assessment into the final answer, without tools."""
    check = state["constraint_check"]
    if check.status != "passed":
        return {"final_answer": "\n".join(check.questions or check.issues)
                or "Please clarify the restaurant request."}

    response = client.responses.create(
        model=model,
        instructions=GENERATE_INSTRUCTIONS,
        input=json.dumps({
            "messages": state["messages"],
            "parsed_query": state["parsed_query"].model_dump(),
            "tool_history": [item.model_dump() for item in state["tool_history"]],
            "assessment": state["assessment"].model_dump(),
            "tool_budget_exhausted": state["tool_budget_exhausted"],
            "filter_result": state.get("filter_result"),
            "sort_result": state.get("sort_result"),
        }, ensure_ascii=False),
        tools=[],
        tool_choice="none",
        store=False,
        reasoning={"effort": "low"},
    )
    if response.status != "completed" or not response.output_text.strip():
        raise ValueError("The model did not produce a complete answer.")
    return {"final_answer": response.output_text.strip()}
