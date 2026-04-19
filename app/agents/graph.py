"""Compiled LangGraph for one ticket."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agents.nodes import act, should_continue, think
from agents.state import AgentState

builder = StateGraph(AgentState)
builder.add_node("think", think)
builder.add_node("act", act)
builder.add_edge(START, "think")
builder.add_conditional_edges("think", should_continue, {"continue": "act", "end": END})
builder.add_edge("act", "think")
graph = builder.compile()
