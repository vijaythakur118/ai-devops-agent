import pytest
from app.agent.workflow import _detect_intent
from app.core.models import IntentType


@pytest.mark.parametrize("command,expected", [
    ("Deploy payment-service to staging", IntentType.DEPLOY),
    ("Release order-service version 2.1", IntentType.DEPLOY),
    ("Check deployment status of auth-service", IntentType.STATUS),
    ("Is payment-service healthy?", IntentType.STATUS),
    ("Restart the notification-service", IntentType.RESTART),
    ("Bounce the worker pod", IntentType.RESTART),
    ("Show application logs for api-gateway", IntentType.LOGS),
    ("Rollback payment-service to previous version", IntentType.ROLLBACK),
    ("Revert the last deployment", IntentType.ROLLBACK),
    ("What is the weather today?", IntentType.UNKNOWN),
])
def test_intent_detection(command, expected):
    assert _detect_intent(command) == expected


def test_tool_result_model():
    from app.core.models import ToolResult
    result = ToolResult(tool_name="mcp_deploy", success=True, data={"status": "ok"})
    assert result.tool_name == "mcp_deploy"
    assert result.error is None


def test_agent_request_model():
    from app.core.models import AgentRequest
    req = AgentRequest(command="Deploy service", session_id="abc")
    assert req.command == "Deploy service"
    assert req.context == {}
