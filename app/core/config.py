from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "AI DevOps Agent"
    debug: bool = False

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    # Kubernetes
    kubeconfig_path: str = ""
    k8s_in_cluster: bool = False

    # GitHub
    github_token: str = ""
    github_owner: str = ""
    github_repo: str = ""

    # MCP
    mcp_server_url: str = "http://localhost:8001"

    # Redis (for state persistence)
    redis_url: str = "redis://localhost:6379"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
