# DESIGN_SPEC: Bid Analysis Agent

## Project Overview
An AI agent system designed for the tender analysis. It uses a multi-agent architecture (A2A) to separate general orchestration from specialized document analysis.

## User Persona
A Bid Manager or Business Developer who needs to quickly evaluate if a public tender is worth pursuing based on requirements and deadlines.

## Requirements
- **Input:** URL of a tender page or a PDF document.
- **Output:** Structured summary (CIG, Deadline, Amount) and a detailed compliance report.
- **Workflow:**
    1. **Extraction:** Identify key tender metadata.
    2. **Deep Analysis (A2A):** Analyze technical and administrative requirements.
    3. **Human-in-the-Loop (HITL):** Request a "Go/No-Go" decision from the user.
    4. **Action (Skill):** Finalize by "setting up a workspace" if the decision is "Go".

## Architecture

### Agents
1. **Bid Manager (Root Agent)**
   - **Role:** Orchestrator and UI interface.
   - **Model:** `gemini-3-flash-preview`
   - **Tools:** `read_tender`, `ask_bid_decision`, `setup_bid_workspace`.
   - **A2A Interaction:** Consults the `tender_analyst` for requirement verification.

2. **Tender Analyst (Sub-Agent)**
   - **Role:** Document specialist.
   - **Model:** `gemini-3-flash-preview`
   - **Instruction:** Expert in Italian public procurement (Codice Appalti). Analyzes tender documents for risks and mandatory certifications.

### Tools
- `read_tender`: (Input: `url` or `file_path`) -> Returns text content.
- `ask_bid_decision`: (HITL) -> Asks user for "Go" or "No-Go".
- `setup_bid_workspace`: (Input: `tender_id`) -> Mock skill that simulates creating a project folder.

## Success Criteria (Evaluation)
- The agent must extract the correct deadline from the Sardegna CAT URL.
- The agent MUST call the `tender_analyst` before proposing a decision.
- The agent MUST NOT proceed to `setup_bid_workspace` without a "Go" decision via HITL.
