"""
Fleet Update Orchestrator — control plane API.

Endpoints:
  POST /agents/register             agent registers itself on startup
  GET  /agents/{agent_id}/desired   agent polls: "what should I be running?"
  POST /agents/{agent_id}/report    agent reports the result of an update attempt
  POST /rollout                     operator triggers a new rollout
  GET  /rollout                     operator checks current rollout state
  GET  /fleet                       operator views all agents and their state
"""

from fastapi import FastAPI, HTTPException

from control_plane.models import (
    RegisterRequest,
    ReportRequest,
    RolloutRequest,
    DesiredStateResponse,
)
from control_plane.state import fleet_state

app = FastAPI(title="Fleet Update Orchestrator")


@app.post("/agents/register")
def register_agent(req: RegisterRequest):
    fleet_state.register(req.agent_id, req.os_version, req.current_version)
    return {"status": "registered", "agent_id": req.agent_id}


@app.get("/agents/{agent_id}/desired", response_model=DesiredStateResponse)
def get_desired_state(agent_id: str):
    decision = fleet_state.decide_action_for(agent_id)
    return DesiredStateResponse(**decision)


@app.post("/agents/{agent_id}/report")
def report_status(agent_id: str, req: ReportRequest):
    if req.agent_id != agent_id:
        raise HTTPException(status_code=400, detail="agent_id mismatch")
    fleet_state.report(agent_id, req.version, req.status, req.detail)
    return {"status": "recorded"}


@app.post("/rollout")
def start_rollout(req: RolloutRequest):
    fleet_state.start_rollout(req.target_version, req.strategy, req.batch_size)
    return {
        "status": "rollout started",
        "target_version": req.target_version,
        "strategy": req.strategy,
    }


@app.get("/rollout")
def get_rollout():
    rollout = fleet_state.current_rollout()
    if not rollout:
        return {"status": "no active rollout"}
    return rollout


@app.get("/fleet")
def get_fleet():
    return fleet_state.list_agents()
