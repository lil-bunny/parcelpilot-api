from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage

from app.core.logger import get_logger
from app.domain.evidence import resolve_evidence
from app.integrations.llm.client import get_chat_model
from app.services.operational_data import OperationalError, query
from app.tools.trace import tool_trace_since_last_user_message
from app.workflows.compiler.compiler import compile_orchestrator

logger = get_logger(__name__)

_graph = None

_POLICY_TOOLS = frozenset({"get_applicable_rules", "get_account_policy"})


def get_graph(model=None):
    global _graph
    if model is not None:
        return compile_orchestrator(model)
    if _graph is None:
        _graph = compile_orchestrator(get_chat_model())
    return _graph


def reset_graph() -> None:
    global _graph
    _graph = None


@dataclass
class ChatResult:
    text: str
    tool_trace: list[dict[str, Any]]
    confirmation_required: bool = False
    proposed_action: dict | None = None
    evidence: list = field(default_factory=list)
    sources: list = field(default_factory=list)
    conflicts: list = field(default_factory=list)
    confidence: float | None = None


def _text_of(message) -> str:
    content = getattr(message, "content", "") or ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block) for block in content
        )
    return str(content)


def _ingest_policy_payload(payload: dict, structured: list, documents: list) -> None:
    if payload.get("error"):
        return
    if payload.get("account"):
        structured.append(payload["account"])
    if payload.get("order"):
        structured.append(payload["order"])
    documents.extend(payload.get("agreement_evidence") or [])
    documents.extend(payload.get("policy_evidence") or [])


def _collect_evidence(
    trace: list[dict[str, Any]],
    auth_account_id: str | None = None,
) -> tuple[list, list, list, float | None]:
    import json

    structured: list[dict] = []
    documents: list[dict] = []
    for row in trace:
        if not row.get("ok") or not row.get("result"):
            continue
        raw = row["result"]
        name = row.get("name")
        if name in _POLICY_TOOLS:
            try:
                payload = json.loads(raw)
                _ingest_policy_payload(payload, structured, documents)
            except (json.JSONDecodeError, TypeError):
                pass
        elif name == "search_documents":
            try:
                payload = json.loads(raw)
                if not payload.get("error"):
                    documents.extend(payload.get("evidence") or [])
            except (json.JSONDecodeError, TypeError):
                pass
        elif name == "query_operational_data":
            try:
                payload = json.loads(raw)
                if payload.get("found") and payload.get("data"):
                    data = payload["data"]
                    if isinstance(data, list):
                        structured.extend(d for d in data if isinstance(d, dict))
                    elif isinstance(data, dict):
                        structured.append(data)
            except (json.JSONDecodeError, TypeError):
                pass
    resolved = resolve_evidence(structured, documents, auth_account_id=auth_account_id)
    sources = [
        {
            "document_name": d.get("document_name"),
            "page": d.get("page"),
            "status": d.get("status"),
        }
        for d in resolved["evidence"]
    ]
    return resolved["evidence"], sources, resolved["conflicts"], None


def _enrich_user_context(user_context: dict | None) -> dict:
    ctx = dict(user_context or {"role": "customer", "account_id": "ACCT-001"})
    if ctx.get("role") == "customer" and ctx.get("account_id") and not ctx.get("account_name"):
        try:
            row = query("account", {}, ctx)
            if row and row.get("account_name"):
                ctx["account_name"] = row["account_name"]
        except OperationalError:
            pass
    return ctx


class OrchestratorService:
    def chat(
        self,
        thread_id: str,
        text: str,
        model=None,
        user_context: dict | None = None,
    ) -> ChatResult:
        graph = get_graph(model)
        ctx = _enrich_user_context(user_context)
        result = graph.invoke(
            {
                "messages": [{"role": "user", "content": text}],
                "user_context": ctx,
            },
            config={"configurable": {"thread_id": thread_id}},
        )
        messages = result["messages"]
        last = messages[-1]
        text_out = _text_of(last) if isinstance(last, AIMessage) else str(last.content)
        trace = tool_trace_since_last_user_message(messages)
        logger.info("chat done thread=%s tools=%s", thread_id, [t["name"] for t in trace])
        auth_account = ctx.get("account_id") if ctx.get("role") == "customer" else None
        evidence, sources, conflicts, confidence = _collect_evidence(trace, auth_account)
        return ChatResult(
            text=text_out,
            tool_trace=trace,
            confirmation_required=bool(result.get("confirmation_required")),
            proposed_action=result.get("proposed_action"),
            evidence=evidence,
            sources=sources,
            conflicts=conflicts,
            confidence=confidence,
        )
