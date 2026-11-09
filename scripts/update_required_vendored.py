"""Update the PrairieLearn-derived vendor packages as one logical unit."""

from __future__ import annotations

import subprocess
from pathlib import Path

from pl_vendor import VendorError, VendorProject

REPOSITORY = Path(__file__).resolve().parents[1]
REQUIRED_PACKAGES = (
    "prairielearn-schemas",
    "prairielearn-htmlmustache",
)
MANAGED_PATHS = (
    "plvendor.lock",
    ".prairielearn/schemas",
    ".htmlmustache",
)
MAX_UPDATE_ATTEMPTS = 3


def ensure_managed_paths_are_clean() -> None:
    result = subprocess.run(
        ["git", "status", "--short", "--", *MANAGED_PATHS],
        cwd=REPOSITORY,
        check=True,
        capture_output=True,
        text=True,
    )
    if changes := result.stdout.strip():
        raise SystemExit(
            "Refusing to overwrite changes in required vendored files:\n" + changes
        )


def required_revisions(project: VendorProject) -> dict[str, str]:
    try:
        packages = project.list(*REQUIRED_PACKAGES)
    except VendorError as exc:
        raise SystemExit(str(exc)) from exc

    revisions: dict[str, str] = {}
    for package in packages:
        assert package.revision is not None
        revisions[package.name] = package.revision
    return revisions


def main() -> None:
    ensure_managed_paths_are_clean()
    project = VendorProject.discover(REPOSITORY)
    revisions: dict[str, str] = {}

    for attempt in range(1, MAX_UPDATE_ATTEMPTS + 1):
        for package in REQUIRED_PACKAGES:
            project.update(package)

        revisions = required_revisions(project)
        if len(set(revisions.values())) == 1:
            revision = next(iter(revisions.values()))
            print(f"Required vendored packages are aligned at {revision}.")
            return

        if attempt < MAX_UPDATE_ATTEMPTS:
            print(
                "PrairieLearn advanced during the update; retrying the package group."
            )

    details = ", ".join(f"{name}={revision}" for name, revision in revisions.items())
    raise SystemExit(
        f"Required vendored packages did not converge after "
        f"{MAX_UPDATE_ATTEMPTS} attempts: {details}"
    )


if __name__ == "__main__":
    main()
