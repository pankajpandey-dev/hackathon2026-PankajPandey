"""LLM prompt templates for the support agent."""

from __future__ import annotations

KNOWLEDGE_EXCERPT_MAX_REPLY = 2200
KNOWLEDGE_EXCERPT_MAX_THOUGHT = 2800


def build_reply_user_prompt(ctx: str, oid: str, hist: str, knowledge_excerpt: str) -> str:
    return (
        "You are ShopWave customer support. Write a concise, professional email body in plain text "
        "(max ~1800 characters). Address the customer by context; use tool results below; do not invent "
        "policies beyond the knowledge excerpt. If a refund was issued, note typical processing time; "
        "if not eligible, explain briefly and kindly.\n\n"
        f"Knowledge excerpt:\n{knowledge_excerpt}\n\n"
        f"Order id (if known): {oid or '(none)'}\n\n"
        f"Customer message:\n{ctx}\n\n"
        f"Tool / system log:\n{hist[:5000]}"
    )


def build_thought_user_prompt(next_action: str, ctx: str, history: str, knowledge_excerpt: str) -> str:
    return (
        f"You are a ShopWave L1 routing analyst. One tool will run next: {next_action}."
        f"Knowledge excerpt:{knowledge_excerpt}"
        f"Ticket:{ctx}"
        f"Tool log so far:{history or '(none)'}"
        "Respond with EXACTLY two lines:"
        "Line 1: One short sentence: your reasoning (why this tool is appropriate now)."
        "Line 2: A single number from 0.0 to 1.0 - your confidence that this is the correct next step."
    )


OFFLINE_THOUGHT = "Pipeline requires `{action}` per policy and ticket state."

FALLBACK_REPLY = (
    "Thanks for contacting ShopWave. We've reviewed your case and will follow up with next steps."
)
