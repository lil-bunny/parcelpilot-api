from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.orchestrator_service import OrchestratorService
from app.tools.registry import all_tools

router = APIRouter()


class UserContext(BaseModel):
    role: str = "customer"
    account_id: str = "ACCT-001"
    account_name: str | None = None


class ChatRequest(BaseModel):
    thread_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    user_context: UserContext = Field(default_factory=UserContext)


class ToolTraceItem(BaseModel):
    id: str
    name: str
    args: dict
    ok: bool
    result: str | None = None


class ChatResponse(BaseModel):
    text: str
    tool_trace: list[ToolTraceItem]
    confirmation_required: bool = False
    proposed_action: dict | None = None
    evidence: list = Field(default_factory=list)
    sources: list = Field(default_factory=list)
    conflicts: list = Field(default_factory=list)
    confidence: float | None = None


@router.get("/tools")
def list_tools():
    return {
        "tools": [
            {"name": t.name, "description": t.description}
            for t in all_tools()
        ]
    }


@router.post("/chat/messages", response_model=ChatResponse)
def post_chat(body: ChatRequest):
    if not settings.llm_api_key:
        raise HTTPException(
            status_code=503,
            detail="Set OPENAI_API_KEY in .env to run the orchestrator.",
        )
    result = OrchestratorService().chat(
        body.thread_id,
        body.text,
        user_context=body.user_context.model_dump(),
    )
    return ChatResponse(
        text=result.text,
        tool_trace=result.tool_trace,
        confirmation_required=result.confirmation_required,
        proposed_action=result.proposed_action,
        evidence=result.evidence,
        sources=result.sources,
        conflicts=result.conflicts,
        confidence=result.confidence,
    )
