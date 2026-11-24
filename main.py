import argparse
from pathlib import Path
from pprint import pformat

from langgraph.graph import END, START, StateGraph

from schemas import AgentState
from nodes import (
    assess, check_constraints, client, execute_tools, generate_answer,
    parse_query, plan_tools, replan,
)


MAX_TOOL_CALLS = 8
MAX_RECURSION = 30

def build_graph():
    def after_constraints(state: AgentState):
        return "plan_tools" if state["constraint_check"].status == "passed" else "generate_answer"

    def after_assess(state: AgentState):
        if state["tool_budget_exhausted"]:
            return "generate_answer"
        return "replan" if state["assessment"].decision == "replan" else "generate_answer"

    builder = StateGraph(AgentState)
    builder.add_node("parse_query", parse_query)
    builder.add_node("check_constraints", check_constraints)
    builder.add_node("plan_tools", plan_tools)
    builder.add_node("execute_tools", execute_tools)
    builder.add_node("assess", assess)
    builder.add_node("replan", replan)
    builder.add_node("generate_answer", generate_answer)

    builder.add_edge(START, "parse_query")
    builder.add_edge("parse_query", "check_constraints")
    builder.add_conditional_edges("check_constraints", after_constraints, {
        "plan_tools": "plan_tools", "generate_answer": "generate_answer",
    })
    builder.add_edge("plan_tools", "execute_tools")
    builder.add_edge("execute_tools", "assess")
    builder.add_conditional_edges("assess", after_assess, {
        "replan": "replan", "generate_answer": "generate_answer",
    })
    builder.add_edge("replan", "execute_tools")
    builder.add_edge("generate_answer", END)
    return builder.compile().with_config(recursion_limit= MAX_RECURSION)


def main():
    parser = argparse.ArgumentParser(description="Find restaurant information")
    parser.add_argument("query", nargs="?", help="Your restaurant request")
    args = parser.parse_args()
    query = args.query if args.query is not None else input("Restaurant request: ")
    if not query.strip():
        parser.error("Please enter a restaurant request.")

    initial_state = {
        "messages": [query.strip()],
        "max_tool_calls": MAX_TOOL_CALLS,
    }
    try:
        output_dir = Path(__file__).resolve().parent / "outputs"
        output_dir.mkdir(exist_ok=True)
        run_number = 1
        while True:
            run_dir = output_dir / f"run_{run_number:03d}"
            try:
                run_dir.mkdir()
                break
            except FileExistsError:
                run_number += 1

        with (
            (run_dir / "full.txt").open("w", encoding="utf-8") as full,
            (run_dir / "clean.txt").open("w", encoding="utf-8") as clean,
        ):
            full.write(f"Input query:\n{query.strip()}\n")
            clean.write(f"Input query:\n{query.strip()}\n\nNodes:\n")
            full.flush()
            clean.flush()
            step = 0

            for update in build_graph().stream(initial_state, stream_mode="updates"):
                for node, changes in update.items():
                    visible = {
                        key: value
                        for key, value in changes.items()
                        if key != "model_input"
                    }
                    full.write(f"\n===== {node} =====\n{pformat(visible, sort_dicts=False)}\n")
                    step += 1
                    clean.write(f"{step}. {node}\n")
                    if "final_answer" in changes:
                        clean.write(f"\nOutput:\n{changes['final_answer']}\n")
                    full.flush()
                    clean.flush()
    finally:
        client.close()


if __name__ == "__main__":
    main()

