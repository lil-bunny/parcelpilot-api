from langchain_core.tools import tool
from typing_extensions import Annotated

from app.services.applicable_rules import fetch_applicable_rules_json
from langgraph.prebuilt import InjectedState


@tool
def get_applicable_rules(
    order_id: str,
    topic: str,
    state: Annotated[dict, InjectedState],
) -> str:
    """For order-specific questions (cancellation, fees, service credits, product issues).

    Looks up the order and account in PostgreSQL first, then retrieves ONLY that customer's
    agreement (via contract_file) plus the relevant current SOP/policy doc. Use this instead
    of broad search_documents when the question references a specific order.

    Returns order, account, agreement_evidence, policy_evidence, agreement_summary, and
    policy_summary — use these to explain standard policy vs customer agreement override
    in your reply.
    """
    user_context = state.get("user_context") or {"role": "customer", "account_id": ""}
    return fetch_applicable_rules_json(order_id, topic, user_context)
