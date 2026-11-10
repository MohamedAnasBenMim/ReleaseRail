import json
from pathlib import Path

from .controller import DeploymentController, Release


def main() -> None:
    controller = DeploymentController(
        Path("artifacts/deployment-state.json"), lambda release: "faulty" not in release.version
    )
    controller.deploy(Release("1.0.0", "sha256:stable"))
    failed = controller.deploy(Release("1.1.0-faulty", "sha256:broken"))
    report = {
        "faulty_release": failed.version,
        "final_status": failed.status,
        "active_after_rollback": controller.active.version if controller.active else None,
        "detection_ms": failed.detection_ms,
        "recovery_ms": failed.recovery_ms,
    }
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/rollback-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
