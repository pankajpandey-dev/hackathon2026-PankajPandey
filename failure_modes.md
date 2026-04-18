# Failure Mode Analysis — ShopWave Agent

## Overview

The ShopWave agent is designed to  **never crash silently** . Every failure is caught, logged to the audit trail, and either retried or escalated to a human agent with full context. Below are the documented failure scenarios and how the system responds to each.

---

## Failure Mode 1: Tool Timeout / Malformed Response

### What happens

A tool call (e.g. `get_order`, `check_refund_eligibility`) simulates a network timeout or returns a malformed payload. This is injected randomly at a 12% base rate via `_simulate_tool_chaos()`.

### How the system responds

**Step 1 — Retry with exponential backoff:**

```
Attempt 1 → fails → wait 0.15s
Attempt 2 → fails → wait 0.30s + jitter
Attempt 3 → fails → wait 0.60s + jitter
Attempt 4 → raise ToolRetriesExhausted
```

**Step 2 — If all retries exhausted:**

* The `act()` node catches `ToolRetriesExhausted`
* Calls `escalate(ticket_id, summary, priority="high")` with full context
* Appends a `tool_error: true` step to the audit log
* Sets `final_decision = "escalated_tool_failure"`
* Agent exits cleanly — ticket is never silently lost

**Logged audit entry:**

```json
{
  "phase": "act",
  "action": "get_order",
  "output": { "error": "simulated tool timeout" },
  "tool_error": true
}
```

**Configuration:** `SHOPWAVE_TOOL_FAILURE_RATE=0.12` (adjustable in `.env`)

---

## Failure Mode 2: Missing Order ID — Unresolvable Ticket

### What happens

A ticket arrives with no `ORD-*` pattern in the body and no customer email address. The agent cannot identify which order to act on.

### Resolution chain attempted

1. `extract_order_id()` scans ticket body — not found
2. `extract_order_id()` scans tool message log — not found
3. Email lookup via `latest_order_id_for_email()` — no email provided
4. `pipeline_next_step()` returns `None`

### How the system responds

* `think()` detects `nxt is None`
* Calls `escalate(ticket_id, summary, priority="high")`
* Summary includes: ticket body preview (400 chars), actions attempted so far
* `final_decision = "escalated_missing_order_id"`
* Audit step logged with `confidence: 0.2` to signal low-certainty escalation

**Why this is correct:** Attempting to guess an order ID would risk issuing a refund against the wrong order. Escalating is the safe default.

---

## Failure Mode 3: Low LLM Confidence

### What happens

The LLM (Groq LLaMA 3.1) returns a confidence score below the threshold (default `0.6`) when reasoning about the next pipeline step. This can occur when the ticket is ambiguous, contradictory, or outside normal patterns.

### How the system responds

* `think()` calls `_llm_thought_confidence(next_action, ctx, history)`
* Parses confidence score from LLM response (handles %, decimal, EU comma formats)
* If `confidence < CONFIDENCE_THRESHOLD`:
  * Calls `escalate(ticket_id, summary, priority="medium")`
  * Summary includes: ticket text (600 chars), actions taken, confidence value
  * `final_decision = "escalated_low_confidence"`

**Threshold configuration:** `SHOPWAVE_CONFIDENCE_THRESHOLD=0.6` in `.env`

**Why this matters:** An agent that acts despite low confidence will make wrong decisions at scale. Escalating uncertain cases is a feature, not a bug.

---

## Failure Mode 4: Infinite Loop / Runaway Agent

### What happens

Due to a bug or unexpected state, the agent's `think/act` loop fails to reach `"done"` and keeps cycling.

### How the system responds

* `think_cycle` counter increments on every call to `think()`
* At `think_cycle > 28`, the agent triggers a safety cap:
  * Calls `escalate(ticket_id, summary, priority="medium")`
  * Summary includes: ticket ID, actions taken so far, reason `max_think_cycles`
  * `final_decision = "escalated_safety_cap"`
  * LangGraph `recursion_limit=64` provides a second layer of protection

**Why 28?** The full happy path is ~8 steps (think+act × 8 = 16 cycles). 28 gives 1.75× headroom for retries before capping.

---

## Failure Mode 5: LLM Unavailable (No API Key / Network Down)

### What happens

`GROQ_API_KEY` is missing, expired, or Groq's API is unreachable at runtime.

### How the system responds

* `_make_llm()` returns `None` if no key is set
* All LLM-dependent functions check `if llm is None or os.getenv("SHOPWAVE_OFFLINE")`
* **`_llm_thought_confidence()`** falls back to: `"Pipeline requires {action} per policy and ticket state."` with confidence `0.86`
* **`_generate_reply_message()`** falls back to a static professional template
* The full pipeline still executes using rule-based logic only
* No crash, no silent failure

**Effect:** Agent runs in "offline mode" — slightly less nuanced replies, but all tool calls, eligibility checks, and refunds still execute correctly.

---

## Failure Mode 6: Corrupt Audit File

### What happens

The `audit_logs/<ticket_id>.json` file is corrupt (e.g. partial write, disk issue).

### How the system responds

* `_load_ticket_audit_file()` catches `json.JSONDecodeError`
* Returns a fresh empty structure with `"corrupted_previous": true` flag
* Agent continues normally; new run data is written cleanly
* Previous corrupt data is not silently overwritten — the flag is preserved for investigation
* Writes use atomic `tmp → replace` pattern to prevent mid-write corruption

---

## Summary Table

| # | Failure                  | Detection                      | Response                             | Ticket Lost? |
| - | ------------------------ | ------------------------------ | ------------------------------------ | ------------ |
| 1 | Tool timeout / malformed | Exception catch                | Retry × 3, then escalate HIGH       | Never        |
| 2 | Missing order ID         | `pipeline_next_step → None` | Escalate HIGH                        | Never        |
| 3 | Low LLM confidence       | Confidence score < 0.6         | Escalate MEDIUM                      | Never        |
| 4 | Infinite loop            | `think_cycle > 28`           | Escalate MEDIUM + recursion_limit=64 | Never        |
| 5 | LLM unavailable          | `llm is None`                | Rule-based offline fallback          | Never        |
| 6 | Corrupt audit file       | `JSONDecodeError`            | Fresh file + corruption flag         | Never        |
