# ruff: noqa
# Copyright 2026 Google LLC

import io
import os

import google.auth
import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import LongRunningFunctionTool, AgentTool, ToolContext
from google.adk.tools.base_tool import BaseTool
from google.genai import types


def configure_vertex_ai() -> None:
    """Configure environment for Vertex AI. Call once at app startup."""
    _, project_id = google.auth.default()
    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
    os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


# --- Tools ---


_MAX_CONTENT_CHARS = 8_000
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BidAnalysisAgent/1.0)"}


def read_tender(url: str) -> str:
    """Reads and extracts text from a tender URL (HTML page or PDF).

    Fetches the document at the given URL, detects whether it is HTML or PDF,
    and returns the plain-text content (truncated to avoid model context limits).

    Args:
        url: The HTTP/HTTPS URL of the tender page or PDF document.

    Returns:
        The extracted text content, at most 8 000 characters.
    """
    try:
        with httpx.Client(follow_redirects=True, timeout=30, verify=False) as client:
            response = client.get(url, headers=_HEADERS)
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        return f"Errore nel recupero del bando: {e.response.status_code} — l'URL potrebbe essere scaduto o non valido."
    except httpx.RequestError as e:
        return f"Errore di rete nel recupero del bando: {e}"

    content_type = response.headers.get("content-type", "")

    if "pdf" in content_type or url.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(response.content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)

    if len(text) > _MAX_CONTENT_CHARS:
        text = text[:_MAX_CONTENT_CHARS] + "\n[... contenuto troncato ...]"

    return text


def ask_bid_decision(message: str, tool_context: ToolContext) -> dict:
    """Requests a Go/No-Go decision from the Bid Manager (Human).

    Calling this tool will pause execution until the manager responds with 'Go' or 'No-Go'.

    Args:
        message: A summary of the analysis and the question for the manager.
    """
    tool_context.state["hitl_requested"] = True
    return {"status": "pending", "message": message}


async def guard_workspace_tool(
    tool: BaseTool, args: dict, tool_context: ToolContext
) -> dict | None:
    """Blocks setup_bid_workspace if ask_bid_decision was never called."""
    if tool.name == "setup_bid_workspace" and not tool_context.state.get(
        "hitl_requested"
    ):
        return {
            "error": "Impossibile procedere: richiedere prima l'approvazione Go/No-Go via 'ask_bid_decision'."
        }
    return None


def setup_bid_workspace(tender_id: str) -> str:
    """Simulates the creation of a shared Google Drive folder and workspace for the bid.

    Args:
        tender_id: The ID or CIG of the tender.
    """
    return f"✅ Workspace creato con successo per la gara {tender_id}. Cartella Drive: 'Gara_{tender_id}_Docs'"


# --- Agents ---

# Sub-Agent: The Specialist
tender_analyst = Agent(
    name="tender_analyst",
    model=Gemini(
        model="gemini-3-flash-preview",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    description="Esperto legale e tecnico di bandi di gara pubblici italiani.",
    instruction="""Sei un Analista di Gara esperto.
    Il tuo compito è analizzare il testo di un bando e identificare:
    1. Requisiti di partecipazione critici (certificazioni, fatturato).
    2. Rischi contrattuali (penali, clausole vessatorie).
    3. Punteggi tecnici.
    Sii sintetico e metti in guardia su eventuali criticità.""",
    output_key="analysis_result",
)

# Root Agent: The Orchestrator
root_agent = Agent(
    name="bid_manager",
    model=Gemini(
        model="gemini-3-flash-preview",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    description="Agente coordinatore per la valutazione delle opportunità di gara.",
    instruction="""Sei il Bid Manager. Il tuo obiettivo è coordinare la valutazione di un bando.
    Segui rigorosamente questo processo:
    1. Usa 'read_tender' per ottenere le informazioni base.
    2. Consulta il 'tender_analyst' per un'analisi approfondita dei requisiti e dei rischi.
    3. Presenta un riassunto all'utente e usa 'ask_bid_decision' (HITL) per ottenere l'approvazione.
    4. SOLO SE l'utente risponde 'Go', usa 'setup_bid_workspace' per terminare il processo.
    Se l'utente risponde 'No-Go', saluta e chiudi la pratica.""",
    tools=[
        read_tender,
        LongRunningFunctionTool(func=ask_bid_decision),
        setup_bid_workspace,
        AgentTool(tender_analyst),
    ],
    before_tool_callback=guard_workspace_tool,
)

app = App(
    root_agent=root_agent,
    name="app",
)
