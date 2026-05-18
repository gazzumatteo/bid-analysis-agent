# Copyright 2026 Google LLC
"""Minimal local A2A server for demo use.

Usage:
    uv run uvicorn streamlit_app.a2a_server:server --port 9090 --reload

This is a stripped-down version of fast_api_app.py with no GCP logging or
telemetry — designed for local demos where only Vertex AI credentials are needed.
"""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH, EXTENDED_AGENT_CARD_PATH
from fastapi import FastAPI
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from app.agent import app as adk_app
from app.agent import configure_vertex_ai

configure_vertex_ai()

PORT = int(os.getenv("A2A_PORT", "9090"))
A2A_RPC_PATH = f"/a2a/{adk_app.name}"

_runner = Runner(
    app=adk_app,
    artifact_service=InMemoryArtifactService(),
    session_service=InMemorySessionService(),
)
_handler = DefaultRequestHandler(
    agent_executor=A2aAgentExecutor(runner=_runner),
    task_store=InMemoryTaskStore(),
)


@asynccontextmanager
async def _lifespan(fastapi_app: FastAPI) -> AsyncIterator[None]:
    agent_card = await AgentCardBuilder(
        agent=adk_app.root_agent,
        capabilities=AgentCapabilities(streaming=True),
        rpc_url=f"http://localhost:{PORT}{A2A_RPC_PATH}",
    ).build()
    a2a = A2AFastAPIApplication(agent_card=agent_card, http_handler=_handler)
    a2a.add_routes_to_app(
        fastapi_app,
        agent_card_url=f"{A2A_RPC_PATH}{AGENT_CARD_WELL_KNOWN_PATH}",
        rpc_url=A2A_RPC_PATH,
        extended_agent_card_url=f"{A2A_RPC_PATH}{EXTENDED_AGENT_CARD_PATH}",
    )
    yield


server = FastAPI(
    title="Bid Analysis Agent — Local A2A Demo Server",
    lifespan=_lifespan,
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(server, host="0.0.0.0", port=PORT)
