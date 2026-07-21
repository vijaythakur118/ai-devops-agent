"""
LangGraph DevOps Agent Workflow

Graph:  classify_intent → agent_reason → [tool_node] → summarize → END
                                ↑______________|  (loop until no tool calls)
"""
import uuid
import json
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from app.agent.state import AgentState
from app.mcp.tools import ALL_TOOLS
from app.core.config import get_settings
from app.core.models import IntentType, ToolResult
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """You are an expert DevOps AI Agent. You help users manage Kubernetes deployments,
CI/CD pipelines, and cloud infrastructure through natural language commands.

Available operations:
- Deploy services to Kubernetes namespaces (staging, production)
- Check deployment status and health
- Restart deployments
- Fetch application logs
- Rollback deployments to previous versions
- Check CI/CD pipeline status

Always extract: service name, environment/namespace, and any version/tag from the user command.
Use the appropriate MCP tool to fulfill the request. Be precise and concise in your responses."""

INTENT_MAP = {
    "deploy": IntentType.DEPLOY,
    "release": IntentType.DEPLOY,
    "status": IntentType.STATUS,
    "health": IntentType.STATUS,
    "restart": IntentType.RESTART,
    "bounce": IntentType.RESTART,
    "log": IntentType.LOGS,
    "rollback": IntentType.ROLLBACK,
    "revert": IntentType.ROLLBACK,
}


def _detect_intent(command: str) -> IntentType:
    lower = command.lower()
    for keyword, intent in INTENT_MAP.items():
        if keyword in lower:
            return intent
    return IntentType.UNKNOWN


def build_graph() -> StateGraph:
    llm = ChatOllama(model=settings.ollama_model, base_url=settings.ollama_base_url)
    llm_with_tools = llm.bind_tools(ALL_TOOLS)
    tool_node = ToolNode(ALL_TOOLS)

    def classify_intent(state: AgentState) -> AgentState:
        last_msg = state["messages"][-1]
        command = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        state["intent"] = _detect_intent(command)
        state["tool_results"] = []
        state["success"] = False
        return state

    def agent_reason(state: AgentState) -> AgentState:
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = llm_with_tools.invoke(messages)
        state["messages"] = state["messages"] + [response]
        return state

    def should_continue(state: AgentState) -> str:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return "summarize"

    def process_tool_results(state: AgentState) -> AgentState:
        """Extract ToolResult objects from tool messages after ToolNode runs."""
        tool_results = list(state.get("tool_results", []))
        for msg in reversed(state["messages"]):
            if hasattr(msg, "name") and hasattr(msg, "content"):
                try:
                    data = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                    success = "error" not in (data if isinstance(data, dict) else {})
                    tool_results.append(ToolResult(
                        tool_name=msg.name,
                        success=success,
                        data=data,
                        error=data.get("error") if isinstance(data, dict) else None,
                    ))
                except (json.JSONDecodeError, AttributeError, TypeError) as exc:
                    logger.warning("Failed to parse tool result message: %s", exc)
                break
        state["tool_results"] = tool_results
        return state

    def summarize(state: AgentState) -> AgentState:
        tool_results = state.get("tool_results", [])
        state["success"] = all(r.success for r in tool_results) if tool_results else False
        last = state["messages"][-1]
        state["final_summary"] = last.content if hasattr(last, "content") else "Operation completed."
        return state

    graph = StateGraph(AgentState)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("agent_reason", agent_reason)
    graph.add_node("tools", tool_node)
    graph.add_node("process_tool_results", process_tool_results)
    graph.add_node("summarize", summarize)

    graph.set_entry_point("classify_intent")
    graph.add_edge("classify_intent", "agent_reason")
    graph.add_conditional_edges("agent_reason", should_continue, {"tools": "tools", "summarize": "summarize"})
    graph.add_edge("tools", "process_tool_results")
    graph.add_edge("process_tool_results", "agent_reason")
    graph.add_edge("summarize", END)

    return graph.compile()


# Singleton compiled graph — protected by module-level import lock (thread-safe at import time)
_graph = None


def get_graph():
    global _graph  # noqa: PLW0603 — intentional module-level singleton
    if _graph is None:
        _graph = build_graph()
    return _graph


async def run_agent(command: str, session_id: str | None = None, context: dict | None = None) -> dict:
    session_id = session_id or str(uuid.uuid4())
    graph = get_graph()

    initial_state: AgentState = {
        "messages": [HumanMessage(content=command)],
        "intent": IntentType.UNKNOWN,
        "session_id": session_id,
        "tool_results": [],
        "final_summary": "",
        "success": False,
        "context": context or {},
    }

    result = await graph.ainvoke(initial_state)
    return {
        "session_id": session_id,
        "intent": result["intent"],
        "summary": result["final_summary"],
        "steps": result["tool_results"],
        "success": result["success"],
    }
