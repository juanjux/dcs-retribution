import contextlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import (
    controlpoints,
    debuggeometries,
    eventstream,
    flights,
    frontlines,
    game,
    mapzones,
    navmesh,
    qt,
    supplyroutes,
    tgos,
    waypoints,
    iadsnetwork,
    retributionai,
)
from .settings import ServerSettings

# The MCP transport is optional: if `mcp` isn't installed the REST API still runs.
try:
    from game.mcp.server import mcp as _mcp
except Exception:  # pragma: no cover - mcp[cli] is an optional dependency
    _mcp = None


@contextlib.asynccontextmanager
async def _lifespan(_app: FastAPI):
    async with contextlib.AsyncExitStack() as stack:
        if _mcp is not None:
            # Required for the streamable-HTTP MCP app mounted at /mcp.
            await stack.enter_async_context(_mcp.session_manager.run())
        yield


app = FastAPI(lifespan=_lifespan)
app.include_router(controlpoints.router)
app.include_router(debuggeometries.router)
app.include_router(eventstream.router)
app.include_router(flights.router)
app.include_router(frontlines.router)
app.include_router(game.router)
app.include_router(mapzones.router)
app.include_router(navmesh.router)
app.include_router(qt.router)
app.include_router(supplyroutes.router)
app.include_router(tgos.router)
app.include_router(waypoints.router)
app.include_router(iadsnetwork.router)
app.include_router(retributionai.router)

if _mcp is not None:
    app.mount("/mcp", _mcp.streamable_http_app())


origins = ["file://"]
if ServerSettings.get().cors_allow_debug_server:
    origins.append("http://localhost:3000")


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
