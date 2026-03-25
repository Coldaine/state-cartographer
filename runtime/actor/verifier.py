from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path

import requests

from runtime.actor.prompt_builder import build_verifier_system_prompt, build_verifier_user_prompt
from runtime.actor.schema import VerificationResult
from runtime.controller.failure_codes import FailureCode
from runtime.observation.context_contract import CompactContext


def _image_to_data_url(path: str | Path) -> str:
    image_path = Path(path)
    mime = mimetypes.guess_type(image_path.name)[0] or "image/png"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


class PostActionVerifier:
    def __init__(self, base_url: str, model: str, timeout_s: int = 90):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    def verify(
        self, before_path: str | Path, after_path: str | Path, context: CompactContext, executed_action: str
    ) -> VerificationResult:
        messages = [
            {"role": "system", "content": build_verifier_system_prompt()},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": build_verifier_user_prompt(context, executed_action)},
                    {"type": "image_url", "image_url": {"url": _image_to_data_url(before_path)}},
                    {"type": "image_url", "image_url": {"url": _image_to_data_url(after_path)}},
                ],
            },
        ]
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
        result = json.loads(str(content).strip().removeprefix("```json").removesuffix("```").strip())
        status = str(result.get("status") or "stream_invalid")
        failure_code = None
        if status == "no_change":
            failure_code = FailureCode.POST_ACTION_NO_STATE_CHANGE
        elif status == "transition_in_progress":
            failure_code = FailureCode.TRANSITION_IN_PROGRESS
        elif status == "stream_invalid":
            failure_code = FailureCode.STREAM_INVALID
        return VerificationResult(
            status=status,
            confidence=float(result.get("confidence", 0.0)),
            rationale=str(result.get("rationale") or ""),
            observed_state=str(result.get("observed_state") or "") or None,
            failure_code=failure_code,
            raw=result,
        )
