from langchain_core.tools import tool


@tool
def ping() -> str:
    """Health check for the tool loop. Returns ok. Use when asked if tools work."""
    return "ok"
