from langchain_core.language_models.chat_models import BaseChatModel

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.domain.state import AgentState
from app.tools.registry import all_tools
from app.workflows.graph.confirmation import (
    check_confirmation_node,
    execute_action_node,
    request_confirmation_node,
)
from app.workflows.graph.orchestrator import call_model
from app.workflows.graph.routers import after_check_confirmation, route_after_model


def compile_orchestrator(model: BaseChatModel):
    """check_confirmation → model ⇄ tools | request_confirmation → execute_action."""
    tools = all_tools()
    bound = model.bind_tools(tools)

    def model_node(state: AgentState):
        return call_model(state, bound)

    workflow = StateGraph(AgentState)
    workflow.add_node("check_confirmation", check_confirmation_node)
    workflow.add_node("model", model_node)
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("request_confirmation", request_confirmation_node)
    workflow.add_node("execute_action", execute_action_node)

    workflow.add_edge(START, "check_confirmation")
    workflow.add_conditional_edges("check_confirmation", after_check_confirmation)
    workflow.add_edge("execute_action", END)
    workflow.add_conditional_edges("model", route_after_model)
    workflow.add_edge("tools", "model")
    workflow.add_edge("request_confirmation", END)

    return workflow.compile(checkpointer=MemorySaver())
