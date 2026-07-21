import httpx
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

GITHUB_API = "https://api.github.com"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def trigger_workflow(workflow_id: str, ref: str, inputs: dict) -> dict:
    url = f"{GITHUB_API}/repos/{settings.github_owner}/{settings.github_repo}/actions/workflows/{workflow_id}/dispatches"
    async with httpx.AsyncClient() as http:
        resp = await http.post(url, headers=_headers(), json={"ref": ref, "inputs": inputs})
        resp.raise_for_status()
        return {"triggered": True, "workflow": workflow_id, "ref": ref}


async def get_workflow_runs(workflow_id: str, limit: int = 5) -> dict:
    url = f"{GITHUB_API}/repos/{settings.github_owner}/{settings.github_repo}/actions/workflows/{workflow_id}/runs"
    async with httpx.AsyncClient() as http:
        resp = await http.get(url, headers=_headers(), params={"per_page": limit})
        resp.raise_for_status()
        data = resp.json()
        runs = [
            {
                "id": r["id"],
                "status": r["status"],
                "conclusion": r["conclusion"],
                "created_at": r["created_at"],
                "html_url": r["html_url"],
            }
            for r in data.get("workflow_runs", [])
        ]
        return {"workflow": workflow_id, "runs": runs}


async def trigger_deploy_pipeline(service: str, environment: str, image_tag: str = "latest") -> dict:
    return await trigger_workflow(
        workflow_id="deploy.yml",
        ref="main",
        inputs={"service": service, "environment": environment, "image_tag": image_tag},
    )
