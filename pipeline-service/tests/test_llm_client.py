"""
Unit tests for the LLM client wrapper (llm/client.py).

Uses pytest-mock to stub litellm.acompletion — no real API calls.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from llm.client import (
    LLMResponseError,
    LLMTimeoutError,
    _validate_structure,
    llm_complete,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(content: str):
    """Create a fake litellm completion response."""
    msg = type("Message", (), {"content": content})()
    choice = type("Choice", (), {"message": msg})()
    return type("Response", (), {"choices": [choice]})()


# ---------------------------------------------------------------------------
# Tests: successful calls
# ---------------------------------------------------------------------------


class TestSuccessfulCalls:
    @pytest.mark.asyncio
    async def test_returns_parsed_json(self) -> None:
        payload = {"synopsis": "test", "characters": [], "locations": []}
        with patch("llm.client.litellm.acompletion", new_callable=AsyncMock) as mock:
            mock.return_value = _mock_response(json.dumps(payload))
            result = await llm_complete("hello", schema={"required": ["synopsis"]})

        assert result["synopsis"] == "test"
        mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_schema_returns_text_wrapped(self) -> None:
        with patch("llm.client.litellm.acompletion", new_callable=AsyncMock) as mock:
            mock.return_value = _mock_response("just some text")
            result = await llm_complete("hello")

        assert result == {"text": "just some text"}

    @pytest.mark.asyncio
    async def test_passes_model_override(self) -> None:
        with patch("llm.client.litellm.acompletion", new_callable=AsyncMock) as mock:
            mock.return_value = _mock_response("{}")
            await llm_complete("hi", model="openai/gpt-4o")

        call_args = mock.call_args
        assert call_args.kwargs["model"] == "openai/gpt-4o"

    @pytest.mark.asyncio
    async def test_passes_timeout(self) -> None:
        with patch("llm.client.litellm.acompletion", new_callable=AsyncMock) as mock:
            mock.return_value = _mock_response("{}")
            await llm_complete("hi", timeout=30)

        call_args = mock.call_args
        assert call_args.kwargs["timeout"] == 30

    @pytest.mark.asyncio
    async def test_env_model_override(self) -> None:
        with patch("llm.client.os.getenv", return_value="deepseek/deepseek-chat"):
            with patch("llm.client.litellm.acompletion", new_callable=AsyncMock) as mock:
                mock.return_value = _mock_response("{}")
                await llm_complete("hi")

            call_args = mock.call_args
            assert call_args.kwargs["model"] == "deepseek/deepseek-chat"


# ---------------------------------------------------------------------------
# Tests: structured output enforcement
# ---------------------------------------------------------------------------


class TestStructuredOutput:
    @pytest.mark.asyncio
    async def test_sets_response_format_json_object(self) -> None:
        schema = {"type": "object", "required": ["result"]}
        with patch("llm.client.litellm.acompletion", new_callable=AsyncMock) as mock:
            mock.return_value = _mock_response('{"result": "ok"}')
            await llm_complete("hi", schema=schema)

        call_args = mock.call_args
        assert call_args.kwargs["response_format"] == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_no_schema_response_format_is_none(self) -> None:
        with patch("llm.client.litellm.acompletion", new_callable=AsyncMock) as mock:
            mock.return_value = _mock_response("text")
            await llm_complete("hi")

        call_args = mock.call_args
        assert call_args.kwargs["response_format"] is None


# ---------------------------------------------------------------------------
# Tests: error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_invalid_json_raises_response_error(self) -> None:
        schema = {"required": ["synopsis"]}
        with patch("llm.client.litellm.acompletion", new_callable=AsyncMock) as mock:
            mock.return_value = _mock_response("this is not json at all")
            with pytest.raises(LLMResponseError, match="invalid JSON"):
                await llm_complete("hi", schema=schema)

    @pytest.mark.asyncio
    async def test_missing_required_keys_raises_response_error(self) -> None:
        schema = {"required": ["synopsis", "characters"]}
        with patch("llm.client.litellm.acompletion", new_callable=AsyncMock) as mock:
            mock.return_value = _mock_response('{"synopsis": "ok"}')
            with pytest.raises(LLMResponseError, match="missing required keys"):
                await llm_complete("hi", schema=schema)

    @pytest.mark.asyncio
    async def test_timeout_retries_then_raises(self) -> None:
        from litellm.exceptions import Timeout

        with patch("llm.client.litellm.acompletion", new_callable=AsyncMock) as mock:
            mock.side_effect = Timeout(
                model="test-model", llm_provider="openai", message="timed out"
            )
            with pytest.raises(LLMTimeoutError, match="timed out"):
                await llm_complete("hi", timeout=1)

        # Should have been called twice (initial + 1 retry)
        assert mock.call_count == 2

    @pytest.mark.asyncio
    async def test_invalid_json_retries_then_raises(self) -> None:
        schema = {"required": ["result"]}
        with patch("llm.client.litellm.acompletion", new_callable=AsyncMock) as mock:
            mock.return_value = _mock_response("not json")
            with pytest.raises(LLMResponseError, match="invalid JSON"):
                await llm_complete("hi", schema=schema)

        # Should have been called twice (initial + 1 retry)
        assert mock.call_count == 2


# ---------------------------------------------------------------------------
# Tests: _validate_structure
# ---------------------------------------------------------------------------


class TestValidateStructure:
    def test_passes_when_all_required_keys_present(self) -> None:
        schema = {"required": ["a", "b"]}
        _validate_structure({"a": 1, "b": 2, "c": 3}, schema)  # should not raise

    def test_raises_when_key_missing(self) -> None:
        schema = {"required": ["a", "b", "c"]}
        with pytest.raises(LLMResponseError, match="missing required keys"):
            _validate_structure({"a": 1}, schema)

    def test_empty_required_passes(self) -> None:
        _validate_structure({"anything": 1}, {"required": []})  # should not raise
