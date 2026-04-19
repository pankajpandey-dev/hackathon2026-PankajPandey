# ShopWave Autonomous Support Agent

### Agentic AI Hackathon 2026 — Ksolves × En(AI)bling

An autonomous customer support resolution agent built with **LangGraph + Groq (LLaMA 3.1)**. It resolves ShopWave support tickets end-to-end: classifies, looks up orders, checks refund eligibility, issues refunds, and replies to customers — without human intervention. The project includes a **web dashboard** and **REST API** to run batches, inspect audits, and view analytics.

**Live demo:** [https://shopwave-ree9.onrender.com/ui/](https://shopwave-ree9.onrender.com/ui/)
*(Hosted on [Render](https://render.com); free tier may cold-start after idle time.)*

---

## Quick start (local dashboard + API)

```bash
git clone https://github.com/pankajpandey-dev/hackathon2026-PankajPandey.git
cd hackathon2026-PankajPandey

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp sample.env .env
# Edit .env: set GROQ_API_KEY for Groq; optional SHOPWAVE_OFFLINE=1 for rule-based fallbacks without an API key.

cd app
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open **http://127.0.0.1:8000/** (redirects to `/ui/`). Use **Run All Tickets** on the dashboard, or call `POST /run` on the API.

> **Offline mode:** set `SHOPWAVE_OFFLINE=1` in `.env` so LLM steps use deterministic fallbacks (no Groq key required).

---

## Optional: Jupyter notebook

```bash
jupyter notebook notebooks/agent.ipynb
```

---

## Tech stack

| Layer         | Technology                                                               |
| ------------- | ------------------------------------------------------------------------ |
| Orchestration | LangGraph 0.2+ (StateGraph, think/act loop)                              |
| LLM           | Groq — LLaMA 3.1 8B Instant                                             |
| API           | FastAPI + Uvicorn                                                        |
| UI            | Static dashboard under `/ui` (tickets, audits, escalations, analytics) |
| Language      | Python 3.11+                                                             |
| Concurrency   | Parallel ticket runs (`ThreadPoolExecutor` / background jobs)          |
| Audit         | Per-ticket JSON under `audit_logs/` (generated at runtime)             |
| Data          | JSON +`knowledge-base.md` under `data/`                              |

---

## Project structure

```
hackathon2026-Pankajpandey/
├── app/                     # FastAPI app (PYTHONPATH = app/ when using Dockerfile)
│   ├── main.py              # App entry, mounts /ui static UI
│   ├── api/                 # REST routes (/run, /status, /tickets, …)
│   ├── agents/              # LangGraph pipeline, tools, LLM
│   ├── services/
│   └── core/config.py       # Repo paths (data/, audit_logs/)
├── frontend/static/         # Dashboard HTML/CSS/JS
├── data/                    # tickets, orders, customers, products, knowledge-base.md
├── audit_logs/              # Generated audits (gitignored); created empty in Docker
├── notebooks/agent.ipynb    # Notebook exploration (optional)
├── Dockerfile               # Production image (Uvicorn :8000)
├── render.yaml              # Render Blueprint (optional one-click deploy)
├── requirements.txt
├── sample.env               # Copy to .env for local secrets
├── architecture.pdf
├── failure_modes.md
└── README.md
```

---

## Agent pipeline

Each ticket flows through this reasoning chain (minimum 7 tool calls):

```
classify_ticket → search_knowledge_base → get_customer →
get_order → get_product → check_refund_eligibility →
issue_refund (if eligible) → send_reply
```

Every step is logged with: reasoning thought, confidence score, tool input, tool output, and timestamp.

---

## Tool inventory

| Tool                         | Type            | Description                               |
| ---------------------------- | --------------- | ----------------------------------------- |
| `classify_ticket`          | Read            | Urgency + category + resolvability triage |
| `search_knowledge_base`    | Read            | Chunked policy/FAQ semantic search        |
| `get_customer`             | Read            | Customer profile and tier lookup          |
| `get_order`                | Read            | Order status, amounts, deadlines          |
| `get_product`              | Read            | Product metadata, warranty, return window |
| `check_refund_eligibility` | Read            | Date-aware eligibility check              |
| `issue_refund`             | **Write** | Irreversible — gated behind eligibility  |
| `send_reply`               | **Write** | Customer-facing email reply               |
| `escalate`                 | **Write** | Routes to human with structured summary   |

---

## Fault tolerance

* **12% simulated failure rate** on every tool call (configurable via `SHOPWAVE_TOOL_FAILURE_RATE`)
* **Exponential backoff** retry: up to 3 retries, base delay 0.15s, doubles each attempt
* **ToolTimeout** and **ToolMalformedResponse** are caught and retried
* After retries exhausted: ticket is **escalated** with full context, never silently dropped
* Safety cap at **28 think cycles** to prevent infinite loops

---

## Escalation triggers

| Trigger                       | Priority   |
| ----------------------------- | ---------- |
| Missing order ID and no email | `high`   |
| Confidence score < 0.6        | `medium` |
| Tool retries exhausted        | `high`   |
| Max think cycles (28) reached | `medium` |

---

## Configuration

Tune via `.env` (start from `sample.env`):

```env
GROQ_API_KEY=your_groq_key
SHOPWAVE_CONFIDENCE_THRESHOLD=0.6   # Escalate below this
SHOPWAVE_TOOL_FAILURE_RATE=0.12     # Simulated chaos rate (0–1)
SHOPWAVE_OFFLINE=                   # Set to 1 for offline/no-LLM mode
```

On **Render**, set `GROQ_API_KEY` (and any other variables) in the service **Environment** tab. The app reads process environment variables; a `.env` file is not required in production.

---

## Audit output

Every ticket produces `audit_logs/<ticket_id>.json`:

```json
{
  "version": 1,
  "ticket_id": "TKT-001",
  "runs": [{
    "run_id": "uuid",
    "started_at": "2026-04-19T...",
    "steps": [
      {
        "phase": "think",
        "thought": "classify_ticket needed as first triage step",
        "action": "classify_ticket",
        "confidence": 0.86,
        "timestamp": "2026-04-19T..."
      }
    ],
    "final_decision": "replied_and_closed",
    "actions_taken": ["classify_ticket", "search_knowledge_base", "..."],
    "escalated": false,
    "finished_at": "2026-04-19T..."
  }]
}
```

---

## Running all 20 tickets

* **Dashboard:** open `/ui/` and use **Run All Tickets**.
* **API:** `POST /run` starts the same parallel batch (OpenAPI docs at `/docs` when running locally).

From Python (e.g. notebook with `app` on `PYTHONPATH`, or `cd app` first):

```python
from agents.runner import run_all_tickets

all_results = run_all_tickets(parallel=True, max_workers=6)
# all_results = run_all_tickets(parallel=False)
```

---
