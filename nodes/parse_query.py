import os
from openai import OpenAI
from dotenv import load_dotenv

from schemas import AgentState, ParsedQuery

load_dotenv()
model = os.getenv("LLM_MODEL_ID")
model_key = os.getenv("LLM_API_KEY")
DEFAULT_LOCATION = os.getenv("DEFAULT_LOCATION")

PARSE_INSTRUCTIONS = """
Extract restaurant requirements from the user's request.

Choose an intent:
- recommendation: recommend restaurants for the user's needs.
- restaurant_search: find restaurants by name, cuisine, or location.
- dish_search: find restaurants serving a requested dish.
- comparison: compare restaurants.
- info_check: check facts about a restaurant, such as its menu, address, or hours.
- out_of_scope: no restaurant discovery, comparison, or information request.

Rules:
- Extract only information stated by the user. Do not assume anything.
- Use null for unspecified scalar fields and empty lists for unspecified list fields.
- Distinguish hard constraints and soft preferences.
- Extract the requested sorting criterion. If none is specified, use "relevance".
- Keep conflicting requirements instead of resolving or dropping them.
- Do not search for restaurants or recommend any restaurants.
- Write extracted descriptions in English.
- For out_of_scope, leave search targets and constraints unspecified, lists empty. Do not search or answer the unrelated request.

"""
client = OpenAI(api_key=model_key, timeout=60.0, max_retries=0)

def parse_query(state: AgentState) -> AgentState:
    messages = state.get("messages", [])
    if not messages or not messages[-1].strip():
        raise ValueError("User request not found.")

    query = messages[-1].strip()

    response = client.responses.parse(
        model=model,
        instructions=PARSE_INSTRUCTIONS,
        input=query,
        text_format=ParsedQuery,
        store=False,
        reasoning={"effort": "low"}
    )

    if response.status != "completed" or response.output_parsed is None:
        raise ValueError("Could not parse the user request.")

    return {
        "parsed_query": response.output_parsed,
    }

