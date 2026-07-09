from __future__ import annotations

import json

import pytest

from app.agents.script_generation import ScriptGenerationResult
from app.agents.seo import SEOGenerationResult
from app.agents.workflow import create_shorts_workflow_graph
from app.services.analytics import AnalyticsCollectionResult
from app.services.learning import LearningAnalysisRequest, LearningAnalyzer
from app.services.script_generation import (
    ScriptDraft,
    ScriptEvaluator,
    ScriptGenerationRequest,
)
from app.services.seo import SEOEvaluation, SEOMetadata
from app.services.video_editing import VideoEditingResult
from app.services.visual_generation import VisualAsset, VisualGenerationResult
from app.services.voice_generation import VoiceGenerationResult
from app.services.youtube import YouTubeUploadResult

pytestmark = pytest.mark.no_db


class FakeTrendAgent:
    async def fetch_trending_topics(self, *, category=None, limit=5):
        return [
            {
                "topic": "AI video editing",
                "score": 94,
                "category": category or "technology",
                "keywords": ["AI video editing", "YouTube Shorts"],
            }
        ][:limit]


class FakeScriptAgent:
    def __init__(self, *, fail_once: bool = False) -> None:
        self.fail_once = fail_once
        self.calls = 0

    async def generate(
        self, request: ScriptGenerationRequest
    ) -> ScriptGenerationResult:
        self.calls += 1
        if self.fail_once and self.calls == 1:
            raise RuntimeError("temporary script failure")
        draft = ScriptDraft(
            hook="What if your Short could edit itself?",
            script=(
                "Use AI to find pauses, cut filler, add captions, and keep the "
                "payoff clear for creators who need faster videos."
            ),
            cta="Save this workflow before your next upload.",
        )
        return ScriptGenerationResult(
            draft=draft,
            evaluation=ScriptEvaluator().evaluate(draft),
            raw_text=json.dumps(draft.to_dict()),
            system_prompt="system",
            user_prompt=request.topic,
        )


class FakeVoiceAgent:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    async def generate(self, request):
        if self.fail:
            raise RuntimeError("voice provider unavailable")
        return VoiceGenerationResult(
            audio_path="storage/audio/voice.mp3", duration=42.0
        )


class FakeVisualAgent:
    async def generate(self, request):
        return VisualGenerationResult(
            scenes=[],
            prompts=[],
            assets=[
                VisualAsset(
                    scene_index=1,
                    asset_path="storage/visuals/scene.png",
                    provider="flux",
                    prompt="cinematic creator workflow",
                    width=1024,
                    height=1792,
                )
            ],
        )


class FakeVideoEditingAgent:
    async def render(self, request):
        return VideoEditingResult(
            video_path="storage/videos/short.mp4",
            width=1080,
            height=1920,
            duration=42.0,
        )


class FakeSEOAgent:
    async def generate(self, request):
        return SEOGenerationResult(
            metadata=SEOMetadata(
                title="7 AI Video Editing Tricks That Save Hours",
                description="Learn a fast AI video editing workflow for Shorts.",
                hashtags=["#AIVideoEditing", "#YouTubeShorts"],
                keywords=["AI video editing", "YouTube Shorts editing"],
            ),
            evaluation=SEOEvaluation(
                ctr_score=90,
                discoverability_score=90,
                description_score=80,
                overall_score=88,
                is_valid=True,
            ),
            raw_text="{}",
            system_prompt="system",
            user_prompt="user",
        )


class FakeUploadAgent:
    async def upload(self, request):
        return YouTubeUploadResult(
            video_id="yt123",
            video_url="https://www.youtube.com/watch?v=yt123",
            upload_status="uploaded",
            response_payload={"id": "yt123"},
        )


class FakeAnalyticsAgent:
    async def collect(self, request):
        return AnalyticsCollectionResult(
            collected_count=1,
            stored_count=1,
            skipped_count=0,
            snapshots=[],
        )


class FakeLearningAgent:
    async def run_learning_cycle(self, request: LearningAnalysisRequest):
        return LearningAnalyzer().analyze([], request)


def _metadata(**overrides):
    base = {
        "category": "technology",
        "trend_agent": FakeTrendAgent(),
        "script_agent": FakeScriptAgent(),
        "voice_agent": FakeVoiceAgent(),
        "visual_agent": FakeVisualAgent(),
        "video_editing_agent": FakeVideoEditingAgent(),
        "seo_agent": FakeSEOAgent(),
        "upload_agent": FakeUploadAgent(),
        "analytics_agent": FakeAnalyticsAgent(),
        "learning_agent": FakeLearningAgent(),
        "workflow_retry_attempts": 1,
        "workflow_retry_base_delay": 0,
        "workflow_retry_max_delay": 0,
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_full_shorts_workflow_completes_all_nodes() -> None:
    graph = create_shorts_workflow_graph()

    result = await graph.ainvoke({"metadata": _metadata(), "messages": []})

    assert result["workflow_status"] == "completed"
    assert result["selected_topic"]["topic"] == "AI video editing"
    assert result["script_draft"]["hook"]
    assert result["voiceover"]["audio_path"].endswith(".mp3")
    assert result["visuals"]["assets"][0]["asset_path"].endswith(".png")
    assert result["edited_video"]["video_path"].endswith(".mp4")
    assert result["seo_metadata"]["title"].startswith("7 AI")
    assert result["upload_result"]["video_id"] == "yt123"
    assert result["analytics_result"]["stored_count"] == 1
    assert result["learning_result"]["model_version"] == "learning-agent-v1"
    assert [event["step"] for event in result["monitoring"]] == [
        "trend",
        "script",
        "voice",
        "visual",
        "video_editor",
        "seo",
        "upload",
        "analytics",
        "learning",
    ]


@pytest.mark.asyncio
async def test_workflow_retries_transient_node_failure() -> None:
    script_agent = FakeScriptAgent(fail_once=True)
    graph = create_shorts_workflow_graph()

    result = await graph.ainvoke(
        {
            "metadata": _metadata(
                script_agent=script_agent,
                workflow_retry_attempts=2,
            ),
            "messages": [],
        }
    )

    script_event = next(
        event for event in result["monitoring"] if event["step"] == "script"
    )
    assert result["workflow_status"] == "completed"
    assert script_agent.calls == 2
    assert script_event["attempts"] == 2


@pytest.mark.asyncio
async def test_workflow_records_error_and_stops_after_failed_node() -> None:
    graph = create_shorts_workflow_graph()

    result = await graph.ainvoke(
        {
            "metadata": _metadata(voice_agent=FakeVoiceAgent(fail=True)),
            "messages": [],
        }
    )

    assert result["workflow_status"] == "failed"
    assert result["current_step"] == "voice"
    assert result["errors"][0]["step"] == "voice"
    assert "visuals" not in result
    assert [event["step"] for event in result["monitoring"]] == [
        "trend",
        "script",
        "voice",
    ]
