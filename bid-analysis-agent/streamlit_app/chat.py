# Copyright 2026 Google LLC
"""Streamlit chat UI for the Bid Analysis Agent.

Supports two backend modes:
  • Local A2A  — connects to a local uvicorn A2A server
  • Agent Runtime — connects directly to the deployed Vertex AI Agent Runtime

Usage — Local A2A mode (2 terminals):
    # Terminal 1 — A2A server
    uv run uvicorn streamlit_app.a2a_server:server --port 9090

    # Terminal 2 — Streamlit UI
    uv run streamlit run streamlit_app/chat.py

Usage — Agent Runtime mode (1 terminal):
    uv run streamlit run streamlit_app/chat.py
    # Then select "Agent Runtime" in the sidebar and enter the resource name.
"""

import asyncio
import uuid
import warnings

import httpx
import streamlit as st

# Suppress deprecation warning from the legacy A2AClient wrapper
warnings.filterwarnings("ignore", category=DeprecationWarning, module="a2a")

from a2a.client import (  # noqa: E402
    A2ACardResolver,
    A2AClient,
    create_text_message_object,
)
from a2a.types import (  # noqa: E402
    Message,
    MessageSendParams,
    SendStreamingMessageRequest,
    Task,
    TaskState,
    TaskStatusUpdateEvent,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_DEFAULT_A2A_SERVER = "http://localhost:9090/a2a/app"
_DEFAULT_AGENT_RUNTIME = (
    "projects/460676655576/locations/us-central1/reasoningEngines/2735792187848523776"
)

# ---------------------------------------------------------------------------
# A2A helpers (local mode)
# ---------------------------------------------------------------------------


def _text_from_message(message: Message | None) -> str:
    if message is None:
        return ""
    return "".join(
        part.root.text for part in message.parts if hasattr(part.root, "text")
    )


async def _send_a2a_async(
    user_text: str,
    context_id: str | None,
    server_url: str,
) -> tuple[str, str | None, bool]:
    async with httpx.AsyncClient(timeout=120) as http:
        card = await A2ACardResolver(http, server_url).get_agent_card()
        client = A2AClient(http, agent_card=card, url=server_url)

        msg = create_text_message_object(content=user_text)
        if context_id:
            msg.context_id = context_id

        request = SendStreamingMessageRequest(
            id=str(uuid.uuid4()),
            params=MessageSendParams(message=msg),
        )

        chunks: list[str] = []
        returned_context_id = context_id
        input_required = False

        async for event in client.send_message_streaming(request):
            result = getattr(event.root, "result", None)
            if result is None:
                continue
            if hasattr(result, "context_id") and result.context_id:
                returned_context_id = result.context_id
            if isinstance(result, Message):
                text = _text_from_message(result)
                if text:
                    chunks.append(text)
            elif isinstance(result, Task):
                if result.status.state == TaskState.input_required:
                    input_required = True
                text = _text_from_message(result.status.message)
                if text:
                    chunks.append(text)
            elif isinstance(result, TaskStatusUpdateEvent):
                if result.status.state == TaskState.input_required:
                    input_required = True
                text = _text_from_message(result.status.message)
                if text:
                    chunks.append(text)

        return "\n\n".join(chunks), returned_context_id, input_required


def send_message_a2a(
    user_text: str,
    context_id: str | None,
    server_url: str,
) -> tuple[str, str | None, bool]:
    return asyncio.run(_send_a2a_async(user_text, context_id, server_url))


# ---------------------------------------------------------------------------
# Agent Runtime helpers
# ---------------------------------------------------------------------------


def _get_or_create_agent_runtime_session(resource_name: str, user_id: str) -> str:
    """Return an existing session_id or create a new one."""
    import vertexai
    from vertexai import agent_engines

    project, location = _parse_resource_name(resource_name)
    vertexai.init(project=project, location=location)
    agent = agent_engines.get(resource_name)

    session_key = f"ar_session_{resource_name}"
    if session_key not in st.session_state or not st.session_state[session_key]:
        session = agent.create_session(user_id=user_id)
        st.session_state[session_key] = session["id"]

    return st.session_state[session_key]


def _parse_resource_name(resource_name: str) -> tuple[str, str]:
    """Extract project and location from a resource name."""
    parts = resource_name.split("/")
    project = parts[1] if len(parts) > 1 else "unknown"
    location = parts[3] if len(parts) > 3 else "us-central1"
    return project, location


def send_message_agent_runtime(
    user_text: str,
    resource_name: str,
) -> tuple[str, bool]:
    """Send a message to Agent Runtime and return (response_text, input_required)."""
    import vertexai
    from vertexai import agent_engines

    project, location = _parse_resource_name(resource_name)
    vertexai.init(project=project, location=location)
    agent = agent_engines.get(resource_name)

    session_id = _get_or_create_agent_runtime_session(resource_name, "demo_user")

    chunks: list[str] = []
    input_required = False

    for event in agent.stream_query(
        user_id="demo_user",
        session_id=session_id,
        message=user_text,
    ):
        if not isinstance(event, dict):
            continue
        content = event.get("content", {})
        parts = content.get("parts", [])
        for part in parts:
            text = part.get("text", "")
            if text:
                chunks.append(text)

        # Detect HITL pause: agent requests tool confirmation
        actions = event.get("actions", {})
        if actions.get("requested_tool_confirmations"):
            input_required = True

    return "\n\n".join(chunks), input_required


# ---------------------------------------------------------------------------
# Streamlit page
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Bid Manager Agent",
    page_icon="🏢",
    layout="centered",
)

