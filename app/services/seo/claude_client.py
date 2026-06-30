"""Claude provider for YouTube SEO generation."""

from app.services.script_generation.claude_client import ClaudeScriptClient


class ClaudeSEOClient(ClaudeScriptClient):
    """Anthropic Messages API client specialized by its SEO prompts."""
