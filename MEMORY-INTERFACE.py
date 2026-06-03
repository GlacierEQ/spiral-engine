#!/usr/bin/env python3
"""
APEX Memory Interface — spiral-engine
Double helix. Each revolution compounds intelligence.
from spiral_engine.memory_interface import remember, recall, log_revolution
"""
import sys, os
PRO_MEMORY_PATH = os.environ.get("PRO_MEMORY_PATH", "../Pro-Memory")
if PRO_MEMORY_PATH not in sys.path:
    sys.path.insert(0, PRO_MEMORY_PATH)
from MEM0_MASTER import APEXMemoryRouter
_router = None
def get_router():
    global _router
    if _router is None: _router = APEXMemoryRouter()
    return _router
def remember(content, category="agent_state", metadata=None):
    return get_router().remember("mastermind", content, category, metadata)
def recall(query): return get_router().recall("mastermind", query, "agent_state")
def log_revolution(n, helix, output_summary):
    """Log each spiral revolution. Each one compounds."""
    return remember(
        f"Spiral revolution {n} [{helix}]: {output_summary}",
        category="agent_state",
        metadata={"revolution": n, "helix": helix, "case": "1FDV-23-0001009"}
    )
