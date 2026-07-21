import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.api.app import create_app

app = create_app()
client = TestClient(app)


@pytest.fixture
def mock_run_agent():
    with patch("app.api.routes.run_agent") as mock:
        mock.return_value = {
            "session_id": "test-session-123",
            "intent": "deploy",
            "summary": "Successfully triggered deployment of payment-service to staging.",
            "steps": [
                {"tool_name": "mcp_deploy", "success": True, "data": {"status": "triggered"}, "error": None}
            ],
            "success": True,
        }
        yield mock


def test_health_endpoint():
    resp = client.get("/agent/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_run_deploy_command(mock_run_agent):
    resp = client.post("/agent/run", json={"command": "Deploy payment-service to staging"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "deploy"
    assert data["success"] is True
    assert "payment-service" in data["summary"]


def test_run_status_command(mock_run_agent):
    mock_run_agent.return_value.update({"intent": "status", "summary": "payment-service: 3/3 pods ready."})
    resp = client.post("/agent/run", json={"command": "Check deployment status of payment-service"})
    assert resp.status_code == 200


def test_run_command_with_session(mock_run_agent):
    resp = client.post("/agent/run", json={
        "command": "Show logs for payment-service",
        "session_id": "my-session-abc",
    })
    assert resp.status_code == 200
    mock_run_agent.assert_called_once()
    call_kwargs = mock_run_agent.call_args
    assert call_kwargs.kwargs["session_id"] == "my-session-abc"


def test_run_command_agent_error():
    with patch("app.api.routes.run_agent", side_effect=RuntimeError("LLM unavailable")):
        resp = client.post("/agent/run", json={"command": "Deploy service"})
        assert resp.status_code == 500
        assert "LLM unavailable" in resp.json()["detail"]
