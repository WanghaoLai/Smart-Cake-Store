"""Agent configuration loaded from environment and a versioned JSON profile."""

import json
import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from settings import AI_CONFIG


AGENTS_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE_PATH = AGENTS_DIR / "config" / "customer_service.json"


class AgentProfile(BaseModel):
    name: str
    description: str = ""
    system_prompt: str
    tools: list[str] = Field(default_factory=list)
    max_history: int = Field(default=20, ge=0, le=100)
    max_model_calls: int = Field(default=4, ge=1, le=10)
    max_tool_calls: int = Field(default=3, ge=1, le=10)


class AgentSettings(BaseModel):
    api_key: str = ""
    model: str = "qwen-turbo"
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    temperature: float = Field(default=0.2, ge=0, le=2)
    timeout_seconds: float = Field(default=45, gt=0, le=300)
    max_retries: int = Field(default=2, ge=0, le=5)
    embedding_model: str = "text-embedding-v2"
    rag_top_k: int = Field(default=3, ge=1, le=10)
    profile_path: Path = DEFAULT_PROFILE_PATH


settings = AgentSettings(
    api_key=AI_CONFIG["dashscope_api_key"],
    model=AI_CONFIG["model"],
    base_url=os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
    timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "45")),
    max_retries=int(os.getenv("LLM_MAX_RETRIES", "2")),
    embedding_model=AI_CONFIG["embedding_model"],
    rag_top_k=AI_CONFIG["top_k"],
    profile_path=Path(os.getenv("AGENT_CONFIG_PATH", str(DEFAULT_PROFILE_PATH))),
)


@lru_cache(maxsize=8)
def load_agent_profile(path: str | Path | None = None) -> AgentProfile:
    profile_path = Path(path) if path else settings.profile_path
    try:
        data = json.loads(profile_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Agent 配置不存在: {profile_path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Agent 配置不是合法 JSON: {profile_path}: {exc}") from exc
    # Deployment overrides are intentionally narrow; identity, prompt and tool
    # permissions remain version-controlled in the profile.
    if os.getenv("LLM_MAX_HISTORY"):
        data["max_history"] = int(os.environ["LLM_MAX_HISTORY"])
    if os.getenv("AGENT_MAX_MODEL_CALLS"):
        data["max_model_calls"] = int(os.environ["AGENT_MAX_MODEL_CALLS"])
    if os.getenv("AGENT_MAX_TOOL_CALLS"):
        data["max_tool_calls"] = int(os.environ["AGENT_MAX_TOOL_CALLS"])
    return AgentProfile.model_validate(data)
