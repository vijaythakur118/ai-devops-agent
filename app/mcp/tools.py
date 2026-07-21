"""
MCP Tool definitions for the DevOps Agent.
Each tool wraps a K8s or CI/CD operation and is registered with LangGraph.
"""
import re
from langchain_core.tools import tool
from app.k8s.client import (
    deploy_service,
    get_deployment_status,
    restart_deployment,
    get_pod_logs,
    rollback_deployment,
)
from app.cicd.github_actions import trigger_deploy_pipeline, get_workflow_runs
from app.core.logging import get_logger

logger = get_logger(__name__)

# Allowlist: only alphanumeric, hyphens, dots — prevents injection into K8s/shell calls
_SAFE_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-\.]{0,62}$")
_SAFE_ENV = re.compile(r"^(staging|production|dev|qa)$")
_SAFE_TAG = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-\.\:_]{0,127}$")


def _validate(value: str, pattern: re.Pattern, field: str) -> str:
    if not pattern.match(value):
        raise ValueError(f"Invalid {field}: '{value}' — rejected by allowlist")
    return value


@tool
def mcp_deploy(service: str, environment: str, image_tag: str = "latest") -> dict:
    """Deploy a service to a Kubernetes namespace via GitHub Actions pipeline.
    Use this when the user wants to deploy or release a service."""
    _validate(service, _SAFE_NAME, "service")
    _validate(environment, _SAFE_ENV, "environment")
    _validate(image_tag, _SAFE_TAG, "image_tag")
    logger.info("MCP deploy: service=%s env=%s tag=%s", service, environment, image_tag)
    import asyncio
    result = asyncio.run(trigger_deploy_pipeline(service, environment, image_tag))
    return result


@tool
def mcp_status(service: str, namespace: str = "default") -> dict:
    """Check the deployment status of a Kubernetes service.
    Use this when the user asks about deployment health or readiness."""
    _validate(service, _SAFE_NAME, "service")
    _validate(namespace, _SAFE_NAME, "namespace")
    logger.info("MCP status: service=%s ns=%s", service, namespace)
    return get_deployment_status(service, namespace)


@tool
def mcp_restart(service: str, namespace: str = "default") -> dict:
    """Restart a Kubernetes deployment by triggering a rolling restart.
    Use this when the user wants to restart or bounce a service."""
    _validate(service, _SAFE_NAME, "service")
    _validate(namespace, _SAFE_NAME, "namespace")
    logger.info("MCP restart: service=%s ns=%s", service, namespace)
    return restart_deployment(service, namespace)


@tool
def mcp_logs(service: str, namespace: str = "default", tail: int = 100) -> dict:
    """Fetch recent pod logs for a Kubernetes service.
    Use this when the user wants to see application logs or debug issues."""
    _validate(service, _SAFE_NAME, "service")
    _validate(namespace, _SAFE_NAME, "namespace")
    tail = max(1, min(tail, 1000))  # clamp to safe range
    logger.info("MCP logs: service=%s ns=%s tail=%d", service, namespace, tail)
    return get_pod_logs(service, namespace, tail)


@tool
def mcp_rollback(service: str, namespace: str = "default") -> dict:
    """Rollback a Kubernetes deployment to the previous revision.
    Use this when the user wants to undo a deployment or revert changes."""
    _validate(service, _SAFE_NAME, "service")
    _validate(namespace, _SAFE_NAME, "namespace")
    logger.info("MCP rollback: service=%s ns=%s", service, namespace)
    return rollback_deployment(service, namespace)


@tool
def mcp_pipeline_status(service: str) -> dict:
    """Get the latest GitHub Actions workflow run status for a service.
    Use this to check CI/CD pipeline progress."""
    _validate(service, _SAFE_NAME, "service")
    logger.info("MCP pipeline status: service=%s", service)
    import asyncio
    return asyncio.run(get_workflow_runs("deploy.yml"))


ALL_TOOLS = [mcp_deploy, mcp_status, mcp_restart, mcp_logs, mcp_rollback, mcp_pipeline_status]
