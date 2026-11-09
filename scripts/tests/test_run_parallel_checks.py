from __future__ import annotations

import io
import sys

from rich.console import Console

from scripts import run_parallel_checks


def test_run_checks_reports_successes() -> None:
    output = io.StringIO()
    console = Console(file=output, force_terminal=False, width=100)

    status = run_parallel_checks.run_checks(
        [
            run_parallel_checks.Check(
                "First check", f"{sys.executable} -c \"print('first output')\""
            ),
            run_parallel_checks.Check(
                "Second check", f"{sys.executable} -c \"print('second output')\""
            ),
        ],
        console,
    )

    rendered = output.getvalue()
    assert status == 0
    assert "First check" in rendered
    assert "Second check" in rendered
    assert "All 2 checks passed" in rendered
    assert "first output" not in rendered
    assert "second output" not in rendered


def test_run_checks_explains_failures_and_returns_first_failure() -> None:
    output = io.StringIO()
    console = Console(file=output, force_terminal=False, width=100)
    first_command = (
        f"{sys.executable} -c \"import sys; print('details'); "
        "print('problem', file=sys.stderr); sys.exit(3)\""
    )

    status = run_parallel_checks.run_checks(
        [
            run_parallel_checks.Check("Broken check", first_command),
            run_parallel_checks.Check(
                "Also broken", f'{sys.executable} -c "raise SystemExit(5)"'
            ),
        ],
        console,
    )

    rendered = output.getvalue()
    assert status == 3
    assert "Failed: Broken check" in rendered
    assert "details" in rendered
    assert "problem" in rendered
    assert "2 of 2 checks failed" in rendered


def test_successful_stderr_is_shown_without_stdout_noise() -> None:
    output = io.StringIO()
    console = Console(file=output, force_terminal=False, width=100)
    command = (
        f"{sys.executable} -c \"import sys; print('context'); "
        "print('warning', file=sys.stderr)\""
    )

    status = run_parallel_checks.run_checks(
        [run_parallel_checks.Check("Warning check", command)], console
    )

    rendered = output.getvalue()
    assert status == 0
    assert "Notes from Warning check" in rendered
    assert "╭─ stdout " not in rendered
    assert "warning" in rendered
