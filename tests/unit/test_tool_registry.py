from langchain_core.tools import tool

from app.tools.registry import TOOL_REGISTRY, all_tools, register


def test_builtin_tools_are_registered():
    names = {t.name for t in all_tools()}
    assert names >= {
        "ping",
        "echo",
        "query_operational_data",
        "search_documents",
        "get_applicable_rules",
        "get_account_policy",
        "calculate_service_credit",
        "create_escalation",
    }
    assert "get_policy" not in names
    assert "lookup_order" not in names
    assert "calculate_fee" not in names
    assert TOOL_REGISTRY["ping"].name == "ping"
    assert TOOL_REGISTRY["echo"].name == "echo"


def test_register_adds_tool_to_registry():
    @tool
    def foo_probe() -> str:
        """Probe tool used only in this test."""
        return "foo"

    register(foo_probe)
    try:
        assert "foo_probe" in TOOL_REGISTRY
        assert any(t.name == "foo_probe" for t in all_tools())
    finally:
        TOOL_REGISTRY.pop("foo_probe", None)
