"""Optional Anthropic-backed LLM service with strict structured-output parsing."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Callable
from urllib import error, request

from pydantic import BaseModel, Field, ValidationError

from app.agents.prompts import build_candidate_plan_prompt
from app.config import AppConfig

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"


class LLMCandidatePlan(BaseModel):
    """Structured candidate plan emitted by the LLM."""

    label: str
    course_ids: list[str]
    rationale_summary: str


class LLMCandidatePlanResponse(BaseModel):
    """Structured LLM candidate plan response payload."""

    plans: list[LLMCandidatePlan] = Field(default_factory=list)


@dataclass
class AnthropicRequest:
    """Parameters for one Anthropic messages API call."""

    api_key: str
    model: str
    prompt: str
    max_tokens: int
    timeout_seconds: float


AnthropicTransport = Callable[[AnthropicRequest], dict[str, Any]]


def _default_anthropic_transport(request_payload: AnthropicRequest) -> dict[str, Any]:
    """Send one request to the Anthropic messages API."""
    payload = json.dumps(
        {
            "model": request_payload.model,
            "max_tokens": request_payload.max_tokens,
            "temperature": 0,
            "messages": [{"role": "user", "content": request_payload.prompt}],
        }
    ).encode("utf-8")
    http_request = request.Request(
        ANTHROPIC_MESSAGES_URL,
        data=payload,
        headers={
            "content-type": "application/json",
            "x-api-key": request_payload.api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=request_payload.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.URLError as exc:
        raise RuntimeError(f"Anthropic request failed: {exc}") from exc


def _extract_text_content(response_payload: dict[str, Any]) -> str:
    """Extract the concatenated text blocks from an Anthropic response."""
    content_blocks = response_payload.get("content", [])
    text_segments: list[str] = []
    for block in content_blocks:
        if not isinstance(block, dict) or block.get("type") != "text":
            continue

        text_value = block.get("text", "")
        if isinstance(text_value, str):
            text_segments.append(text_value)
        elif isinstance(text_value, (list, tuple)):
            text_segments.append("".join(str(item) for item in text_value))
        else:
            text_segments.append(str(text_value))

    return "\n".join(segment for segment in text_segments if segment)


def _extract_json_block(text: str) -> str:
    """Extract the first JSON object from a raw model response."""
    fenced_match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fenced_match:
        return fenced_match.group(1)

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model response.")
    return text[start : end + 1]


class LLMService:
    """Optional LLM assistance layer for candidate plan generation."""

    def __init__(
        self,
        config: AppConfig | None = None,
        transport: AnthropicTransport | None = None,
    ) -> None:
        self.config = config or AppConfig.from_env()
        self.transport = transport or _default_anthropic_transport

    def is_enabled(self) -> bool:
        """Return whether live LLM calls are allowed and configured."""
        return self.config.llm_enabled and bool(self.config.anthropic_api_key)

    def suggest_candidate_plans(
        self,
        *,
        query: str,
        term: str,
        completed_courses: list[str],
        preferred_directions: list[str],
        max_courses: int,
        max_credits: int,
        available_courses: list[dict[str, object]],
    ) -> list[LLMCandidatePlan] | None:
        """Return parsed LLM suggestions or None when disabled/invalid."""
        if not self.is_enabled():
            return None

        prompt = build_candidate_plan_prompt(
            query=query,
            term=term,
            completed_courses=completed_courses,
            preferred_directions=preferred_directions,
            max_courses=max_courses,
            max_credits=max_credits,
            available_courses=available_courses,
        )
        response_payload = self.transport(
            AnthropicRequest(
                api_key=self.config.anthropic_api_key or "",
                model=self.config.anthropic_model,
                prompt=prompt,
                max_tokens=self.config.anthropic_max_tokens,
                timeout_seconds=self.config.anthropic_timeout_seconds,
            )
        )

        try:
            response_text = _extract_text_content(response_payload)
            response_json = json.loads(_extract_json_block(response_text))
            parsed = LLMCandidatePlanResponse.model_validate(response_json)
        except (ValueError, json.JSONDecodeError, ValidationError, RuntimeError):
            return None

        valid_labels = {"balanced", "ambitious", "conservative"}
        available_ids = {str(course["course_id"]) for course in available_courses}
        filtered_plans: list[LLMCandidatePlan] = []
        for plan in parsed.plans:
            if plan.label not in valid_labels:
                continue
            if len(plan.course_ids) > max_courses:
                continue
            if not plan.course_ids or len(set(plan.course_ids)) != len(plan.course_ids):
                continue
            if any(course_id not in available_ids for course_id in plan.course_ids):
                continue
            filtered_plans.append(plan)

        return filtered_plans or None
