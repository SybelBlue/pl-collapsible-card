"""Run named shell checks in parallel and present their results with Rich."""

from __future__ import annotations

import argparse
import subprocess
import time
from collections.abc import Sequence
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TaskID, TextColumn, TimeElapsedColumn
from rich.text import Text


@dataclass(frozen=True)
class Check:
    name: str
    command: str


@dataclass(frozen=True)
class CheckResult:
    check: Check
    returncode: int
    stdout: str
    stderr: str


def run_check(check: Check) -> CheckResult:
    """Run one check and capture its output for an uncluttered live display."""
    try:
        process = subprocess.run(
            ["bash", "-c", check.command],
            check=False,
            capture_output=True,
            text=True,
            errors="replace",
        )
    except OSError as exc:
        return CheckResult(
            check=check,
            returncode=127,
            stdout="",
            stderr=str(exc),
        )

    return CheckResult(
        check=check,
        returncode=process.returncode,
        stdout=process.stdout,
        stderr=process.stderr,
    )


def output_panel(output: str, title: str, border_style: str) -> Panel:
    return Panel(
        Text.from_ansi(output.rstrip()),
        title=title,
        title_align="left",
        border_style=border_style,
    )


def print_result_output(result: CheckResult, console: Console) -> None:
    """Print useful captured output after the live progress display finishes."""
    if result.returncode == 0:
        if not result.stderr:
            return
        console.rule(f"[yellow]Notes from {escape(result.check.name)}[/yellow]")
        console.print(f"[dim]$ {escape(result.check.command)}[/dim]")
        console.print(output_panel(result.stderr, "stderr", "yellow"))
        return

    console.rule(f"[red]Failed: {escape(result.check.name)}[/red]")
    console.print(f"[dim]$ {escape(result.check.command)}[/dim]")
    if result.stdout:
        console.print(output_panel(result.stdout, "stdout", "red"))
    if result.stderr:
        console.print(output_panel(result.stderr, "stderr", "red"))
    if not result.stdout and not result.stderr:
        console.print("[dim]The command produced no output.[/dim]")


def run_checks(checks: Sequence[Check], console: Console) -> int:
    """Run checks concurrently, returning the first failing exit code in list order."""
    started = time.monotonic()
    console.print(
        Panel.fit(
            f"[bold]Project checks[/bold]\nRunning {len(checks)} checks in parallel",
            border_style="cyan",
        )
    )

    progress = Progress(
        SpinnerColumn(),
        TextColumn("{task.description}", justify="left"),
        TextColumn("{task.fields[status]}", justify="right"),
        TimeElapsedColumn(),
        console=console,
    )
    with progress, ThreadPoolExecutor(max_workers=len(checks)) as executor:
        futures: dict[Future[CheckResult], TaskID] = {}
        ordered_futures: list[Future[CheckResult]] = []
        for check in checks:
            task_id = progress.add_task(
                escape(check.name), total=None, status="[cyan]running[/cyan]"
            )
            future = executor.submit(run_check, check)
            futures[future] = task_id
            ordered_futures.append(future)

        for future in as_completed(futures):
            result = future.result()
            if result.returncode == 0:
                status = "[green]✓ passed[/green]"
            else:
                status = f"[red]✗ failed ({result.returncode})[/red]"
            progress.update(
                futures[future],
                total=1,
                completed=1,
                status=status,
            )

    results = [future.result() for future in ordered_futures]
    for result in results:
        print_result_output(result, console)

    failures = [result for result in results if result.returncode != 0]
    duration = time.monotonic() - started
    if failures:
        console.print(
            Panel.fit(
                f"[bold red]{len(failures)} of {len(checks)} checks failed[/bold red] "
                f"in {duration:.1f}s",
                title="Checks failed",
                border_style="red",
            )
        )
        return failures[0].returncode

    console.print(
        Panel.fit(
            f"[bold green]All {len(checks)} checks passed[/bold green] "
            f"in {duration:.1f}s",
            border_style="green",
        )
    )
    return 0


def parse_checks(raw_checks: Sequence[Sequence[str]]) -> list[Check]:
    return [Check(name=name, command=command) for name, command in raw_checks]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="append",
        nargs=2,
        required=True,
        metavar=("NAME", "COMMAND"),
        help="named shell command to run; may be repeated",
    )
    args = parser.parse_args(argv)
    return run_checks(parse_checks(args.check), Console())


if __name__ == "__main__":
    raise SystemExit(main())
