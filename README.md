# 🤖 POTA L'Agentic AI: Analisi Bando di Gara con Google ADK

Benvenuti in questo progetto dimostrativo realizzato per il meetup di Brescia Pota! L'Agentic AI. 
Lo scopo di questo repository è mostrare come passare dal semplice *prompting* alla costruzione di **Agenti AI** completi, capaci di collaborare tra loro e interagire con il mondo reale e con l'uomo.

> **HUMANS · TECHNOLOGY · PROGRESS**

---

## 🎯 Il Caso d'Uso: Analisi Strategica di Bandi Pubblici
Leggere e valutare un bando di gara pubblico è un'attività ad alto carico cognitivo e rischio legale. Un errore nell'identificare una penale o un requisito di fatturato può costare caro all'azienda.

Abbiamo costruito un sistema agentico che:
1.  **Estrae** i dati chiave in secondi.
2.  **Analizza** legalmente il documento tramite uno specialista AI.
3.  **Coinvolge** l'essere umano per le decisioni critiche (*Human-in-the-Loop*).
4.  **Agisce** nel mondo reale configurando un'area di lavoro.

---

## 🏗️ Architettura della Soluzione

Il progetto sfrutta il protocollo **A2A (Agent-to-Agent)** e **A2UI (Agent-to-UI)** del [Google Agent Development Kit (ADK)](https://github.com/google/adk).

### Gli Agenti
-   **Bid Manager (Root Agent):** L'orchestratore. Gestisce l'interfaccia utente, coordina il flusso e possiede la visione d'insieme del processo.
-   **Tender Analyst (Sub-Agent):** Lo specialista. Conosce il Codice degli Appalti ed è addestrato a trovare "trappole" legali e requisiti tecnici stringenti.

### Gli Strumenti (Tools & Skills)
-   `read_tender`: Simula il caricamento e il parsing dei documenti (Grounding).
-   `ask_bid_decision`: Implementa il blocco **HITL**. L'agente non procede finché un umano non dice "Go".
-   `setup_bid_workspace`: Una **Skill** che simula l'automazione di processi (es. creazione cartelle Drive).

---

## 🚀 Come Iniziare

### Prerequisiti
-   Python 3.12+
-   [uv](https://docs.astral.sh/uv/) installato.
-   `google-agents-cli` installato: `uv tool install google-agents-cli`.
-   Accesso a un progetto Google Cloud con Vertex AI abilitato (o API Key di AI Studio).

### 1. Installazione
Clona il repository ed entra nella cartella:
```bash
cd bid-analysis-agent
agents-cli install
```

### 2. Configurazione
Assicurati di aver configurato le credenziali Google Cloud:
```bash
gcloud auth application-default login
```
L'agente utilizzerà automaticamente il tuo progetto di default. Se necessario, puoi creare un file `.env` basato sui log di sistema.

### 3. Esecuzione Demo
Avvia l'interfaccia grafica per interagire con l'agente:
```bash
agents-cli playground
```
Accedi all'URL fornito (solitamente `http://localhost:8080`) e prova a inviare:
> *"Analizza questo bando: https://sardegnacat.regione.sardegna.it/portalegare/index.php/bandi?id=187960"*

### 4. Evaluation (Qualità)
Per verificare che l'agente si comporti sempre secondo le regole (es. che non scavalchi mai l'approvazione umana):
```bash
agents-cli eval run
```

---

## 📚 Documentazione Ufficiale
Per approfondire i concetti mostrati in questa demo, consulta le risorse ufficiali:
-   [Google ADK Documentation](https://google.github.io/adk-docs/)
-   [A2A Protocol Overview](https://google.github.io/adk-docs/agents/multi-agent/)
-   [Evaluation Framework Guide](https://google.github.io/adk-docs/evaluate/)

---

## 💡 Perchè ADK?
A differenza di semplici script basati su LLM, ADK offre:
1.  **Stato Persistente:** L'agente ricorda le decisioni prese.
2.  **Governance:** Il pattern HITL è nativo e robusto.
3.  **Testabilità:** Puoi misurare la "traiettoria" del ragionamento AI, non solo la risposta finale.

---

Creato con ❤️  da [Matteo](https://matteo.gazzurelli.com)..
*"Rendere accessibile ciò che è complesso."*
