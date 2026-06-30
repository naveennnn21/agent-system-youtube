from __future__ import annotations

import json

import httpx
import pytest

from app.agents.graph import script_node
from app.agents.script_generation import (
    ScriptGenerationAgent,
    ScriptGenerationResult,
    parse_script_response,
)
from app.services.script_generation import (
    ClaudeScriptClient,
    ScriptDraft,
    ScriptEvaluator,
    ScriptGenerationRequest,
    ScriptPromptBuilder,
)

pytestmark = pytest.mark.no_db


VALID_SCRIPT = {
    "hook": "What if your next viral Short starts with one boring mistake?",
    "script": (
        "Most creators chase bigger ideas first, but retention usually comes from "
        "a smaller promise. Start with one clear problem your viewer already feels. "
        "Then show the wrong way in one sentence, because that creates tension. "
        "Here is the simple switch: make the first line ask a question, make the "
        "middle reveal one useful contrast, and save the clearest payoff for the "
        "last five seconds. That loop keeps people watching because they know a "
        "specific answer is coming. Try this before your next upload."
    ),
    "cta": "Save this checklist and share it with a creator who needs a stronger hook.",
}


class FakeClaudeProvider:
    def __init__(self, payload: dict[str, str]) -> None:
        self.payload = payload
        self.system_prompt = ""
        self.user_prompt = ""

    async def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return json.dumps(self.payload)


def test_prompt_template_contains_constraints_and_context() -> None:
    request = ScriptGenerationRequest(
        topic="AI editing workflow",
        category="technology",
        keywords=["ai", "editing", "retention"],
        target_seconds=45,
        audience="solo creators",
        tone="sharp and practical",
        research_context={"score": 88},
    )

    system_prompt, user_prompt = ScriptPromptBuilder().build(request)

    assert "valid JSON only" in system_prompt
    assert "hook, script, cta" in system_prompt
    assert "30-60 seconds" in system_prompt
    assert "AI editing workflow" in user_prompt
    assert "solo creators" in user_prompt
    assert '"score": 88' in user_prompt


@pytest.mark.asyncio
async def test_script_generation_agent_returns_required_contract_and_evaluation() -> None:
    provider = FakeClaudeProvider(VALID_SCRIPT)
    agent = ScriptGenerationAgent(provider=provider)

    result = await agent.generate(
        ScriptGenerationRequest(
            topic="Creator retention",
            category="education",
            keywords=["hook", "retention"],
            target_seconds=45,
        )
    )

    assert result.draft.to_dict() == VALID_SCRIPT
    assert result.evaluation.is_valid
    assert 30 <= result.evaluation.estimated_seconds <= 60
    assert result.evaluation.retention_score >= 55
    assert "Creator retention" in provider.user_prompt


def test_parse_script_response_accepts_fenced_json() -> None:
    raw_text = "```json\n" + json.dumps(VALID_SCRIPT) + "\n```"

    draft = parse_script_response(raw_text)

    assert draft.hook == VALID_SCRIPT["hook"]
    assert draft.script == VALID_SCRIPT["script"]
    assert draft.cta == VALID_SCRIPT["cta"]


def test_evaluator_flags_too_short_scripts() -> None:
    evaluation = ScriptEvaluator().evaluate(
        ScriptDraft(
            hook="Want better hooks?",
            script="Ask a sharper question.",
            cta="Follow for more.",
        )
    )

    assert not evaluation.is_valid
    assert "Script is shorter than 30 seconds." in evaluation.issues


@pytest.mark.asyncio
async def test_claude_client_posts_messages_api_payload_and_extracts_text() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["api_key"] = request.headers["x-api-key"]
        captured["anthropic_version"] = request.headers["anthropic-version"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(VALID_SCRIPT),
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        claude = ClaudeScriptClient(
            api_key="test-key",
            model="claude-sonnet-4-5-20250929",
            client=client,
        )
        text = await claude.generate_text(
            system_prompt="system",
            user_prompt="user",
        )

    payload = captured["payload"]
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["api_key"] == "test-key"
    assert captured["anthropic_version"] == "2023-06-01"
    assert payload["model"] == "claude-sonnet-4-5-20250929"
    assert payload["max_tokens"] == 1200
    assert payload["system"] == "system"
    assert payload["messages"] == [{"role": "user", "content": "user"}]
    assert json.loads(text) == VALID_SCRIPT


@pytest.mark.asyncio
async def test_graph_script_node_uses_injected_script_agent() -> None:
    class FakeScriptAgent:
        async def generate(self, request: ScriptGenerationRequest) -> ScriptGenerationResult:
            draft = ScriptDraft(**VALID_SCRIPT)
            evaluation = ScriptEvaluator().evaluate(draft)
            return ScriptGenerationResult(
                draft=draft,
                evaluation=evaluation,
                raw_text=json.dumps(VALID_SCRIPT),
                system_prompt="system",
                user_prompt=f"topic={request.topic}",
            )

    output = await script_node(
        {
            "metadata": {
                "script_agent": FakeScriptAgent(),
                "script_target_seconds": 45,
                "audience": "solo creators",
            },
            "research_results": {
                "topic": "Creator retention",
                "trending_keywords": ["hook", "retention"],
            },
            "messages": [],
        }
    )

    assert output["script_draft"] == VALID_SCRIPT
    assert output["script_evaluation"]["is_valid"] is True
