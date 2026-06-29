"""Transient OPFOR-AI session state (not persisted, not in the save).

Shared between the server thread (the LLM toggles it via REST/MCP) and the Qt main
thread (the toolbar robot reads ``active``/``status``; Take Off is gated on
``active``; the player can ``cancel`` a running AI turn). Plain attributes guarded
by a lock — a process-wide singleton, since there is exactly one live game.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone


class _AiSession:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.active = False
        self.status = ""
        self.cancelled = False
        self.updated_at: datetime | None = None

    def set_active(self, active: bool) -> None:
        with self._lock:
            self.active = active
            if active:
                self.cancelled = False  # a fresh turn clears a stale cancel
            self.updated_at = datetime.now(timezone.utc)

    def set_status(self, status: str) -> None:
        with self._lock:
            self.status = status
            self.updated_at = datetime.now(timezone.utc)

    def cancel(self) -> None:
        """Player asks the AI to stop; its next write should be refused."""
        with self._lock:
            self.cancelled = True
            self.updated_at = datetime.now(timezone.utc)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "active": self.active,
                "status": self.status,
                "cancelled": self.cancelled,
                "updated_at": (
                    self.updated_at.isoformat() if self.updated_at else None
                ),
            }


AI_SESSION = _AiSession()
