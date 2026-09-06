"""The /start doc must describe the endpoints that actually exist.

A wrong endpoint in the docs is worse than a missing one: the planner reads /start,
calls what it says, gets a 404, and burns the turn guessing. This drifted to twelve
invented endpoints (POST /transfers, POST /buy/auto, GET /ai_log, ...) before anyone
noticed, because nothing compared the prose against the router.
"""

from __future__ import annotations

import re
from pathlib import Path

_ROUTES = Path("game/server/retributionai/routes.py")
_START_DOC = Path("game/agent/docs/start.md")

# The decorator's first string literal is the path, whether or not the call spans lines.
_ROUTE_RE = re.compile(r'@router\.(get|post|delete|put)\((?:[^)]*?)"(/[^"]*)"', re.S)
_CITED_RE = re.compile(r"`(GET|POST|DELETE|PUT) (/[^`\s]+)")


def _normalise(path: str) -> str:
    """Drop the query string and the router prefix, and blank out path params."""
    path = path.split("?")[0].rstrip("`")
    path = path.replace("/retribution-ai", "")
    return re.sub(r"\{[^}]+\}", "{}", path)


def _real_endpoints() -> set[tuple[str, str]]:
    text = _ROUTES.read_text(encoding="utf-8")
    return {
        (m.group(1).upper(), _normalise(m.group(2))) for m in _ROUTE_RE.finditer(text)
    }


def _cited_endpoints() -> set[tuple[str, str]]:
    text = _START_DOC.read_text(encoding="utf-8")
    return {(verb, _normalise(path)) for verb, path in _CITED_RE.findall(text)}


def test_start_doc_cites_no_endpoint_that_does_not_exist() -> None:
    invented = sorted(_cited_endpoints() - _real_endpoints())
    assert not invented, (
        "/start documents endpoints the server does not serve; the planner will 404 "
        f"on them: {invented}"
    )


def test_start_doc_documents_every_endpoint() -> None:
    """An endpoint the planner cannot read about is one it never calls."""
    undocumented = sorted(_real_endpoints() - _cited_endpoints())
    assert not undocumented, f"endpoints served but absent from /start: {undocumented}"
