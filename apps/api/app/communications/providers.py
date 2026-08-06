"""Provider adapter layer — CLAUDE.md section 16 / this phase's own
instruction's Architectural Principle 1: the domain must never import a
vendor SDK (Meta WhatsApp Cloud API, Twilio, SendGrid, etc.) directly.
Every outbound send and every inbound/status webhook goes through this
narrow interface instead.

Only `InternalMockProvider` is implemented — a real WhatsApp/email/SMS
adapter is not built in this phase (`docs/TOOLS.md` section 10 marks those
providers "final account approval required", and no environment variable
names are locked in yet, matching the earlier Phase 10 env-var research in
this project). Registering a real provider later means adding a class here
and a `provider` value on the relevant `CommunicationChannel` row — no
change to any caller of `send_text`/`parse_inbound_webhook`/etc.
"""

import hashlib
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class SendResult:
    provider_message_id: str
    accepted: bool
    failure_code: str | None = None
    failure_reason: str | None = None


@dataclass(frozen=True)
class NormalizedInboundMessage:
    provider_event_id: str
    sender_reference: str
    recipient_reference: str | None
    body_text: str | None
    provider_message_id: str | None
    received_at: datetime


@dataclass(frozen=True)
class NormalizedStatusEvent:
    provider_event_id: str
    provider_message_id: str
    normalized_status: str
    occurred_at: datetime
    failure_code: str | None = None
    failure_reason: str | None = None


class ProviderAdapter(ABC):
    """Stable capability surface this phase's own instruction section 5
    names: send text/template/attachment, parse inbound webhook, parse
    status webhook, validate webhook signature, fetch delivery status where
    supported. A provider that cannot support a capability raises
    `NotImplementedError` rather than silently no-opping."""

    name: str

    @abstractmethod
    def validate_webhook_signature(self, *, headers: dict[str, str], raw_body: bytes) -> bool: ...

    @abstractmethod
    async def send_text(self, *, recipient_reference: str, body: str) -> SendResult: ...

    @abstractmethod
    async def send_template(
        self, *, recipient_reference: str, template_code: str, rendered_body: str
    ) -> SendResult: ...

    @abstractmethod
    def parse_inbound_webhook(self, payload: dict[str, Any]) -> NormalizedInboundMessage: ...

    @abstractmethod
    def parse_status_webhook(self, payload: dict[str, Any]) -> NormalizedStatusEvent: ...


@dataclass
class InternalMockProvider(ProviderAdapter):
    """The only provider registered today — every send is accepted
    immediately and recorded, no network call is made. This is what keeps
    the Communication Hub fully functional (internal channel, staff-to-
    staff/system messages, and local development/tests) with zero live
    provider credentials configured, per this phase's own instruction
    section 5 ("must work with no live provider configured")."""

    name: str = "internal_mock"
    sent_log: list[SendResult] = field(default_factory=list)

    def validate_webhook_signature(self, *, headers: dict[str, str], raw_body: bytes) -> bool:
        # No external webhook source exists for the mock provider; any
        # caller reaching this path is a test/dev exercise of the pipeline,
        # not a real signature to check.
        return True

    async def send_text(self, *, recipient_reference: str, body: str) -> SendResult:
        result = SendResult(provider_message_id=f"mock-{uuid.uuid4().hex[:16]}", accepted=True)
        self.sent_log.append(result)
        return result

    async def send_template(
        self, *, recipient_reference: str, template_code: str, rendered_body: str
    ) -> SendResult:
        return await self.send_text(recipient_reference=recipient_reference, body=rendered_body)

    def parse_inbound_webhook(self, payload: dict[str, Any]) -> NormalizedInboundMessage:
        return NormalizedInboundMessage(
            provider_event_id=str(payload["event_id"]),
            sender_reference=str(payload["from"]),
            recipient_reference=payload.get("to"),
            body_text=payload.get("body"),
            provider_message_id=payload.get("provider_message_id"),
            received_at=datetime.now(UTC),
        )

    def parse_status_webhook(self, payload: dict[str, Any]) -> NormalizedStatusEvent:
        return NormalizedStatusEvent(
            provider_event_id=str(payload["event_id"]),
            provider_message_id=str(payload["provider_message_id"]),
            normalized_status=str(payload["status"]),
            occurred_at=datetime.now(UTC),
            failure_code=payload.get("failure_code"),
            failure_reason=payload.get("failure_reason"),
        )


_PROVIDERS: dict[str, ProviderAdapter] = {"internal_mock": InternalMockProvider()}


def get_provider(name: str | None) -> ProviderAdapter:
    """Falls back to the mock provider for any unregistered/unset name —
    CLAUDE.md section 21 ("optional integrations remain disabled without
    crashing unrelated modules"): a channel configured with a provider that
    has no adapter yet degrades to the mock rather than raising at request
    time. Only safe for outbound sends, where "silently use the mock" is
    the intended degraded behavior — see `get_registered_provider` for the
    inbound-webhook counterpart, where the same fallback would be unsafe."""
    if name is None:
        return _PROVIDERS["internal_mock"]
    return _PROVIDERS.get(name, _PROVIDERS["internal_mock"])


def get_registered_provider(name: str) -> ProviderAdapter | None:
    """Strict lookup, no mock fallback — `None` if `name` has no adapter
    registered in `_PROVIDERS`.

    Webhook entry points must use this instead of `get_provider()`. A
    channel can be created with any free-text `provider` string
    (`CommunicationChannelCreateIn.provider: str | None`, no allowlist), so
    `get_provider()`'s mock fallback would mean a channel declared
    `provider="whatsapp"` — before a real WhatsApp adapter is ever
    registered — resolves its inbound webhook to `InternalMockProvider`,
    whose `validate_webhook_signature` unconditionally returns `True`. That
    fails open: any unauthenticated caller could post unsigned payloads and
    have them accepted as genuine messages on that channel. Failing closed
    here (reject with no adapter) is correct until the real adapter lands.
    """
    return _PROVIDERS.get(name)


def hash_payload(raw_body: bytes) -> str:
    return hashlib.sha256(raw_body).hexdigest()
