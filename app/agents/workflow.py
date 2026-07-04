"""Full LangGraph workflow for autonomous Shorts production."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import asdict
from datetime import date, datetime, timedelta
from typing import Any, Callable, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph import END, StateGraph

from app.agents.analytics import AnalyticsAgent
from app.agents.learning import LearningAgent
from app.agents.script_generation import ScriptGenerationAgent
from app.agents.seo import SEOAgent
from app.agents.trend_research import TrendResearchAgent
from app.agents.video_editing import VideoEditingAgent
from app.agents.visual_generation import VisualGenerationAgent
from app.agents.voice_generation import VoiceGenerationAgent
from app.agents.youtube_upload import YouTubeUploadAgent
from app.core.config import get_settings
from app.services.analytics import AnalyticsCollectionRequest
from app.services.learning import LearningAnalysisRequest
from app.services.script_generation import ScriptGenerationRequest
from app.services.seo import SEOGenerationRequest
from app.services.video_editing import VideoEditingRequest
from app.services.visual_generation import VisualGenerationRequest
from app.services.voice_generation import VoiceGenerationRequest
from app.services.youtube import YouTubeUploadRequest

logger = logging.getLogger(__name__)

WorkflowStatus = Literal["running", "completed", "failed"]


class WorkflowState(TypedDict, total=False):
    """State shared by every node in the production Shorts workflow."""

    messages: list[BaseMessage]
    current_step: str
    workflow_status: WorkflowStatus
    metadata: dict[str, Any]
    errors: list[dict[str, Any]]
    monitoring: list[dict[str, Any]]
    trend_results: list[dict[str, Any]]
    selected_topic: dict[str, Any]
    script_draft: dict[str, str]
    script_evaluation: dict[str, Any]
    voiceover: dict[str, Any]
    visuals: dict[str, Any]
    edited_video: dict[str, Any]
    seo_metadata: dict[str, Any]
    upload_result: dict[str, Any]
    analytics_result: dict[str, Any]
    learning_result: dict[str, Any]


async def trend_workflow_node(state: WorkflowState) -> dict[str, Any]:
    return await _run_node(state, "trend", _trend_operation)


async def script_workflow_node(state: WorkflowState) -> dict[str, Any]:
    return await _run_node(state, "script", _script_operation)


async def voice_workflow_node(state: WorkflowState) -> dict[str, Any]:
    return await _run_node(state, "voice", _voice_operation)


async def visual_workflow_node(state: WorkflowState) -> dict[str, Any]:
    return await _run_node(state, "visual", _visual_operation)


async def video_editor_workflow_node(state: WorkflowState) -> dict[str, Any]:
    return await _run_node(state, "video_editor", _video_editor_operation)


async def seo_workflow_node(state: WorkflowState) -> dict[str, Any]:
    return await _run_node(state, "seo", _seo_operation)


async def upload_workflow_node(state: WorkflowState) -> dict[str, Any]:
    return await _run_node(state, "upload", _upload_operation)


async def analytics_workflow_node(state: WorkflowState) -> dict[str, Any]:
    return await _run_node(state, "analytics", _analytics_operation)


async def learning_workflow_node(state: WorkflowState) -> dict[str, Any]:
    return await _run_node(
        state,
        "learning",
        _learning_operation,
        completed_status="completed",
    )


async def _trend_operation(state: WorkflowState) -> dict[str, Any]:
    metadata = state.get("metadata", {})
    agent = metadata.get("trend_agent") or TrendResearchAgent.from_settings()
    trends = await agent.fetch_trending_topics(
        category=metadata.get("category"),
        limit=int(metadata.get("trend_limit", 5)),
    )
    topic_name = metadata.get("topic") or (
        trends[0]["topic"] if trends else "AI technology"
    )
    selected = next(
        (trend for trend in trends if trend.get("topic") == topic_name),
        {"topic": topic_name, "category": metadata.get("category", "general"), "keywords": []},
    )
    return {"trend_results": trends, "selected_topic": selected}


async def _script_operation(state: WorkflowState) -> dict[str, Any]:
    settings = get_settings()
    metadata = state.get("metadata", {})
    selected = state.get("selected_topic", {})
    topic = selected.get("topic", metadata.get("topic", "AI technology"))
    keywords = selected.get("keywords") or selected.get("trending_keywords") or []
    agent = metadata.get("script_agent") or ScriptGenerationAgent.from_settings(settings)
    request = ScriptGenerationRequest(
        topic=topic,
        category=selected.get("category", metadata.get("category", "general")),
        keywords=keywords[:10],
        target_seconds=int(metadata.get("script_target_seconds", settings.SCRIPT_TARGET_SECONDS)),
        audience=metadata.get("audience", "curious general viewers"),
        tone=metadata.get("tone", "energetic, clear, and credible"),
        research_context={"selected_topic": selected, "trend_results": state.get("trend_results", [])},
    )
    result = await agent.generate(request)
    return {
        "script_draft": result.draft.to_dict(),
        "script_evaluation": asdict(result.evaluation),
    }


async def _voice_operation(state: WorkflowState) -> dict[str, Any]:
    metadata = state.get("metadata", {})
    agent = metadata.get("voice_agent") or VoiceGenerationAgent.from_settings()
    request = VoiceGenerationRequest(
        text=_script_text(state.get("script_draft", {})),
        voice=metadata.get("voice", "narrator"),
        filename_prefix=metadata.get("filename_prefix", "voiceover"),
    )
    result = await agent.generate(request)
    return {"voiceover": _to_dict(result)}


async def _visual_operation(state: WorkflowState) -> dict[str, Any]:
    metadata = state.get("metadata", {})
    selected = state.get("selected_topic", {})
    agent = metadata.get("visual_agent") or VisualGenerationAgent.from_settings()
    request = VisualGenerationRequest(
        script=state.get("script_draft", {}),
        topic=selected.get("topic", metadata.get("topic", "YouTube Shorts")),
        style=metadata.get("visual_style", get_settings().VISUAL_STYLE),
        max_scenes=int(metadata.get("visual_max_scenes", get_settings().VISUAL_MAX_SCENES)),
        filename_prefix=metadata.get("filename_prefix", "visual"),
    )
    result = await agent.generate(request)
    return {"visuals": _to_dict(result)}


async def _video_editor_operation(state: WorkflowState) -> dict[str, Any]:
    metadata = state.get("metadata", {})
    agent = metadata.get("video_editing_agent") or VideoEditingAgent.from_settings()
    visual_assets = state.get("visuals", {}).get("assets", [])
    voiceover = state.get("voiceover", {})
    request = VideoEditingRequest(
        visuals=[asset.get("asset_path") for asset in visual_assets if asset.get("asset_path")],
        voiceover_path=voiceover.get("audio_path", ""),
        script=state.get("script_draft", {}),
        background_music_path=metadata.get("background_music_path"),
        output_prefix=metadata.get("filename_prefix", "short"),
    )
    result = await agent.render(request)
    return {"edited_video": _to_dict(result)}


async def _seo_operation(state: WorkflowState) -> dict[str, Any]:
    metadata = state.get("metadata", {})
    selected = state.get("selected_topic", {})
    agent = metadata.get("seo_agent") or SEOAgent.from_settings()
    request = SEOGenerationRequest(
        topic=selected.get("topic", metadata.get("topic", "YouTube Shorts")),
        script=state.get("script_draft", {}),
        category=selected.get("category", metadata.get("category", "general")),
        seed_keywords=selected.get("keywords", []),
        audience=metadata.get("audience", "curious general viewers"),
        research_context={"trend_results": state.get("trend_results", [])},
    )
    result = await agent.generate(request)
    return {"seo_metadata": result.metadata.to_dict()}


async def _upload_operation(state: WorkflowState) -> dict[str, Any]:
    metadata = state.get("metadata", {})
    agent = metadata.get("upload_agent") or YouTubeUploadAgent.from_settings()
    seo = state.get("seo_metadata", {})
    edited_video = state.get("edited_video", {})
    request = YouTubeUploadRequest(
        video_path=edited_video.get("video_path", ""),
        title=seo.get("title", "YouTube Short")[:100],
        description=seo.get("description", ""),
        tags=_upload_tags(seo),
        privacy_status=metadata.get("privacy_status", get_settings().YOUTUBE_DEFAULT_PRIVACY_STATUS),
        publish_at=_datetime_or_none(metadata.get("publish_at")),
        video_id=_uuid_or_none(metadata.get("db_video_id")),
    )
    result = await agent.upload(request)
    return {"upload_result": result.to_dict()}


async def _analytics_operation(state: WorkflowState) -> dict[str, Any]:
    metadata = state.get("metadata", {})
    agent = metadata.get("analytics_agent")
    if agent is None:
        db_session = metadata.get("db_session")
        if db_session is None:
            raise RuntimeError("analytics_agent or db_session is required.")
        agent = AnalyticsAgent.from_session(db_session)

    upload = state.get("upload_result", {})
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=int(metadata.get("analytics_lookback_days", 7)))
    result = await agent.collect(
        AnalyticsCollectionRequest(
            start_date=start_date,
            end_date=end_date,
            external_video_ids=[upload["video_id"]] if upload.get("video_id") else [],
            max_results=int(metadata.get("analytics_max_results", 100)),
        )
    )
    return {"analytics_result": _to_dict(result)}


async def _learning_operation(state: WorkflowState) -> dict[str, Any]:
    metadata = state.get("metadata", {})
    agent = metadata.get("learning_agent")
    if agent is None:
        db_session = metadata.get("db_session")
        if db_session is None:
            raise RuntimeError("learning_agent or db_session is required.")
        agent = LearningAgent.from_session(db_session)
    result = await agent.run_learning_cycle(
        LearningAnalysisRequest(
            lookback_days=int(metadata.get("learning_lookback_days", get_settings().LEARNING_LOOKBACK_DAYS)),
            top_n=int(metadata.get("learning_top_n", get_settings().LEARNING_TOP_N)),
            max_samples=int(metadata.get("learning_max_samples", get_settings().LEARNING_MAX_SAMPLES)),
            min_views=int(metadata.get("learning_min_views", get_settings().LEARNING_MIN_VIEWS)),
            store_results=bool(metadata.get("learning_store_results", True)),
            model_version=metadata.get("learning_model_version", get_settings().LEARNING_MODEL_VERSION),
        )
    )
    return {"learning_result": _to_dict(result)}


async def _run_node(
    state: WorkflowState,
    step: str,
    operation: Callable[[WorkflowState], Any],
    *,
    completed_status: WorkflowStatus = "running",
) -> dict[str, Any]:
    settings = get_settings()
    metadata = state.get("metadata", {})
    max_attempts = int(metadata.get("workflow_retry_attempts", settings.WORKFLOW_RETRY_ATTEMPTS))
    base_delay = float(metadata.get("workflow_retry_base_delay", settings.WORKFLOW_RETRY_BASE_DELAY))
    max_delay = float(metadata.get("workflow_retry_max_delay", settings.WORKFLOW_RETRY_MAX_DELAY))
    start = time.perf_counter()

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info("workflow step %s starting attempt %s", step, attempt)
            partial = await operation(state)
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            return {
                **partial,
                "current_step": step,
                "workflow_status": completed_status,
                "monitoring": state.get("monitoring", []) + [
                    {
                        "step": step,
                        "status": "succeeded",
                        "attempts": attempt,
                        "duration_ms": duration_ms,
                    }
                ],
                "messages": state.get("messages", []) + [
                    AIMessage(content=f"{step} step completed.")
                ],
            }
        except Exception as exc:
            logger.warning(
                "workflow step %s failed on attempt %s/%s: %s",
                step,
                attempt,
                max_attempts,
                exc,
            )
            if attempt >= max_attempts:
                duration_ms = round((time.perf_counter() - start) * 1000, 2)
                error = {
                    "step": step,
                    "attempt": attempt,
                    "error": str(exc),
                    "type": exc.__class__.__name__,
                }
                return {
                    "current_step": step,
                    "workflow_status": "failed",
                    "errors": state.get("errors", []) + [error],
                    "monitoring": state.get("monitoring", []) + [
                        {
                            "step": step,
                            "status": "failed",
                            "attempts": attempt,
                            "duration_ms": duration_ms,
                            "error": str(exc),
                        }
                    ],
                    "messages": state.get("messages", []) + [
                        AIMessage(content=f"{step} step failed: {exc}")
                    ],
                }
            await asyncio.sleep(min(max_delay, base_delay * (2 ** (attempt - 1))))

    return {"workflow_status": "failed"}


def create_shorts_workflow_graph():
    """Build the full production Shorts workflow graph."""
    graph = StateGraph(WorkflowState)
    graph.add_node("trend", trend_workflow_node)
    graph.add_node("script", script_workflow_node)
    graph.add_node("voice", voice_workflow_node)
    graph.add_node("visual", visual_workflow_node)
    graph.add_node("video_editor", video_editor_workflow_node)
    graph.add_node("seo", seo_workflow_node)
    graph.add_node("upload", upload_workflow_node)
    graph.add_node("analytics", analytics_workflow_node)
    graph.add_node("learning", learning_workflow_node)

    graph.set_entry_point("trend")
    graph.add_conditional_edges("trend", _route_or_end("script"), {"script": "script", END: END})
    graph.add_conditional_edges("script", _route_or_end("voice"), {"voice": "voice", END: END})
    graph.add_conditional_edges("voice", _route_or_end("visual"), {"visual": "visual", END: END})
    graph.add_conditional_edges("visual", _route_or_end("video_editor"), {"video_editor": "video_editor", END: END})
    graph.add_conditional_edges("video_editor", _route_or_end("seo"), {"seo": "seo", END: END})
    graph.add_conditional_edges("seo", _route_or_end("upload"), {"upload": "upload", END: END})
    graph.add_conditional_edges("upload", _route_or_end("analytics"), {"analytics": "analytics", END: END})
    graph.add_conditional_edges("analytics", _route_or_end("learning"), {"learning": "learning", END: END})
    graph.add_edge("learning", END)
    return graph.compile()


def _route_or_end(next_step: str):
    def route(state: WorkflowState):
        if state.get("workflow_status") == "failed":
            return END
        return next_step

    return route


def _script_text(script: dict[str, str]) -> str:
    return " ".join(
        str(script.get(key, "")).strip()
        for key in ("hook", "script", "cta")
        if str(script.get(key, "")).strip()
    )


def _to_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return value
    return asdict(value)


def _upload_tags(seo: dict[str, Any]) -> list[str]:
    values = list(seo.get("keywords", []) or []) + list(seo.get("hashtags", []) or [])
    tags: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = str(value).strip().lstrip("#")
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            tags.append(cleaned)
    return tags


def _datetime_or_none(value: Any) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return None


def _uuid_or_none(value: Any) -> uuid.UUID | None:
    if value is None or isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str) and value:
        return uuid.UUID(value)
    return None