st.title("🏢 Bid Manager Agent")
st.caption("Demo A2A · Pota! L'Agentic AI · Brescia 2026")

# Sidebar
with st.sidebar:
    st.header("Modalità")
    mode = st.radio(
        "Backend",
        ["Local A2A", "Agent Runtime"],
        help="Local A2A: richiede il server uvicorn locale.\nAgent Runtime: usa il deployment su Vertex AI.",
    )

    st.markdown("---")

    if mode == "Local A2A":
        server_url = st.text_input("A2A Server URL", value=_DEFAULT_A2A_SERVER)
        st.markdown(
            "**Avviare prima:**\n"
            "```bash\n"
            "uv run uvicorn \\\n"
            "  streamlit_app.a2a_server:server \\\n"
            "  --port 9090\n"
            "```"
        )
    else:
        agent_resource = st.text_input(
            "Agent Runtime resource name",
            value=_DEFAULT_AGENT_RUNTIME,
            help="Format: projects/{proj}/locations/{loc}/reasoningEngines/{id}",
        )
        project_id, location_id = _parse_resource_name(agent_resource)
        engine_id = agent_resource.split("/")[-1]
        st.markdown(
            f"**Console:**\n"
            f"[Apri playground]"
            f"(https://console.cloud.google.com/vertex-ai/agents/agent-engines/locations/{location_id}/agent-engines/{engine_id}/playground?project={project_id})"
        )

    st.markdown("---")
    if st.button("🔄 Nuova conversazione", use_container_width=True):
        st.session_state.messages = []
        st.session_state.context_id = None
        # Clear Agent Runtime session
        for key in list(st.session_state.keys()):
            if key.startswith("ar_session_"):
                del st.session_state[key]
        st.rerun()

    st.markdown("---")
    st.markdown(
        "**Flusso demo:**\n"
        "1. Incolla l'URL di un bando\n"
        "2. L'agente legge il bando e chiama il Tender Analyst\n"
        "3. Risposta **Go** o **No-Go** per la decisione HITL\n"
        "4. Con Go → crea il workspace"
    )

# Session state init
if "messages" not in st.session_state:
    st.session_state.messages = []
if "context_id" not in st.session_state:
    st.session_state.context_id = None

# Render conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input(
    "Es: Analizza questo bando → https://sardegnacat.regione.sardegna.it/..."
):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("L'agente sta lavorando..."):
            try:
                if mode == "Local A2A":
                    response_text, new_ctx, input_required = send_message_a2a(
                        prompt, st.session_state.context_id, server_url
                    )
                    st.session_state.context_id = new_ctx
                else:
                    response_text, input_required = send_message_agent_runtime(
                        prompt, agent_resource
                    )
            except Exception as exc:
                if mode == "Local A2A":
                    response_text = (
                        f"❌ Errore di connessione: {exc}\n\n"
                        f"Verifica che il server A2A sia in esecuzione su `{server_url}`."
                    )
                else:
                    response_text = f"❌ Errore Agent Runtime: {exc}"
                input_required = False

        if response_text:
            st.markdown(response_text)
        if input_required:
            st.info(
                "⏳ L'agente attende la tua decisione.\n\n"
                "Rispondi **Go** per procedere o **No-Go** per chiudere la pratica."
            )

    if response_text:
        st.session_state.messages.append(
            {"role": "assistant", "content": response_text}
        )

    st.rerun()
