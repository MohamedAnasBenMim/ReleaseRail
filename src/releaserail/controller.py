from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol


class ReleaseStatus(StrEnum):
    PENDING = "pending"
    HEALTHY = "healthy"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass(slots=True)
class Release:
    version: str
    image_digest: str
    status: ReleaseStatus = ReleaseStatus.PENDING
    detection_ms: float | None = None
    recovery_ms: float | None = None


class HealthProbe(Protocol):
    def __call__(self, release: Release) -> bool: ...


class DeploymentController:
    def __init__(self, state_path: Path, health_probe: HealthProbe, attempts: int = 3) -> None:
        self.state_path = state_path
        self.health_probe = health_probe
        self.attempts = attempts
        self.history: list[Release] = []
        self.active: Release | None = None

    def deploy(self, candidate: Release) -> Release:
        previous = self.active
        started = time.perf_counter()
        self.history.append(candidate)
        for _ in range(self.attempts):
            if self.health_probe(candidate):
                candidate.status = ReleaseStatus.HEALTHY
                self.active = candidate
                self._persist()
                return candidate
        candidate.status = ReleaseStatus.FAILED
        candidate.detection_ms = round((time.perf_counter() - started) * 1000, 4)
        if previous:
            rollback_started = time.perf_counter()
            previous.status = ReleaseStatus.HEALTHY
            self.active = previous
            candidate.status = ReleaseStatus.ROLLED_BACK
            candidate.recovery_ms = round((time.perf_counter() - rollback_started) * 1000, 4)
        self._persist()
        return candidate

    def reconcile(self, desired_version: str, digest: str) -> Release:
        if (
            self.active
            and self.active.version == desired_version
            and self.active.image_digest == digest
        ):
            return self.active
        return self.deploy(Release(desired_version, digest))

    def _persist(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "active": asdict(self.active) if self.active else None,
            "history": [asdict(release) for release in self.history],
        }
        self.state_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
