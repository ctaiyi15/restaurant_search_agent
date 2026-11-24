import os
from openai import OpenAI


SEARCH_INSTRUCTIONS = """
Search the web for information relevant to the query.
Prioritize official websites. Read relevant pages when needed.
Summarize information and cite their sources.
Clearly state when information is missing, uncertain, or conflicting.
Do not infer any information without evidence.
"""


def web_search(query: str) -> str:
    if not query or not query.strip():
        raise ValueError("A search query is required.")

    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL_ID")
    if not api_key or not model:
        raise ValueError("LLM_API_KEY and LLM_MODEL_ID must be configured.")

    with OpenAI(api_key=api_key, timeout=60.0, max_retries=0) as client:
        response = client.responses.create(
            model=model,
            instructions=SEARCH_INSTRUCTIONS,
            input=query.strip(),
            tools=[{"type": "web_search"}],
            tool_choice="required",
            store=False
        )

    if response.status != "completed" or not response.output_text.strip():
        raise ValueError("Web search did not produce an answer.")

    return response.output_text
