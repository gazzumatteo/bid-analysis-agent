# Copyright 2026 Google LLC
"""Streamlit chat UI for the Bid Analysis Agent — A2A demo client.

Usage:
    # Terminal 1 — A2A server
    uv run uvicorn streamlit_app.a2a_server:server --port 9090

    # Terminal 2 — Streamlit UI
    uv run streamlit run streamlit_app/chat.py
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

_DEFAULT_SERVER = "http://localhost:9090/a2a/app"


# ---------------------------------------------------------------------------
# A2A helpers
# ---------------------------------------------------------------------------


def _text_from_message(message: Message | None) -> str:
    if message is None:
        return ""
    return "".join(
        part.root.text for part in message.parts if hasattr(part.root, "text")
    )


async def _send_async(
    user_text: str,
    context_id: str | None,
    server_url: str,
) -> tuple[str, str | None, bool]:
    """Send one turn to the A2A agent and collect the streamed response.

    Returns:
        (response_text, context_id, input_required)
    """
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


def send_message(
    user_text: str,
    context_id: str | None,
    server_url: str,
) -> tuple[str, str | None, bool]:
    return asyncio.run(_send_async(user_text, context_id, server_url))


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
    st.header("Configurazione")
    server_url = st.text_input("A2A Server URL", value=_DEFAULT_SERVER)

    st.markdown("---")
    if st.button("🔄 Nuova conversazione", use_container_width=True):
        st.session_state.messages = []
        st.session_state.context_id = None
        st.rerun()

    st.markdown("---")
    st.markdown(
        "**Come avviare i server:**\n\n"
        "```bash\n"
        "# Terminale 1 — agente\n"
        "uv run uvicorn \\\n"
        "  streamlit_app.a2a_server:server \\\n"
        "  --port 9090\n\n"
        "# Terminale 2 — questa UI\n"
        "uv run streamlit run \\\n"
        "  streamlit_app/chat.py\n"
        "```"
    )
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
                response_text, new_ctx, input_required = send_message(
                    prompt, st.session_state.context_id, server_url
                )
            except Exception as exc:
                response_text = f"❌ Errore di connessione: {exc}\n\nVerifica che il server A2A sia in esecuzione su `{server_url}`."
                new_ctx = st.session_state.context_id
                input_required = False

        if response_text:
            st.markdown(response_text)
        if input_required:
            st.info(
                "⏳ L'agente attende la tua decisione.\n\n"
                "Rispondi **Go** per procedere o **No-Go** per chiudere la pratica."
            )

    st.session_state.context_id = new_ctx
    if response_text:
        st.session_state.messages.append(
            {"role": "assistant", "content": response_text}
        )

    st.rerun()
