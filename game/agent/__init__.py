"""OPFOR-AI agent feature.

The single source of truth for the LLM-driven OPFOR commander: a pure-Python
service layer (``service.py``) over the live ``Game`` (via ``GameContext.require``)
that both the REST routers (``game/server/retributionai/``) and the MCP tools
(``game/mcp/``) delegate to. See ``ai-docs/`` for the full design.
"""
