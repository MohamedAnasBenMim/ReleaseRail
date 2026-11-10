import json
from pathlib import Path

from releaserail.controller import DeploymentController, Release, ReleaseStatus


def test_healthy_release_becomes_active(tmp_path: Path) -> None:
    controller = DeploymentController(tmp_path / "state.json", lambda _release: True)
    release = controller.deploy(Release("1.0.0", "sha256:one"))
    assert release.status is ReleaseStatus.HEALTHY
    assert controller.active is release


def test_faulty_release_is_detected_and_rolled_back(tmp_path: Path) -> None:
    controller = DeploymentController(
        tmp_path / "state.json", lambda release: release.version != "bad"
    )
    stable = controller.deploy(Release("stable", "sha256:stable"))
    failed = controller.deploy(Release("bad", "sha256:bad"))
    assert failed.status is ReleaseStatus.ROLLED_BACK
    assert controller.active is stable
    assert failed.detection_ms is not None
    assert failed.recovery_ms is not None


def test_first_failed_release_has_no_rollback_target(tmp_path: Path) -> None:
    controller = DeploymentController(tmp_path / "state.json", lambda _release: False)
    failed = controller.deploy(Release("bad", "sha256:bad"))
    assert failed.status is ReleaseStatus.FAILED
    assert controller.active is None


def test_reconcile_is_idempotent(tmp_path: Path) -> None:
    controller = DeploymentController(tmp_path / "state.json", lambda _release: True)
    first = controller.reconcile("1.0", "sha256:one")
    second = controller.reconcile("1.0", "sha256:one")
    assert first is second
    assert len(controller.history) == 1


def test_state_is_persisted(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    DeploymentController(path, lambda _release: True).deploy(Release("1.0", "sha256:one"))
    payload = json.loads(path.read_text())
    assert payload["active"]["image_digest"] == "sha256:one"
