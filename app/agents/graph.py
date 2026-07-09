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
from dataclasses import asdict
from typing import Any, TypedDict

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.script_generation import ScriptGenerationAgent
from app.agents.trend_research import TrendResearchAgent
from app.core.config import get_settings
from app.services.script_generation import ScriptGenerationRequest

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
    script_draft: str | dict[str, str]
    script_evaluation: dict[str, Any]
    review_feedback: dict[str, Any]


# ── Node implementations ─────────────────────────────────────────────


async def research_node(state: AgentState) -> dict:
    """Gather trending topics, keywords, and reference material.

    TODO: Integrate real YouTube / Google Trends / SerpAPI calls.
    """
    logger.info("research_node — starting topic research …")

    metadata = state.get("metadata", {})
    category = metadata.get("category")
    limit = int(metadata.get("trend_limit", 5))

    agent = metadata.get("trend_agent") or TrendResearchAgent.from_settings()
    trending_topics = await agent.fetch_trending_topics(
        category=category,
        limit=limit,
    )
    topic = metadata.get("topic") or (
        trending_topics[0]["topic"] if trending_topics else "AI technology"
    )
    trending_keywords = [
        keyword for trend in trending_topics for keyword in trend.get("keywords", [])
    ]
    research_results = {
        "topic": topic,
        "trending_topics": trending_topics,
        "trending_keywords": trending_keywords
        or [
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

    settings = get_settings()
    metadata = state.get("metadata", {})
    research = state.get("research_results", {})
    topic = research.get("topic", "unknown")
    script_agent = metadata.get("script_agent")

    if script_agent is not None or settings.ANTHROPIC_API_KEY:
        agent = script_agent or ScriptGenerationAgent.from_settings(settings)
        request = ScriptGenerationRequest(
            topic=topic,
            category=metadata.get("category", "general"),
            keywords=research.get("trending_keywords", [])[:10],
            target_seconds=int(
                metadata.get("script_target_seconds", settings.SCRIPT_TARGET_SECONDS)
            ),
            audience=metadata.get("audience", "curious general viewers"),
            tone=metadata.get("tone", "energetic, clear, and credible"),
            research_context=research,
        )
        result = await agent.generate(request)
        generated_script = result.draft.to_dict()

        return {
            "current_step": "script",
            "script_draft": generated_script,
            "script_evaluation": asdict(result.evaluation),
            "messages": state.get("messages", [])
            + [AIMessage(content="Claude script draft created.")],
        }

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

    script_value = state.get("script_draft", "")
    if isinstance(script_value, dict):
        script = " ".join(
            script_value.get(part, "") for part in ("hook", "script", "cta")
        )
    else:
        script = script_value

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


def create_agent_graph() -> CompiledStateGraph:
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
