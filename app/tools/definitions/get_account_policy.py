from langchain_core.tools import tool
from typing_extensions import Annotated

from app.services.applicable_rules import fetch_account_policy_json
from langgraph.prebuilt import InjectedState


@tool
def get_account_policy(
    topic: str,
    state: Annotated[dict, InjectedState],
) -> str:
    """Customer SLA/support/cancellation policy WITHOUT an order id.

    Loads the authenticated account from Postgres, then retrieves ONLY that customer's
    agreement (via contract_file) plus the relevant global policy doc (support policy for
    SLA/P2, cancellation SOP for cancel/credit topics). Use instead of broad search_documents.
    """
    user_context = state.get("user_context") or {"role": "customer", "account_id": ""}
    return fetch_account_policy_json(topic, user_context)
