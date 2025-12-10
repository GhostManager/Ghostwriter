"""Utilities for interacting with the OpenAI Assistants API."""

from __future__ import annotations

import logging
import time
from typing import Optional

import requests
from django.db.utils import OperationalError, ProgrammingError

from ghostwriter.commandcenter.models import OpenAIConfiguration

logger = logging.getLogger(__name__)

_OPENAI_API_BASE = "https://api.openai.com/v1"
_OPENAI_ASSISTANTS_BETA = "assistants=v2"


def submit_prompt_to_assistant(prompt: str, config: Optional[OpenAIConfiguration] = None) -> Optional[str]:
    """Submit ``prompt`` to the configured OpenAI Assistant and return the response text."""

    if not prompt or not prompt.strip():
        return None

    try:
        active_config = config or OpenAIConfiguration.get_solo()
    except (OpenAIConfiguration.DoesNotExist, ProgrammingError, OperationalError):
        logger.debug("OpenAI configuration is unavailable; skipping prompt submission")
        return None

    if not active_config.enable:
        return None

    assistant_id = (active_config.assistant_id or "").strip()
    api_key = (active_config.api_key or "").strip()
    if not assistant_id or not api_key:
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "OpenAI-Beta": _OPENAI_ASSISTANTS_BETA,
        "Content-Type": "application/json",
    }

    try:
        thread_response = requests.post(
            f"{_OPENAI_API_BASE}/threads",
            headers=headers,
            timeout=30,
        )
        thread_response.raise_for_status()
        thread_id = thread_response.json().get("id")
        if not thread_id:
            logger.warning("OpenAI thread response missing identifier")
            return None

        message_response = requests.post(
            f"{_OPENAI_API_BASE}/threads/{thread_id}/messages",
            headers=headers,
            json={"role": "user", "content": [{"type": "text", "text": prompt}]},
            timeout=30,
        )
        message_response.raise_for_status()

        run_response = requests.post(
            f"{_OPENAI_API_BASE}/threads/{thread_id}/runs",
            headers=headers,
            json={"assistant_id": assistant_id},
            timeout=30,
        )
        run_response.raise_for_status()
        run_id = run_response.json().get("id")
        if not run_id:
            logger.warning("OpenAI run response missing identifier")
            return None
    except requests.RequestException as exc:  # pragma: no cover - network safety
        logger.warning("Failed to initialize OpenAI assistant run: %s", exc)
        return None

    # Keep the overall request below common gateway/proxy limits to avoid client-facing timeouts.
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            status_response = requests.get(
                f"{_OPENAI_API_BASE}/threads/{thread_id}/runs/{run_id}",
                headers=headers,
                timeout=30,
            )
            status_response.raise_for_status()
        except requests.RequestException as exc:  # pragma: no cover - network safety
            logger.warning("Error polling OpenAI run status: %s", exc)
            return None

        status_payload = status_response.json()
        status = status_payload.get("status")
        if status == "completed":
            break
        if status in {"failed", "cancelled", "expired"}:
            logger.info("OpenAI run ended with status %s", status)
            return None
        time.sleep(2)
    else:
        logger.info("OpenAI run timed out before completion")
        return None

    try:
        messages_response = requests.get(
            f"{_OPENAI_API_BASE}/threads/{thread_id}/messages",
            headers=headers,
            params={"limit": 20},
            timeout=30,
        )
        messages_response.raise_for_status()
    except requests.RequestException as exc:  # pragma: no cover - network safety
        logger.warning("Failed to fetch OpenAI messages: %s", exc)
        return None

    payload = messages_response.json()
    messages = payload.get("data", []) if isinstance(payload, dict) else []
    for message in messages:
        if not isinstance(message, dict):
            continue
        if message.get("role") != "assistant" or message.get("run_id") != run_id:
            continue
        content_entries = message.get("content") or []
        parts = []
        for entry in content_entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("type") in {"text", "output_text"}:
                text_payload = entry.get("text") or {}
                value = text_payload.get("value") if isinstance(text_payload, dict) else None
                if value:
                    parts.append(value.strip())
        if parts:
            return " ".join(part for part in parts if part).strip()

    return None
