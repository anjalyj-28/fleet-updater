from pydantic import BaseModel
from typing import Literal, Optional


class RegisterRequest(BaseModel):
    agent_id: str
    os_version: str
    current_version: str


class ReportRequest(BaseModel):
    agent_id: str
    version: str
    status: Literal["success", "failed"]
    detail: Optional[str] = None


class RolloutRequest(BaseModel):
    target_version: str
    strategy: Literal["canary", "rolling", "all"] = "canary"
    batch_size: int = 1  # used when strategy == "rolling"


class DesiredStateResponse(BaseModel):
    action: Literal["update", "hold"]
    target_version: Optional[str] = None


class AgentState(BaseModel):
    agent_id: str
    os_version: str
    current_version: str
    last_seen: Optional[str] = None
    last_status: Optional[str] = None
    eligible_for_update: bool = False
