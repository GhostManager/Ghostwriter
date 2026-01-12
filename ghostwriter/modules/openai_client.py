"""Utilities for interacting with the OpenAI Responses API."""

from __future__ import annotations

import logging
from typing import Optional

from django.db.utils import OperationalError, ProgrammingError
from openai import OpenAI

from ghostwriter.commandcenter.models import OpenAIConfiguration

logger = logging.getLogger(__name__)

def _extract_response_text(response: object) -> Optional[str]:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    payload = response
    if hasattr(response, "model_dump"):
        payload = response.model_dump()

    if not isinstance(payload, dict):
        return None

    output_items = payload.get("output", [])
    parts: list[str] = []
    for item in output_items:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            if content.get("type") not in {"output_text", "text"}:
                continue
            text_value = content.get("text")
            if isinstance(text_value, dict):
                text_value = text_value.get("value")
            if isinstance(text_value, str) and text_value.strip():
                parts.append(text_value.strip())

    if parts:
        return " ".join(parts).strip()

    return None


def submit_prompt_to_assistant(prompt: str, config: Optional[OpenAIConfiguration] = None) -> Optional[str]:
    """Submit ``prompt`` to the configured OpenAI prompt and return the response text."""

    if not prompt or not prompt.strip():
        return None

    try:
        active_config = config or OpenAIConfiguration.get_solo()
    except (OpenAIConfiguration.DoesNotExist, ProgrammingError, OperationalError):
        logger.debug("OpenAI configuration is unavailable; skipping prompt submission")
        return None

    if not active_config.enable:
        return None

    prompt_id = (active_config.prompt_id or "").strip()
    api_key = (active_config.api_key or "").strip()
    if not prompt_id or not api_key:
        return None

    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            prompt=prompt_id,
            input=prompt,
        )
    except Exception as exc:  # pragma: no cover - network safety
        logger.warning("Failed to submit OpenAI prompt: %s", exc)
        return None

    return _extract_response_text(response)
