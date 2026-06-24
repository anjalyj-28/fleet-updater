"""
In-memory fleet state and rollout orchestration logic.

This is intentionally simple (a dict, not a database) — see README for why
that's an acceptable scope cut for this project. The interesting logic is
in `decide_action_for`, which implements canary / rolling / all strategies
and the "halt on canary failure" safety rule.
"""

from datetime import datetime, timezone
from threading import Lock
from typing import Dict, Optional

from control_plane.models import AgentState


class FleetState:
    def __init__(self):
        self._lock = Lock()
        self._agents: Dict[str, AgentState] = {}
        self._rollout: Optional[dict] = None  # {target_version, strategy, batch_size}
        self._canary_agent_id: Optional[str] = None
        self._canary_result: Optional[str] = None  # None | "success" | "failed"
        self._updated_agent_ids: set = set()

    # -- registration / reporting -------------------------------------

    def register(self, agent_id: str, os_version: str, current_version: str):
        with self._lock:
            self._agents[agent_id] = AgentState(
                agent_id=agent_id,
                os_version=os_version,
                current_version=current_version,
                last_seen=_now(),
            )

    def report(self, agent_id: str, version: str, status: str, detail: Optional[str]):
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return
            agent.current_version = version
            agent.last_seen = _now()
            agent.last_status = status

            if agent_id == self._canary_agent_id:
                self._canary_result = status
            if status == "success":
                self._updated_agent_ids.add(agent_id)

    def list_agents(self):
        with self._lock:
            return list(self._agents.values())

    # -- rollout control --------------------------------------------

    def start_rollout(self, target_version: str, strategy: str, batch_size: int):
        with self._lock:
            self._rollout = {
                "target_version": target_version,
                "strategy": strategy,
                "batch_size": batch_size,
            }
            self._canary_agent_id = None
            self._canary_result = None
            self._updated_agent_ids = set()

    def current_rollout(self):
        with self._lock:
            return self._rollout

    # -- the core decision: what should THIS agent do right now? -----

    def decide_action_for(self, agent_id: str) -> dict:
        """
        Returns {"action": "hold"} or {"action": "update", "target_version": ...}

        Encodes the rollout strategy:
          - canary: only the first agent to poll gets the update. Everyone
            else holds until the canary reports success. If the canary
            fails, the rollout halts entirely (no one else gets updated).
          - rolling: agents get updated in arrival order, batch_size at a time.
          - all: every agent is eligible immediately.
        """
        with self._lock:
            rollout = self._rollout
            agent = self._agents.get(agent_id)
            if not rollout or not agent:
                return {"action": "hold"}

            if agent.current_version == rollout["target_version"]:
                return {"action": "hold"}

            strategy = rollout["strategy"]

            if strategy == "all":
                return {"action": "update", "target_version": rollout["target_version"]}

            if strategy == "canary":
                if self._canary_agent_id is None:
                    # this agent becomes the canary
                    self._canary_agent_id = agent_id
                    return {"action": "update", "target_version": rollout["target_version"]}
                if agent_id == self._canary_agent_id:
                    return {"action": "update", "target_version": rollout["target_version"]}
                if self._canary_result == "success":
                    return {"action": "update", "target_version": rollout["target_version"]}
                # canary hasn't succeeded yet (still pending, or it failed) -> hold
                return {"action": "hold"}

            if strategy == "rolling":
                batch_size = rollout.get("batch_size", 1)
                if len(self._updated_agent_ids) < batch_size:
                    return {"action": "update", "target_version": rollout["target_version"]}
                return {"action": "hold"}

            return {"action": "hold"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


fleet_state = FleetState()
