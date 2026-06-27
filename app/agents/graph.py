"""
Starter LangGraph agent for YouTube Shorts content creation.

Defines a three-node ``StateGraph`` that moves through:

    research  →  script  →  review

Each node receives the shared ``AgentState`` and returns a partial
update dict.  The ``create_agent_graph()`` factory compiles the graph
into a runnable that can be invoked with::

    graph = create_agent_graph()
    result = await graph.ainvoke(initial_state)
"""

from __future__ import annotations

import logging
from typing import Any, TypedDict

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph import END, StateGraph

logger = logging.getLogger(__name__)


# ── Agent state schema ───────────────────────────────────────────────


class AgentState(TypedDict, total=False):
    """Shared state that flows through every node in the graph.

    Attributes:
        messages: Conversation / reasoning trace.
        current_step: Name of the node currently executing.
        metadata: Arbitrary bag of run-level metadata (topic, style, etc.).
        research_results: Output produced by the research node.
        script_draft: Output produced by the script node.
        review_feedback: Output produced by the review node.
    """

    messages: list[BaseMessage]
    current_step: str
    metadata: dict[str, Any]
    research_results: dict[str, Any]
    script_draft: str
    review_feedback: dict[str, Any]


# ── Node implementations ─────────────────────────────────────────────


async def research_node(state: AgentState) -> dict:
    """Gather trending topics, keywords, and reference material.

    TODO: Integrate real YouTube / Google Trends / SerpAPI calls.
    """
    logger.info("research_node — starting topic research …")

    topic = state.get("metadata", {}).get("topic", "AI technology")
    research_results = {
        "topic": topic,
        "trending_keywords": [
            f"{topic} explained",
            f"{topic} in 60 seconds",
            f"{topic} for beginners",
        ],
        "reference_urls": [],
        "competitor_analysis": [],
    }

    return {
        "current_step": "research",
        "research_results": research_results,
        "messages": state.get("messages", [])
        + [AIMessage(content=f"Research complete for topic: {topic}")],
    }


async def script_node(state: AgentState) -> dict:
    """Draft a short-form video script based on research output.

    TODO: Replace stub with an LLM chain (e.g. ChatOpenAI) that
    receives the research results and produces a real script.
    """
    logger.info("script_node — drafting script …")

    research = state.get("research_results", {})
    topic = research.get("topic", "unknown")

    script_draft = (
        f"🎬 YOUTUBE SHORT SCRIPT — {topic.upper()}\n"
        f"{'=' * 40}\n\n"
        f"[HOOK — 0-3 s]\n"
        f'"Did you know {topic} is changing everything?"\n\n'
        f"[BODY — 3-50 s]\n"
        f"Here are 3 things you need to know about {topic} …\n"
        f"1. …\n2. …\n3. …\n\n"
        f"[CTA — 50-60 s]\n"
        f'"Follow for more {topic} content!"\n'
    )

    return {
        "current_step": "script",
        "script_draft": script_draft,
        "messages": state.get("messages", [])
        + [AIMessage(content="Script draft created.")],
    }


async def review_node(state: AgentState) -> dict:
    """Review and score the draft script for quality.

    TODO: Hook up an LLM-based reviewer / critic that returns
    structured feedback so the graph can loop back for rewrites.
    """
    logger.info("review_node — reviewing script draft …")

    script = state.get("script_draft", "")

    review_feedback = {
        "approved": True,
        "score": 0.85,
        "suggestions": [
            "Add a stronger hook with a surprising statistic.",
            "Include on-screen text cues for accessibility.",
        ],
        "word_count": len(script.split()),
    }

    return {
        "current_step": "review",
        "review_feedback": review_feedback,
        "messages": state.get("messages", [])
        + [AIMessage(content="Review complete — script approved.")],
    }


# ── Graph factory ─────────────────────────────────────────────────────


def create_agent_graph() -> StateGraph:
    """Build and compile the content-creation agent graph.

    Returns:
        A compiled ``StateGraph`` runnable.
    """
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("research", research_node)
    graph.add_node("script", script_node)
    graph.add_node("review", review_node)

    # Define edges: linear pipeline for now
    graph.set_entry_point("research")
    graph.add_edge("research", "script")
    graph.add_edge("script", "review")
    graph.add_edge("review", END)

    return graph.compile()
