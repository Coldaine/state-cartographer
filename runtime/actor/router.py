from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path
from typing import Any

import requests

from runtime.actor.prompt_builder import build_actor_system_prompt, build_actor_user_prompt
from runtime.actor.schema import ActorDecision, parse_actor_decision
from runtime.controller.failure_codes import FailureCode
from runtime.observation.context_contract import CompactContext


def _image_to_data_url(path: str | Path) -> str:
    image_path = Path(path)
    mime = mimetypes.guess_type(image_path.name)[0] or "image/png"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


class LocalActorRouter:
    def __init__(self, base_url: str, model: str, timeout_s: int = 90):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    def _complete(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Content-Type": "application/json"},
            json={"model": self.model, "messages": messages, "response_format": {"type": "json_object"}},
            timeout=self.timeout_s,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "\n".join(item.get("text", "") for item in content if item.get("type") == "text")
        return json.loads(str(content).strip().removeprefix("```json").removesuffix("```").strip())

    def propose(self, frame_path: str | Path, context: CompactContext) -> ActorDecision:
        repair_note = ""
        last_error: str | None = None
        for _attempt in (1, 2):
            prompt = build_actor_user_prompt(context)
            if repair_note:
                prompt = f"{prompt}\nSchema repair note: {repair_note}"
            messages = [
                {"role": "system", "content": build_actor_system_prompt()},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": _image_to_data_url(frame_path)}},
                    ],
                },
            ]
            try:
                payload = self._complete(messages)
                return parse_actor_decision(payload)
            except Exception as exc:
                last_error = str(exc)
                repair_note = f"Previous output was invalid: {exc}. Return valid JSON only."
        return ActorDecision(
            screen_label=None,
            transition_state="unknown_or_ambiguous_state",
            candidates=(),
            raw={"error": last_error},
            failure_code=FailureCode.LOCAL_ACTOR_CANDIDATE_AMBIGUOUS,
            notes=("schema_retry_exhausted",),
        )
