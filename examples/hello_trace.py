"""
AgentOps End-to-End Example
============================
Demonstrates the full SDK -> server -> dashboard loop.

Usage:
    cd sdk && pip install -e . -q
    cd ..
    python examples/hello_trace.py

Then open http://localhost:3000 to see the trace.
"""
import sys
import time

import agentops

# Point to local dev server
agentops.init(
    api_key="dev_key",
    endpoint="http://localhost:8080",
    project="01JDEFAULTPROJECT000000",
)


@agentops.track(name="hello_agent")
def hello_agent(prompt: str) -> str:
    """Simulates an AI agent doing some work."""
    time.sleep(0.1)  # simulate LLM latency
    return f"Processed: {prompt}"


if __name__ == "__main__":
    print("Running hello_agent...")
    result = hello_agent("What is AgentOps?")
    print(f"Result: {result}")
    print()
    print("✓ Trace sent to AgentOps server")
    print("  API server: http://localhost:8080")
    print("  Open http://localhost:3000 to see the run in the dashboard.")
