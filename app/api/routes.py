from fastapi import APIRouter, HTTPException
from app.core.models import AgentRequest, AgentResponse
from app.agent.workflow import run_agent
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/agent", tags=["agent"])


import re

_SAFE_LOG_PATTERN = re.compile(r"[^\w\s\-.:/@]")


def _sanitize(value: str) -> str:
    """Strip characters that could break log integrity (log injection prevention)."""
    return _SAFE_LOG_PATTERN.sub("_", value)


@router.post("/run", response_model=AgentResponse)
async def run_command(request: AgentRequest):
    """Accept a natural language DevOps command and execute it via the AI agent."""
    logger.info(
        "Received command: %s | session: %s",
        _sanitize(request.command[:200]),
        _sanitize(str(request.session_id or "")),
    )
    try:
        result = await run_agent(
            command=request.command,
            session_id=request.session_id,
            context=request.context,
        )
        return AgentResponse(**result)
    except Exception as e:
        logger.exception("Agent execution failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health():
    return {"status": "ok"}
