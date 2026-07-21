from pydantic import BaseModel, Field
from typing import Any, Optional
from enum import Enum


class IntentType(str, Enum):
    DEPLOY = "deploy"
    STATUS = "status"
    RESTART = "restart"
    LOGS = "logs"
    ROLLBACK = "rollback"
    UNKNOWN = "unknown"


class AgentRequest(BaseModel):
    command: str = Field(..., description="Natural language DevOps command")
    session_id: Optional[str] = None
    context: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    tool_name: str
    success: bool
    data: Any
    error: Optional[str] = None


class AgentResponse(BaseModel):
    session_id: str
    intent: IntentType
    summary: str
    steps: list[ToolResult] = []
    success: bool
    raw_output: Optional[str] = None
