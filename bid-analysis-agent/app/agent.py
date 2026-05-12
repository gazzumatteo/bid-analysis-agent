# ruff: noqa
# Copyright 2026 Google LLC

import os
import google.auth
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import LongRunningFunctionTool, AgentTool, ToolContext
from google.genai import types

# Setup environment
_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

# --- Tools ---


def read_tender(url: str) -> str:
    """Reads and extracts text from a tender URL or PDF file.

    Args:
        url: The URL or file path of the tender document.

    Returns:
        The extracted text content from the tender.
    """
    # Mocking content for the Sardegna CAT example mentioned in the plan
    if "sardegnacat" in url.lower():
        return """
        BANDO DI GARA: Servizio di manutenzione impianti.
        CIG: Z123456789
        Scadenza: 20 Maggio 2026 ore 13:00
        Importo: € 150.000,00
        Requisiti: Certificazione ISO 9001 obbligatoria. Fatturato annuo minimo € 300.000,00.
        Penali: 1% per ogni giorno di ritardo.
        """
    return f"Contenuto generico per il bando: {url}. Si prega di analizzare i requisiti standard."


def ask_bid_decision(message: str, tool_context: ToolContext) -> dict:
    """Requests a Go/No-Go decision from the Bid Manager (Human).

    Calling this tool will pause execution until the manager responds with 'Go' or 'No-Go'.

    Args:
        message: A summary of the analysis and the question for the manager.
    """
    tool_context.state["hitl_requested"] = True
    return {"status": "pending", "message": message}


async def guard_workspace_tool(
    ctx: CallbackContext, tool_name: str, args: dict
) -> dict | None:
    """Blocks setup_bid_workspace if ask_bid_decision was never called."""
    if tool_name == "setup_bid_workspace" and not ctx.state.get("hitl_requested"):
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
