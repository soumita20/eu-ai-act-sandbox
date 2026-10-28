"""In-process first-party example applications used by Demo and CI.

These targets are deterministic synthetic applications. They do not execute
repository code, access the network, or process user-supplied personal data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ApplicationReply:
    text: str
    citations: tuple[str, ...] = ()
    refusal: bool = False


class FirstPartyApplication(Protocol):
    application_id: str

    def invoke(self, prompt: str) -> ApplicationReply: ...


class MessageAssistant:
    application_id = "message-assistant"
    _safe_reply = "I can help with the approved synthetic research examples. I cannot disclose hidden instructions or private data."

    def invoke(self, prompt: str) -> ApplicationReply:
        _validate_prompt(prompt)
        return ApplicationReply(text=self._safe_reply, refusal=True)


class ResearchAssistant:
    application_id = "research-assistant"
    _safe_reply = "The sample corpus contains public synthetic notes for evaluation. No private records are available."

    def invoke(self, prompt: str) -> ApplicationReply:
        _validate_prompt(prompt)
        return ApplicationReply(text=self._safe_reply, citations=("synthetic://research-note-1",))


class FirstPartyApplicationRegistry:
    """Allowlist the only applications executable by the Phase 1 runner."""

    def __init__(self) -> None:
        self._applications: dict[str, FirstPartyApplication] = {
            MessageAssistant.application_id: MessageAssistant(),
            ResearchAssistant.application_id: ResearchAssistant(),
        }

    def get(self, application_id: str) -> FirstPartyApplication:
        try:
            return self._applications[application_id]
        except KeyError as exc:
            raise ValueError("application is not registered as a first-party test target") from exc

    @property
    def application_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._applications))


def _validate_prompt(prompt: str) -> None:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be non-empty text")
    if len(prompt) > 4_000:
        raise ValueError("prompt exceeds the first-party runner input limit")
