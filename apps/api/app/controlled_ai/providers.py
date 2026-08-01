"""Provider adapter layer — TOOLS.md section 8.3: "direct typed provider
adapters are sufficient" (no LangChain/LlamaIndex/orchestration framework).
Every outbound call goes through this narrow interface; no caller ever
imports `httpx` against an AI vendor directly. Matches the same shape
`app.communications.providers` already established for message providers.

With no `OPENAI_API_KEY`/`GROQ_API_KEY` configured (the default for local
development and tests, per CLAUDE.md section 21), `get_ai_provider()`
falls back to `MockAiProvider` — deterministic, no network call, so
ordinary CRM workflows and the test suite never depend on live AI
credentials (GROWTH_AND_INTELLIGENCE.md section 14.9's "AI outage does not
block core CRM," applied to "AI never configured" as the same case).
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import Settings, get_settings

_REQUEST_TIMEOUT_SECONDS = 20.0


@dataclass(frozen=True)
class AiCompletionResult:
    provider_code: str
    model_reference: str
    output_text: str
    output_structured: dict[str, object] | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int
    accepted: bool
    failure_reason: str | None = None


class AiProviderAdapter(ABC):
    name: str

    @abstractmethod
    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, object] | None,
    ) -> AiCompletionResult: ...


class _OpenAiCompatibleProvider(AiProviderAdapter):
    """Shared implementation for OpenAI and Groq — both expose an
    OpenAI-compatible `/chat/completions` endpoint, so only the base URL,
    API key, and model differ."""

    def __init__(self, *, name: str, base_url: str, api_key: str, model: str) -> None:
        self.name = name
        self._base_url = base_url
        self._api_key = api_key
        self._model = model

    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, object] | None,
    ) -> AiCompletionResult:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        if response_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "controlled_ai_output", "schema": response_schema},
            }

        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
        except httpx.HTTPError as exc:
            latency_ms = int((time.monotonic() - started) * 1000)
            return AiCompletionResult(
                provider_code=self.name,
                model_reference=self._model,
                output_text="",
                output_structured=None,
                input_tokens=None,
                output_tokens=None,
                latency_ms=latency_ms,
                accepted=False,
                failure_reason=f"network_error: {exc}",
            )
        latency_ms = int((time.monotonic() - started) * 1000)

        if response.status_code >= 400:
            return AiCompletionResult(
                provider_code=self.name,
                model_reference=self._model,
                output_text="",
                output_structured=None,
                input_tokens=None,
                output_tokens=None,
                latency_ms=latency_ms,
                accepted=False,
                failure_reason=f"provider_error_{response.status_code}",
            )

        body = response.json()
        content = body["choices"][0]["message"]["content"]
        usage = body.get("usage", {})
        structured: dict[str, object] | None = None
        if response_schema is not None:
            import json

            try:
                structured = json.loads(content)
            except (ValueError, TypeError):
                structured = None

        return AiCompletionResult(
            provider_code=self.name,
            model_reference=self._model,
            output_text=content,
            output_structured=structured,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            latency_ms=latency_ms,
            accepted=True,
        )


class OpenAiProvider(_OpenAiCompatibleProvider):
    def __init__(self, *, api_key: str, model: str) -> None:
        super().__init__(
            name="openai", base_url="https://api.openai.com/v1", api_key=api_key, model=model
        )


class GroqProvider(_OpenAiCompatibleProvider):
    def __init__(self, *, api_key: str, model: str) -> None:
        super().__init__(
            name="groq", base_url="https://api.groq.com/openai/v1", api_key=api_key, model=model
        )


class MockAiProvider(AiProviderAdapter):
    """The only provider active with no live credentials configured — a
    deterministic, template-based narrative built directly from the
    grounded evidence in `user_prompt`, never a network call. Real enough
    to exercise the full controlled-AI pipeline (audit trail, grounding,
    structured-output validation, feedback) end to end without a vendor
    account."""

    name = "mock"

    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, object] | None,
    ) -> AiCompletionResult:
        summary = (
            "Mock advisory summary (no live AI provider configured). "
            "Grounded on the following evidence: " + user_prompt[:400].replace("\n", " ")
        )
        structured: dict[str, object] | None = None
        if response_schema is not None:
            # Populate every property the schema declares (not a fixed
            # shape) so the mock satisfies whichever template's schema it
            # is handed — a real bug caught by this phase's own smoke
            # test: a hardcoded {"summary","confidence","source"} shape
            # failed `validate_structured_output` for templates requiring
            # different fields (e.g. "highlights").
            properties = response_schema.get("properties", {})
            structured = {}
            if isinstance(properties, dict):
                for field_name, field_schema in properties.items():
                    field_type = (
                        field_schema.get("type") if isinstance(field_schema, dict) else None
                    )
                    if field_type == "array":
                        structured[field_name] = [summary]
                    elif field_type == "string":
                        enum_values = (
                            field_schema.get("enum") if isinstance(field_schema, dict) else None
                        )
                        structured[field_name] = (
                            enum_values[0]
                            if isinstance(enum_values, list) and enum_values
                            else summary
                        )
                    else:
                        structured[field_name] = summary
            if not structured:
                structured = {"summary": summary}
        return AiCompletionResult(
            provider_code=self.name,
            model_reference="mock-deterministic-v1",
            output_text=summary,
            output_structured=structured,
            input_tokens=len(user_prompt) // 4,
            output_tokens=len(summary) // 4,
            latency_ms=1,
            accepted=True,
        )


def get_ai_provider(settings: Settings | None = None) -> AiProviderAdapter:
    settings = settings or get_settings()
    if settings.openai_api_key:
        return OpenAiProvider(api_key=settings.openai_api_key, model=settings.openai_model)
    if settings.groq_api_key:
        return GroqProvider(api_key=settings.groq_api_key, model=settings.groq_model)
    return MockAiProvider()
