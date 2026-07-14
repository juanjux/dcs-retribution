"""Transient OPFOR-AI session state (not persisted, not in the save).

Shared between the server thread (the LLM drives it via REST/MCP) and the Qt main
thread (the toolbar robot reads ``active``/``status``; Take Off is gated on
``active``; the player can ``cancel`` a running AI turn). Plain attributes guarded
by a lock — a process-wide singleton, since there is exactly one live game.

There is no manual on/off: ``active`` is derived from recent activity. Every API
call (any REST/MCP transport hit) calls ``touch()``, and the robot reads as active
for ``ACTIVE_WINDOW`` afterwards — so it lights up for a few seconds on each call
and settles back to idle once the LLM stops talking to us.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

#: How long the robot stays "active" (lit, Take Off gated) after each API call.
ACTIVE_WINDOW = timedelta(seconds=5)


class _AiSession:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.status = ""
        self.cancelled = False
        self.updated_at: datetime | None = None
        self._last_activity: datetime | None = None

    def _active_locked(self) -> bool:
        if self._last_activity is None:
            return False
        return datetime.now(timezone.utc) - self._last_activity < ACTIVE_WINDOW

    @property
    def active(self) -> bool:
        """True while an API call landed within the last ``ACTIVE_WINDOW``."""
        with self._lock:
            return self._active_locked()

    def touch(self) -> None:
        """Record an API call: the robot lights up for ``ACTIVE_WINDOW`` from now."""
        with self._lock:
            self._last_activity = datetime.now(timezone.utc)
            self.cancelled = False  # fresh activity clears a stale cancel
            self.updated_at = self._last_activity

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
                "active": self._active_locked(),
                "status": self.status,
                "cancelled": self.cancelled,
                "updated_at": (
                    self.updated_at.isoformat() if self.updated_at else None
                ),
            }


AI_SESSION = _AiSession()
