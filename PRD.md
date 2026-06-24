# PRD: Fleet Update Orchestrator

## Problem

Teams running software across many machines (servers, IoT devices, edge
fleets) need a reliable way to push out updates without manually touching
each machine, and without risking a bad update reaching the entire fleet at
once. Most ad-hoc approaches (SSH loops, manual scripts) don't track state,
don't handle partial failure, and don't support staged rollout.

## Goal

Build a minimal but real control plane that can:
1. Track which version every machine in the fleet is running.
2. Roll out a new version safely, in stages, with automatic halt on failure.
3. Tolerate machines being temporarily offline without missing them.

## Non-goals (v1)

- Real production-grade security (auth, mTLS) — flagged as a known gap,
  not silently ignored.
- Multi-region or multi-control-plane HA — single control plane is
  sufficient to demonstrate the core mechanics.
- A UI — the API and CLI are sufficient for v1; a dashboard is a natural v2.

## Users

- **Primary**: an engineer or SRE managing a small-to-medium fleet who
  needs visibility into rollout state and a safe default rollout strategy.
- **Secondary** (for this project specifically): an interviewer or
  recruiter evaluating technical + product judgment from a single
  artifact.

## Key design decisions and tradeoffs

| Decision | Choice | Why | Tradeoff accepted |
|---|---|---|---|
| Push vs. pull | Pull (agents poll) | Resilient to transient agent downtime; matches Borg/Kubernetes precedent | Update propagation has latency = poll interval, not instant |
| Rollout strategy | Canary by default | Limits blast radius of a bad update to one machine | Slower full-fleet rollout than "update everyone at once" |
| State storage | In-memory (v1) | Fast to build, fine for demo scale | Not durable across control plane restarts — flagged as v2 work |
| Failure handling | Halt rollout on canary failure | Safety over speed — matches how real fleet operators behave | Requires an operator to manually investigate and resume |

## Success metrics (if this were a real product)

- Time to detect and halt a bad rollout (target: within one poll interval
  of the canary failing).
- Percentage of fleet successfully reconciled to target version within N
  poll cycles.
- Operator time spent per rollout (target: near zero after triggering).

## V2 ideas (explicitly out of scope, listed to show roadmap thinking)

- Persistent state store (SQLite/Postgres) so fleet state survives restarts.
- Web dashboard showing live fleet state and rollout progress.
- Configurable canary size (N machines, not just 1) and rolling batch size.
- Real update mechanism: container image pull or signed binary deployment.
- Agent authentication via mTLS or signed tokens.
