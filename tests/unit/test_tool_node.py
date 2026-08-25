from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.domain.state import AgentState
from app.tools.definitions.calculate_service_credit import compute_credit
from app.tools.registry import TOOL_REGISTRY, all_tools


def test_echo_tool_runs():
    assert TOOL_REGISTRY["echo"].invoke({"text": "hi"}) == "hi"


def test_calculate_service_credit_customer_fault():
    result = compute_credit(
        {"delay_hours": 5, "carrier_fault": True, "customer_fault": True, "shipment_fee_inr": 100},
        ["Service credit after 2 hours of carrier delay."],
    )
    assert result["eligible"] is False


def test_calculate_service_credit_meets_threshold():
    result = compute_credit(
        {"delay_hours": 3, "carrier_fault": True, "customer_fault": False, "shipment_fee_inr": 1000},
        ["Credits apply after 2 hours delay at 10% of shipment fee."],
    )
    assert result["eligible"] is True
    assert result["credit_amount"] == 100.0


def test_tool_node_runs_echo_from_registry():
    """LangGraph ToolNode executes a registered @tool (Graph API, no LLM)."""
    workflow = StateGraph(AgentState)
    workflow.add_node("tools", ToolNode(all_tools()))
    workflow.add_edge(START, "tools")
    workflow.add_edge("tools", END)
    graph = workflow.compile()
    out = graph.invoke(
        {
            "messages": [
                HumanMessage(content="echo hi"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "echo",
                            "args": {"text": "hi"},
                            "id": "c1",
                            "type": "tool_call",
                        }
                    ],
                ),
            ]
        }
    )
    last = out["messages"][-1]
    assert last.content == "hi"
    assert last.tool_call_id == "c1"
