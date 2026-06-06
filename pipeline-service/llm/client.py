"""
LiteLLM client wrapper — unified interface for LLM API calls.

Supports OpenAI, DeepSeek, Claude, and other providers via LiteLLM.
Enforces Structured Output / JSON mode for reliable parsing.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any

import litellm
from dotenv import load_dotenv

# Load .env file at module import time
load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class LLMError(Exception):
    """Base class for LLM-related errors."""


class LLMTimeoutError(LLMError):
    """Request timed out after retries."""


class LLMResponseError(LLMError):
    """Response is not valid JSON when structured output was expected."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_TIMEOUT = 60  # seconds
_MAX_RETRIES = 1
_DEFAULT_MODEL = "openai/mimo-v2.5-pro"  # MiMo model via OpenAI-compatible API


def _get_model(model: str | None) -> str:
    return model or os.getenv("LITELLM_MODEL", _DEFAULT_MODEL)


def _get_api_config(model: str | None = None) -> dict:
    """Get API configuration for the current model from environment variables."""
    resolved = _get_model(model)
    config: dict = {}
    if "mimo" in resolved.lower():
        base_url = os.getenv("MIMO_BASE_URL")
        api_key = os.getenv("MIMO_API_KEY")
        if not base_url or not api_key:
            raise LLMError(
                "MIMO_BASE_URL and MIMO_API_KEY environment variables are required. "
                "Copy .env.example to .env and fill in your values."
            )
        config["base_url"] = base_url
        config["api_key"] = api_key
    return config


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------


async def llm_complete(
    prompt: str,
    schema: dict[str, Any] | None = None,
    model: str | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> dict:
    """
    Send a completion request to the LLM.

    Args:
        prompt: the full prompt text
        schema: optional JSON Schema for structured output (forces JSON mode)
        model: optional model override (defaults to env LITELLM_MODEL)
        timeout: request timeout in seconds

    Returns:
        Parsed JSON response as a dictionary.

    Raises:
        LLMTimeoutError: if the request times out after retries
        LLMResponseError: if the response is not valid JSON when schema is provided
    """
    resolved_model = _get_model(model)
    api_config = _get_api_config(resolved_model)
    last_exc: Exception | None = None

    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = await litellm.acompletion(
                model=resolved_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"} if schema else None,
                timeout=timeout,
                **api_config,  # Pass base_url and api_key for MiMo
            )
            raw_text = response.choices[0].message.content or ""

            # Parse JSON
            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError as e:
                # If schema was expected, treat as error
                if schema:
                    raise LLMResponseError(
                        f"LLM returned invalid JSON (attempt {attempt + 1}): {e}\n"
                        f"Raw response: {raw_text[:500]}"
                    ) from e
                # No schema expected — wrap in dict
                return {"text": raw_text}

            # Validate against schema if provided (basic structural check)
            if schema:
                _validate_structure(data, schema)

            return data

        except (litellm.Timeout, LLMResponseError) as e:
            last_exc = e
            logger.warning("LLM attempt %d failed: %s", attempt + 1, e)
            if attempt < _MAX_RETRIES:
                continue
            break
        except Exception as e:
            last_exc = e
            logger.error("Unexpected LLM error: %s", e)
            raise

    # All retries exhausted
    if isinstance(last_exc, LLMResponseError):
        raise last_exc
    raise LLMTimeoutError(
        f"LLM request timed out after {_MAX_RETRIES + 1} attempts: {last_exc}"
    )


def _validate_structure(data: dict, schema: dict) -> None:
    """
    Lightweight structural validation — checks required keys exist.
    Full JSON Schema validation is deferred to the caller (jsonschema lib).
    """
    required = schema.get("required", [])
    missing = [k for k in required if k not in data]
    if missing:
        raise LLMResponseError(
            f"LLM response missing required keys: {missing}. Got keys: {list(data.keys())}"
        )


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------

StreamCallback = Callable[[str], Awaitable[None]]
"""Called with each chunk of streamed text. Return value is awaited."""


async def llm_stream_json(
    prompt: str,
    schema: dict[str, Any] | None = None,
    model: str | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
    on_chunk: StreamCallback | None = None,
) -> dict:
    """
    Stream a completion request, calling on_chunk for each token.
    Falls back to non-streaming on JSON parse failure.
    """
    resolved_model = _get_model(model)
    api_config = _get_api_config(resolved_model)

    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = await litellm.acompletion(
                model=resolved_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"} if schema else None,
                timeout=timeout,
                stream=True,
                **api_config,
            )

            accumulated: list[str] = []
            async for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    accumulated.append(delta)
                    if on_chunk:
                        await on_chunk(delta)

            raw_text = "".join(accumulated)

            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError as e:
                if attempt < _MAX_RETRIES:
                    logger.warning("Streaming JSON parse failed (attempt %d), retrying...", attempt + 1)
                    continue
                if schema:
                    raise LLMResponseError(
                        f"LLM returned invalid JSON after {_MAX_RETRIES + 1} attempts: {e}\n"
                        f"Raw: {raw_text[:500]}"
                    ) from e
                return {"text": raw_text}

            if schema:
                _validate_structure(data, schema)

            return data

        except (litellm.Timeout,) as e:
            if attempt < _MAX_RETRIES:
                logger.warning("Streaming timeout (attempt %d), retrying...", attempt + 1)
                continue
            raise LLMTimeoutError(f"Streaming timed out after {_MAX_RETRIES + 1} attempts") from e

    raise LLMTimeoutError(f"Streaming failed after {_MAX_RETRIES + 1} attempts")
