from __future__ import annotations

import io
from pathlib import Path

from pl_vendor import VendorProject

REPOSITORY = Path(__file__).resolve().parents[2]


def test_repository_manifest_and_lock_use_published_interface():
    project = VendorProject.discover(REPOSITORY)
    packages = project.list()

    assert [package.name for package in packages] == [
        "prairielearn-schemas",
        "prairielearn-htmlmustache",
    ]
    assert all(package.revision is not None for package in packages)
    assert [package.path.as_posix() for package in packages] == [
        ".prairielearn/schemas",
        ".htmlmustache",
    ]


def test_repository_lock_passes_published_project_check():
    output = io.StringIO()
    project = VendorProject.discover(REPOSITORY, output=output)

    assert not project.lock(check=True)
    assert output.getvalue() == "The lockfile is up to date.\n"
