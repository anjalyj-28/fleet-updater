"""
Fleet agent — simulates a single machine in the fleet.

Run multiple instances with different AGENT_ID / OS_VERSION env vars to
simulate a heterogeneous fleet. Each instance:
  1. Registers itself with the control plane.
  2. Polls /agents/{id}/desired on an interval.
  3. If told to update, simulates applying the update (with a configurable
     chance of failure) and reports the result back.

This is the file you'd swap out for a real implementation — e.g. pulling a
container image, running a package manager command, or triggering a
configuration management run — without touching the control plane at all.
"""

import os
import random
import time

import requests

CONTROL_PLANE_URL = os.environ.get("CONTROL_PLANE_URL", "http://localhost:8000")
AGENT_ID = os.environ.get("AGENT_ID", "server-a")
OS_VERSION = os.environ.get("OS_VERSION", "ubuntu-22.04")
POLL_INTERVAL_SECONDS = float(os.environ.get("POLL_INTERVAL_SECONDS", "3"))
FAILURE_RATE = float(os.environ.get("FAILURE_RATE", "0.0"))  # 0.0-1.0, for testing canary halt

current_version = os.environ.get("STARTING_VERSION", "v1.0.0")


def register():
    resp = requests.post(
        f"{CONTROL_PLANE_URL}/agents/register",
        json={
            "agent_id": AGENT_ID,
            "os_version": OS_VERSION,
            "current_version": current_version,
        },
    )
    resp.raise_for_status()
    print(f"[{AGENT_ID}] registered, running {current_version} on {OS_VERSION}")


def poll_and_apply():
    global current_version

    resp = requests.get(f"{CONTROL_PLANE_URL}/agents/{AGENT_ID}/desired")
    resp.raise_for_status()
    decision = resp.json()

    if decision["action"] == "hold":
        print(f"[{AGENT_ID}] holding at {current_version}")
        return

    target_version = decision["target_version"]
    print(f"[{AGENT_ID}] applying update -> {target_version} ...")

    # Simulate the actual update mechanism. In a real agent this is where
    # you'd pull a container image, run `apt upgrade`, swap a binary, etc.
    time.sleep(1.5)
    failed = random.random() < FAILURE_RATE

    if failed:
        print(f"[{AGENT_ID}] update FAILED")
        requests.post(
            f"{CONTROL_PLANE_URL}/agents/{AGENT_ID}/report",
            json={
                "agent_id": AGENT_ID,
                "version": current_version,  # stayed on old version
                "status": "failed",
                "detail": "simulated failure",
            },
        )
        return

    current_version = target_version
    print(f"[{AGENT_ID}] update SUCCEEDED, now on {current_version}")
    requests.post(
        f"{CONTROL_PLANE_URL}/agents/{AGENT_ID}/report",
        json={
            "agent_id": AGENT_ID,
            "version": current_version,
            "status": "success",
        },
    )


def main():
    register()
    while True:
        try:
            poll_and_apply()
        except requests.RequestException as e:
            print(f"[{AGENT_ID}] control plane unreachable: {e}")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
