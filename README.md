# Fleet Update Orchestrator

A minimal control plane for orchestrating software updates across a fleet of
heterogeneous machines — built as a portfolio project demonstrating both
product thinking (see `PRD.md`) and the underlying distributed-systems
mechanics (pull-based reconciliation, canary rollout, failure handling).

Inspired by the design principles behind Google's Borg and Kubernetes
(declarative desired state, agents reconciling toward it) — scoped down to
something a single person can build, run, and explain end to end.

## Architecture

```
┌─────────────────────┐
│    Control plane     │   Tracks fleet state, decides rollout order
│  (FastAPI, in-mem)   │   Single source of truth: target version + strategy
└──────────┬───────────┘
           │  HTTP (poll / report)
   ┌───────┼───────┬───────────┐
   ▼               ▼           ▼
┌────────┐    ┌────────┐  ┌────────┐
│Agent A │    │Agent B │  │Agent C │   Each agent polls for desired
│Ubuntu  │    │Debian  │  │CentOS  │   state, applies updates, reports
└────────┘    └────────┘  └────────┘   back success/failure
```

**Why pull, not push.** Agents poll the control plane on an interval and
reconcile their own state toward whatever the control plane says the target
should be. This is more resilient than push: if an agent is offline when an
update is announced, it simply catches up on its next poll instead of being
permanently missed. Borg and Kubernetes both default to this pattern. A
manual "force update now" push endpoint is included for operator overrides.

**Why canary first.** Rather than updating the whole fleet at once, the
control plane updates one agent, waits for a success report, then proceeds
to the rest. If the canary fails, the rollout halts automatically — nobody
else gets the bad update.

## Project structure

```
fleet-update-orchestrator/
├── control_plane/
│   ├── main.py        # FastAPI app: registration, polling, reporting, rollout
│   ├── models.py       # Pydantic request/response models
│   └── state.py         # In-memory fleet state store
├── agent/
│   └── agent.py          # Polling agent: simulates applying an update
├── PRD.md                  # One-page product spec (problem, scope, tradeoffs)
├── requirements.txt
└── README.md
```

## Running it locally

```bash
pip install -r requirements.txt

# Terminal 1 — start the control plane
uvicorn control_plane.main:app --reload --port 8000

# Terminal 2, 3, 4 — start a few simulated fleet machines
AGENT_ID=server-a OS_VERSION=ubuntu-22.04 python agent/agent.py
AGENT_ID=server-b OS_VERSION=debian-12    python agent/agent.py
AGENT_ID=server-c OS_VERSION=centos-9     python agent/agent.py
```

Then trigger a rollout:

```bash
curl -X POST http://localhost:8000/rollout \
  -H "Content-Type: application/json" \
  -d '{"target_version": "v2.0.0", "strategy": "canary"}'
```

Watch the agent terminals — the first agent to poll picks up the canary,
applies it, and reports back. Once it succeeds, the control plane releases
the update to the rest of the fleet on their next poll.

Check fleet state any time:

```bash
curl http://localhost:8000/fleet
```

## What this does NOT do (intentionally, for scope)

- No real SSH/binary deployment — agents simulate "applying an update" with
  a delay and a configurable failure rate. Swapping in a real update
  mechanism (pulling a container image, running a package manager command)
  is a contained change to `agent/agent.py`.
- No persistent storage — fleet state is in-memory and resets on restart.
  A real version would use SQLite or Postgres.
- No auth between agents and control plane. A real version would use
  mTLS or signed agent tokens.

These are documented here deliberately — knowing what you cut and why is
part of the product thinking this project is meant to demonstrate.
