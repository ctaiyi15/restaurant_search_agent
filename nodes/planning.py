import json

from schemas import AgentState
from tools.function_tools import available_tools
from .parse_query import client, model


def plan_batch(
    state: AgentState, *, instructions: str,
    feedback: dict | None = None,
) -> AgentState:
    remaining = state["max_tool_calls"] - len(state.get("tool_history", []))
    inputs = list(state.get("model_input", []))
    if not inputs:
        inputs.append({
            "role": "user",
            "content": json.dumps({
                "messages": state["messages"],
                "parsed_query": state["parsed_query"].model_dump(),
            }, ensure_ascii=False),
        })
    inputs.append({
        "role": "user",
        "content": json.dumps({
            "remaining_tool_calls": remaining,
            "candidate_count": len(state.get("candidates", [])),
            "filter_completed": state.get("filter_result") is not None,
            "sort_completed": state.get("sort_result") is not None,
            **(feedback or {}),
        }, ensure_ascii=False),
    })

    response = client.responses.create(
        model=model,
        instructions=instructions,
        input=inputs,
        tools=available_tools(state),
        tool_choice="required",
        parallel_tool_calls=True,
        store=False,
        reasoning={"effort": "low"},
        include=["reasoning.encrypted_content"],
    )
    if response.status != "completed":
        raise ValueError("The planning response did not complete.")

    output = [item.model_dump(exclude_none=True) for item in response.output]
    calls = [item for item in output if item["type"] == "function_call"]
    if not calls:
        raise ValueError("The planner returned no tool calls.")

    calls = calls[:remaining]
    call_ids = {call["call_id"] for call in calls}
    output = [item for item in output
              if item["type"] != "function_call" or item["call_id"] in call_ids]
    return {"model_input": inputs + output, "pending_tool_calls": calls}
