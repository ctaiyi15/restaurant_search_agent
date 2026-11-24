import json

from schemas import AgentState, ToolCallResult
from tools.function_tools import execute_tool


def execute_tools(state: AgentState) -> AgentState:
    calls = state["pending_tool_calls"]
    history = list(state.get("tool_history", []))
    inputs = list(state["model_input"])
    candidates = {place["id"]: place for place in state.get("candidates", [])}
    updates = {}

    for call in calls:
        try:
            arguments = json.loads(call["arguments"])
            if not isinstance(arguments, dict):
                raise ValueError("Tool arguments must be a JSON object.")
        except ValueError:
            arguments = {}
            result = {"error": "Tool arguments must be a valid JSON object."}
        else:
            # Each call uses the data available before this batch.
            result = execute_tool(call["name"], arguments, state=state)

        failed = isinstance(result, dict) and "error" in result
        if not failed:
            if call["name"] == "search_places":
                for place in result:
                    candidates[place["id"]] = {**candidates.get(place["id"], {}), **place}
            elif call["name"] == "geocode_location":
                if arguments["location"].strip() == (state["parsed_query"].location or "").strip():
                    updates["origin"] = result
            elif call["name"] == "filter_places":
                updates.update(filter_result=result, sort_result=None)
            elif call["name"] == "sort_places":
                updates["sort_result"] = result

        # web_search returns text; other tools return JSON data.
        output = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
        history.append(ToolCallResult(
            call_id=call["call_id"],
            tool=call["name"],
            arguments=arguments,
            output=output,
            status="error" if failed else "success",
        ))
        inputs.append({
            "type": "function_call_output",
            "call_id": call["call_id"],
            "output": output,
        })

    places = list(candidates.values())
    if (places != state.get("candidates", [])
            or updates.get("origin", state.get("origin")) != state.get("origin")):
        updates.update(filter_result=None, sort_result=None)

    return {
        **updates,
        "candidates": places,
        "model_input": inputs,
        "tool_history": history,
        "pending_tool_calls": [],
        "tool_budget_exhausted": len(history) >= state["max_tool_calls"],
    }
