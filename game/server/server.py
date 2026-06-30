import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from threading import Thread
from typing import Optional

import uvicorn
from uvicorn import Config

from game.server import EventStream
from game.server.app import app
from game.server.security import ApiKeyManager
from game.server.settings import ServerSettings
from game.sim import GameUpdateEvents

# Upper bound (seconds) on uvicorn's graceful shutdown. Without it, uvicorn waits
# forever for in-flight tasks/connections to drain. The web UI keeps a long-lived
# /eventstream websocket open, and if the client goes away without closing the
# socket cleanly (e.g. the Qt web view is torn down as the window closes) that
# handler's task never finishes, so serve() never returns and the join() below
# hangs the whole process on exit. Capping the timeout lets uvicorn cancel the
# straggler and stop the server thread.
GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS = 3


class Server(uvicorn.Server):
    def __init__(self, port: Optional[int]) -> None:
        settings = ServerSettings.get(port)
        super().__init__(
            Config(
                app=app,
                host=settings.server_bind_address,
                port=settings.server_port,
                # Configured explicitly with default_logging.yaml or logging.yaml.
                log_config=None,
                timeout_graceful_shutdown=GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS,
            )
        )

    @contextmanager
    def run_in_thread(self) -> Iterator[None]:
        # This relies on undocumented behavior, but it is what the developer recommends:
        # https://github.com/encode/uvicorn/issues/742
        thread = Thread(target=self.run)
        thread.start()
        try:
            while not self.started:
                time.sleep(1e-3)
            host = self.config.host
            logging.getLogger(__name__).info(
                "OPFOR-AI commander API ready — point an LLM at "
                "http://%s:%s/retribution-ai/start?token=%s",
                f"[{host}]" if ":" in str(host) else host,
                self.config.port,
                ApiKeyManager.KEY,
            )
            yield
        finally:
            self.should_exit = True
            EventStream.put_nowait(GameUpdateEvents().shut_down())
            # timeout_graceful_shutdown caps how long uvicorn waits for in-flight
            # tasks, so the thread should stop within a few seconds even if the
            # /eventstream websocket task is wedged. Give it a small grace beyond
            # that before checking.
            thread.join(timeout=GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS + 2)
            if thread.is_alive():
                # Graceful shutdown stalled anyway; force uvicorn to stop waiting
                # so the process can exit instead of hanging on join() forever.
                self.force_exit = True
                thread.join(timeout=GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS)
