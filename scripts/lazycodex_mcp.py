#!/usr/bin/env python3
"""LazyCodex MCP server entrypoint (stdio).

Register with Codex CLI:
    codex mcp add lazycodex -- python3 /path/to/LazyCodex/scripts/lazycodex_mcp.py

Then invoke any tool in a session:
    /mcp call lazycodex lazycodex_tabs
    /mcp call lazycodex lazycodex_cost_summary
    /mcp call lazycodex lazycodex_security_scan
    ...

No network. No auth. Runs entirely on the local machine against ~/.codex/.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.mcp_server import run

if __name__ == "__main__":
    run()
