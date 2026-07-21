from typing import Annotated, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from app.core.models import IntentType, ToolResult


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    intent: IntentType
    session_id: str
    tool_results: list[ToolResult]
    final_summary: str
    success: bool
    context: dict[str, Any]
