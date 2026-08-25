from langchain_core.tools import tool


@tool
def echo(text: str) -> str:
    """Echo the given text back. Use when the user asks to repeat or echo something."""
    return text
