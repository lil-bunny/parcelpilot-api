"""Register tools here. Add a tool = @tool file + register() — no new graph nodes."""



from langchain_core.tools import BaseTool



from app.tools.definitions.actions import create_escalation, create_followup, update_ticket

from app.tools.definitions.calculate_service_credit import calculate_service_credit

from app.tools.definitions.echo import echo

from app.tools.definitions.get_account_policy import get_account_policy

from app.tools.definitions.get_applicable_rules import get_applicable_rules

from app.tools.definitions.ping import ping

from app.tools.definitions.query_operational_data import query_operational_data

from app.tools.definitions.search_documents import search_documents



TOOL_REGISTRY: dict[str, BaseTool] = {}





def register(tool: BaseTool) -> None:

    TOOL_REGISTRY[tool.name] = tool





def all_tools() -> list[BaseTool]:

    return list(TOOL_REGISTRY.values())





def tool_names() -> list[str]:

    return [t.name for t in all_tools()]





register(ping)

register(echo)

register(query_operational_data)

register(search_documents)

register(get_applicable_rules)

register(get_account_policy)

register(calculate_service_credit)

register(create_escalation)

register(update_ticket)

register(create_followup)

