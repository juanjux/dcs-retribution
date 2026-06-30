"""MCP transport for the OPFOR-AI feature (optional — requires ``mcp[cli]``).

Isolated so the rest of the engine never imports ``mcp``; only this package and the
mount in ``game/server/app.py`` do (kept optional there). See ``ai-docs/``.
"""
