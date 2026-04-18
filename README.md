
# ShopWave Autonomous Support Agent

### Agentic AI Hackathon 2026 — Ksolves × En(AI)bling

An autonomous customer support resolution agent built with  **LangGraph + Groq (LLaMA 3.1)** . Resolves ShopWave support tickets end-to-end: classifies, looks up orders, checks refund eligibility, issues refunds, and replies to customers — all without human intervention.

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/<your-username>/hackathon2026-<your-name>.git
cd hackathon2026-<your-name>

# 2. Install dependencies
pip install "langgraph>=0.2" "langchain-core>=1.2.2,<3" "langchain-groq>=1.0.0" python-dotenv

# 3. Set your Groq API key
cp .env.example .env
# Edit .env and add: GROQ_API_KEY=your_key_here

# 4. Run the agent (processes all 20 tickets in parallel)
jupyter nbconvert --to notebook --execute shopwave_agent.ipynb

# OR run directly in Jupyter
jupyter notebook shopwave_agent.ipynb
```

> **Offline mode** (no API key needed): Set `SHOPWAVE_OFFLINE=1` in your `.env`. The agent runs fully with rule-based fallbacks.

---

## Tech Stack

| Layer         | Technology                                         |
| ------------- | -------------------------------------------------- |
| Orchestration | LangGraph 0.2+ (StateGraph, think/act loop)        |
| LLM           | Groq — LLaMA 3.1 8B Instant                       |
| Language      | Python 3.11+                                       |
| Concurrency   | `ThreadPoolExecutor`(parallel ticket processing) |
| Audit Logging | Per-ticket JSON under `audit_logs/`              |
| Data          | JSON files under `data/`                         |

---

## Project Structure

```
hackathon2026-<your-name>/
├── shopwave_agent.ipynb     # Main agent notebook (entry point)
├── data/
│   ├── tickets.json         # 20 mock support tickets
│   ├── orders.json          # Order records
│   ├── customers.json       # Customer profiles + tiers
│   ├── products.json        # Product catalogue
│   └── knowledge-base.md    # Policy & FAQ document
├── audit_logs/
│   ├── TKT-001.json         # Per-ticket audit (auto-generated)
│   ├── ...
│   └── escalations.json     # All escalation records
├── architecture.pdf         # Agent architecture diagram
├── failure_modes.md         # Failure scenarios + responses
├── README.md                # This file
└── .env.example             # API key template
```

---

## Agent Pipeline

Each ticket flows through this reasoning chain (minimum 7 tool calls):

```
classify_ticket → search_knowledge_base → get_customer →
get_order → get_product → check_refund_eligibility →
issue_refund (if eligible) → send_reply
```

Every step is logged with: reasoning thought, confidence score, tool input, tool output, and timestamp.

---

## Tool Inventory

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

## Fault Tolerance

* **12% simulated failure rate** on every tool call (configurable via `SHOPWAVE_TOOL_FAILURE_RATE`)
* **Exponential backoff** retry: up to 3 retries, base delay 0.15s, doubles each attempt
* **ToolTimeout** and **ToolMalformedResponse** are caught and retried
* After retries exhausted: ticket is **escalated** with full context, never silently dropped
* Safety cap at **28 think cycles** to prevent infinite loops

---

## Escalation Triggers

| Trigger                       | Priority   |
| ----------------------------- | ---------- |
| Missing order ID and no email | `high`   |
| Confidence score < 0.6        | `medium` |
| Tool retries exhausted        | `high`   |
| Max think cycles (28) reached | `medium` |

---

## Configuration

All tuneable via `.env`:

```env
GROQ_API_KEY=your_groq_key
SHOPWAVE_CONFIDENCE_THRESHOLD=0.6   # Escalate below this
SHOPWAVE_TOOL_FAILURE_RATE=0.12     # Simulated chaos rate (0–1)
SHOPWAVE_OFFLINE=                   # Set to 1 for offline/no-LLM mode
```

---

## Audit Output

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

## Running All 20 Tickets

```python
# Parallel (recommended)
all_results = run_all_tickets(parallel=True, max_workers=6)

# Sequential
all_results = run_all_tickets(parallel=False)
```

---

## Notes

* No API keys are hardcoded anywhere. All secrets are loaded from `.env` via `python-dotenv`.
* The agent degrades gracefully when Groq is unavailable — rule-based fallbacks keep it running.
* `issue_refund` is only called after `check_refund_eligibility` confirms `eligible: True`.
