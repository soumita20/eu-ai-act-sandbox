"""Read-only, manifest-verified Demo assessment replay catalog."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from eu_ai_act_sandbox.assessment.models import AssessmentResponse


@dataclass(frozen=True, slots=True)
class AssessmentReplay:
    fixture_id: str
    title: str
    sha256: str
    assessment: AssessmentResponse


TRUSTED_MANIFEST_SHA256 = "b4312e13579ac9d80ae3a78854e4b2745f439c6a583e4c4c598c57c3d4d910c8"


class ReplayCatalog:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else Path(__file__).resolve().parents[3] / "data" / "replays"

    def list_fixtures(self) -> tuple[dict[str, str], ...]:
        manifest = self._manifest()
        return tuple({"fixture_id": item["fixture_id"], "title": item["title"]} for item in manifest["fixtures"])

    def load(self, fixture_id: str) -> AssessmentReplay:
        manifest = self._manifest()
        item = next((entry for entry in manifest["fixtures"] if entry["fixture_id"] == fixture_id), None)
        if item is None:
            raise KeyError("unknown replay fixture")
        path = (self.root / item["path"]).resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError("replay fixture path escapes the catalog directory")
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != item["sha256"]:
            raise ValueError("replay fixture hash does not match the manifest")
        payload = json.loads(data)
        if payload.get("schema_version") != "assessment-replay-v1":
            raise ValueError("unsupported assessment replay schema")
        assessment = AssessmentResponse.model_validate(payload["assessment"])
        return AssessmentReplay(fixture_id, item["title"], digest, assessment)

    def _manifest(self) -> dict:
        path = self.root / "manifest.json"
        try:
            manifest_bytes = path.read_bytes()
            if hashlib.sha256(manifest_bytes).hexdigest() != TRUSTED_MANIFEST_SHA256:
                raise ValueError("replay manifest hash does not match the release-pinned digest")
            manifest = json.loads(manifest_bytes)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("replay manifest is missing or invalid") from exc
        if manifest.get("schema_version") != "demo-replay-manifest-v1":
            raise ValueError("unsupported replay manifest schema")
        if not isinstance(manifest.get("fixtures"), list):
            raise ValueError("replay manifest fixture list is invalid")
        return manifest
