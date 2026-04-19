from __future__ import annotations

import logging
import os
import re

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from agents.prompts import (
    FALLBACK_REPLY,
    KNOWLEDGE_EXCERPT_MAX_REPLY,
    KNOWLEDGE_EXCERPT_MAX_THOUGHT,
    OFFLINE_THOUGHT,
    build_reply_user_prompt,
    build_thought_user_prompt,
)
from core.config import REPO_ROOT
from utils.load_data import KNOWLEDGE_BASE

_env_file = REPO_ROOT / ".env"
if _env_file.is_file():
    load_dotenv(_env_file)


def _make_llm():
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        return None
    return ChatGroq(api_key=key, model="llama-3.1-8b-instant", temperature=0)


llm = _make_llm()
_LOG = logging.getLogger("shopwave.agent")


def parse_confidence_from_llm_lines(lines: list[str], default: float = 0.75) -> float:
    if not lines:
        return default
    num_in_01 = re.compile(r"(?<![0-9.])(1(?:\.0+)?|0?\.\d+)(?![0-9.])")
    pct = re.compile(r"(?<!\d)(\d{1,3})\s*%")
    for ln in reversed(lines):
        t = ln.strip().replace(chr(0xA0), " ").replace(",", ".")
        m_pct = pct.search(t.replace(" ", ""))
        if m_pct:
            try:
                v = int(m_pct.group(1))
                if 0 <= v <= 100:
                    x = v / 100.0
                    if 0.0 <= x <= 1.0:
                        return x
            except ValueError:
                pass
        compact = re.sub(r"\s+", "", t)
        for m in num_in_01.finditer(compact):
            try:
                v = float(m.group(1))
                if 0.0 <= v <= 1.0:
                    return v
            except ValueError:
                continue
    return default


def generate_reply_message(state: dict) -> str:
    ctx = (state.get("ticket") or "").strip()
    hist = "\n".join(state.get("messages") or [])
    oid = (state.get("order_id") or "").strip().upper()
    excerpt = KNOWLEDGE_BASE[:KNOWLEDGE_EXCERPT_MAX_REPLY]
    if llm is None or os.getenv("SHOPWAVE_OFFLINE"):
        tail = f" Regarding order {oid}, we have applied the outcome from our tools above." if oid else " We have applied the outcome from our tools above."
        return ("Thanks for contacting ShopWave." + tail)[:2000]
    prompt = build_reply_user_prompt(ctx, oid, hist, excerpt)
    try:
        resp = llm.invoke(prompt)
        body = (getattr(resp, "content", None) or str(resp)).strip()
        if body:
            return body[:2000]
    except Exception as e:
        _LOG.warning("ChatGroq reply generation failed: %s", e, exc_info=True)
    return FALLBACK_REPLY


def llm_thought_confidence(next_action: str, ctx: str, history: str) -> tuple[str, float]:
    if llm is None or os.getenv("SHOPWAVE_OFFLINE"):
        return OFFLINE_THOUGHT.format(action=next_action), 0.86
    excerpt = KNOWLEDGE_BASE[:KNOWLEDGE_EXCERPT_MAX_THOUGHT]
    prompt = build_thought_user_prompt(next_action, ctx, history, excerpt)
    try:
        resp = llm.invoke(prompt)
        text = (getattr(resp, "content", None) or str(resp) or "").strip()
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        thought = lines[0] if lines else "Proceed with tool."
        conf = parse_confidence_from_llm_lines(lines, default=0.75)
        return thought, conf
    except Exception as e:
        _LOG.warning("ChatGroq invoke failed in llm_thought_confidence: %s", e, exc_info=True)
        return "LLM unavailable; using default confidence.", 0.72
