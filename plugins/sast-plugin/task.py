#!/usr/bin/env python3
"""Simple named task queues backed by timestamped folders under /tmp/tasklists/."""

from __future__ import annotations

import argparse
import os
import re
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


TASKLISTS_DIR = Path("/tmp/tasklists")
LATEST_DIR = TASKLISTS_DIR / "_latest"
RULES_PATH = Path(__file__).resolve().parent / "data" / "rules.md"
SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9_.-]+$")
LOCK_TIMEOUT_SECONDS = 30


def is_rule_row(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return False
    if stripped.startswith("|---"):
        return False
    if stripped.startswith("| Rule ID |"):
        return False
    return True


def validate_component(value: str, label: str) -> str:
    if not value or value in {".", ".."} or not SAFE_COMPONENT.fullmatch(value):
        raise ValueError(f"{label} must contain only letters, numbers, dots, dashes, and underscores")
    return value


def make_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def create_run_root() -> tuple[str, Path]:
    TASKLISTS_DIR.mkdir(parents=True, exist_ok=True)

    while True:
        run_id = make_run_id()
        run_root = TASKLISTS_DIR / run_id
        try:
            run_root.mkdir(mode=0o700, exist_ok=False)
            return run_id, run_root
        except FileExistsError:
            time.sleep(0.001)


def get_tasklist_path(name: str, run_id: str) -> Path:
    safe_name = validate_component(name, "Task list name")
    safe_run_id = validate_component(run_id, "Run ID")
    return TASKLISTS_DIR / safe_run_id / safe_name / "tasks.txt"


def get_latest_pointer_path(name: str) -> Path:
    safe_name = validate_component(name, "Task list name")
    return LATEST_DIR / f"{safe_name}.txt"


def update_latest_pointer(name: str, run_id: str) -> None:
    pointer_path = get_latest_pointer_path(name)
    LATEST_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = pointer_path.with_name(f"{pointer_path.name}.{os.getpid()}.tmp")
    temp_path.write_text(f"{run_id}\n", encoding="utf-8")
    temp_path.replace(pointer_path)


def get_latest_run_id(name: str) -> str:
    pointer_path = get_latest_pointer_path(name)
    if not pointer_path.exists():
        raise FileNotFoundError(
            f"No latest run found for {name!r}. Run with --start first or pass --run-id."
        )

    run_id = pointer_path.read_text(encoding="utf-8").strip()
    return validate_component(run_id, "Run ID")


@contextmanager
def task_lock(task_dir: Path):
    lock_dir = task_dir / ".lock"
    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS

    while True:
        try:
            lock_dir.mkdir()
            break
        except FileExistsError:
            if time.monotonic() > deadline:
                raise TimeoutError(f"Timed out waiting for task lock: {lock_dir}")
            time.sleep(0.05)

    try:
        yield
    finally:
        lock_dir.rmdir()


def read_tasks(tasklist_path: Path) -> list[str]:
    if not tasklist_path.exists():
        return []
    return [line.rstrip("\n") for line in tasklist_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_tasks(tasklist_path: Path, tasks: list[str]) -> None:
    tasklist_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = tasklist_path.with_name(f"{tasklist_path.name}.{os.getpid()}.tmp")
    temp_path.write_text("\n".join(tasks) + ("\n" if tasks else ""), encoding="utf-8")
    temp_path.replace(tasklist_path)


def initialise_tasklist(name: str, run_id: str | None = None) -> None:
    if not RULES_PATH.exists():
        raise FileNotFoundError(f"Rules file not found: {RULES_PATH}")

    if run_id is None:
        run_id, run_root = create_run_root()
    else:
        run_id = validate_component(run_id, "Run ID")
        run_root = TASKLISTS_DIR / run_id
        run_root.mkdir(mode=0o700, parents=True, exist_ok=True)

    tasklist_path = get_tasklist_path(name, run_id)
    try:
        tasklist_path.parent.mkdir(mode=0o700, exist_ok=False)
    except FileExistsError as exc:
        raise FileExistsError(f"Task list already exists for run {run_id}: {tasklist_path}") from exc

    tasks = [
        line.strip()
        for line in RULES_PATH.read_text(encoding="utf-8").splitlines()
        if is_rule_row(line)
    ]
    write_tasks(tasklist_path, tasks)
    update_latest_pointer(name, run_id)
    print(f"Initialised {tasklist_path} with {len(tasks)} tasks")
    print(f"Run ID: {run_id}")


def get_next_task(name: str, run_id: str | None = None) -> None:
    if run_id is None:
        run_id = get_latest_run_id(name)

    tasklist_path = get_tasklist_path(name, run_id)
    if not tasklist_path.exists():
        raise FileNotFoundError(f"Task list not found: {tasklist_path}")

    with task_lock(tasklist_path.parent):
        tasks = read_tasks(tasklist_path)
        if not tasks:
            print("All tasks completed")
            return

        next_task = tasks.pop(0)
        write_tasks(tasklist_path, tasks)
    print(next_task)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Task queue manager.\n\n"
            "Initialise: task.py --f NAME\n"
            "Get+remove next task from latest run: task.py --f NAME --get\n"
            "Get+remove next task from a specific run: task.py --f NAME --run-id RUN_ID --get\n"
            "Start a fresh timestamped run: task.py --f NAME --start\n\n"
            "NAME can also be passed positionally: task.py NAME [--get|--start]\n"
            "Tasklists are stored in /tmp/tasklists/RUN_ID/NAME/tasks.txt"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("name", nargs="?", help="Task list name")
    parser.add_argument("--f", dest="name_flag", help="Task list name")
    parser.add_argument("--run-id", help="Timestamped run ID. Defaults to latest run for NAME when using --get.")
    parser.add_argument("--get", action="store_true", help="Return and remove the next remaining task")
    parser.add_argument("--start", action="store_true", help="Initialise a fresh timestamped tasklist (reload from rules.md)")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    name = args.name_flag or args.name

    if not name:
        parser.error("Task list name required: use NAME or --f NAME")

    try:
        if args.start:
            initialise_tasklist(name, args.run_id)
        elif args.get:
            get_next_task(name, args.run_id)
        else:
            initialise_tasklist(name, args.run_id)
    except (FileExistsError, FileNotFoundError, TimeoutError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
