# tests/test_task.py

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest


PARENT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PARENT_DIR))

import task  # noqa: E402


@pytest.fixture()
def isolated_paths(tmp_path, monkeypatch):
    tasklists_dir = tmp_path / "tasklists"
    latest_dir = tasklists_dir / "_latest"
    rules_path = tmp_path / "data" / "rules.md"
    rules_path.parent.mkdir(parents=True)
    rules_path.write_text(
        "\n".join(
            [
                "| Rule ID | Rule |",
                "|---|---|",
                "| R001 | First task |",
                "| R002 | Second task |",
                "",
                "not a table row",
                "| R003 | Third task |",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(task, "TASKLISTS_DIR", tasklists_dir)
    monkeypatch.setattr(task, "LATEST_DIR", latest_dir)
    monkeypatch.setattr(task, "RULES_PATH", rules_path)

    return {
        "tasklists_dir": tasklists_dir,
        "latest_dir": latest_dir,
        "rules_path": rules_path,
    }


def test_is_rule_row_filters_header_separator_and_non_table_rows():
    assert task.is_rule_row("| R001 | Do thing |") is True

    assert task.is_rule_row("not a row") is False
    assert task.is_rule_row("|---|---|") is False
    assert task.is_rule_row("| Rule ID | Rule |") is False
    assert task.is_rule_row("  | Rule ID | Rule |") is False


@pytest.mark.parametrize(
    "value",
    [
        "alpha",
        "alpha-1",
        "alpha_1",
        "alpha.1",
        "ABC_123.-xyz",
    ],
)
def test_validate_component_accepts_safe_values(value):
    assert task.validate_component(value, "Name") == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        ".",
        "..",
        "a/b",
        "../x",
        "name with spaces",
        "name\nx",
        "name:x",
    ],
)
def test_validate_component_rejects_unsafe_values(value):
    with pytest.raises(ValueError, match="must contain only"):
        task.validate_component(value, "Name")


def test_make_run_id_uses_expected_utc_timestamp_shape():
    run_id = task.make_run_id()

    assert run_id.endswith("Z")
    assert len(run_id) == len("20260102T030405123456Z")
    assert "T" in run_id


def test_create_run_root_creates_private_run_directory(isolated_paths):
    run_id, run_root = task.create_run_root()

    assert run_root == isolated_paths["tasklists_dir"] / run_id
    assert run_root.is_dir()
    assert run_root.stat().st_mode & 0o777 == 0o700


def test_get_tasklist_path_validates_name_and_run_id(isolated_paths):
    path = task.get_tasklist_path("my-list", "20260101T000000000000Z")

    assert path == (
        isolated_paths["tasklists_dir"]
        / "20260101T000000000000Z"
        / "my-list"
        / "tasks.txt"
    )

    with pytest.raises(ValueError):
        task.get_tasklist_path("../bad", "run")

    with pytest.raises(ValueError):
        task.get_tasklist_path("good", "../bad")


def test_get_latest_pointer_path_validates_name(isolated_paths):
    path = task.get_latest_pointer_path("queue")

    assert path == isolated_paths["latest_dir"] / "queue.txt"

    with pytest.raises(ValueError):
        task.get_latest_pointer_path("../bad")


def test_latest_pointer_round_trip(isolated_paths):
    task.update_latest_pointer("queue", "run-001")

    pointer_path = isolated_paths["latest_dir"] / "queue.txt"

    assert pointer_path.read_text(encoding="utf-8") == "run-001\n"
    assert task.get_latest_run_id("queue") == "run-001"


def test_get_latest_run_id_raises_when_missing(isolated_paths):
    with pytest.raises(FileNotFoundError, match="No latest run found"):
        task.get_latest_run_id("missing")


def test_get_latest_run_id_rejects_tampered_pointer(isolated_paths):
    task.update_latest_pointer("queue", "run-001")
    pointer_path = isolated_paths["latest_dir"] / "queue.txt"
    pointer_path.write_text("../bad\n", encoding="utf-8")

    with pytest.raises(ValueError):
        task.get_latest_run_id("queue")


def test_read_tasks_returns_empty_for_missing_file(tmp_path):
    assert task.read_tasks(tmp_path / "missing.txt") == []


def test_write_and_read_tasks_round_trip(tmp_path):
    tasklist_path = tmp_path / "queue" / "tasks.txt"

    task.write_tasks(tasklist_path, ["task 1", "task 2"])

    assert tasklist_path.read_text(encoding="utf-8") == "task 1\ntask 2\n"
    assert task.read_tasks(tasklist_path) == ["task 1", "task 2"]


def test_write_tasks_writes_empty_file_for_empty_task_list(tmp_path):
    tasklist_path = tmp_path / "queue" / "tasks.txt"

    task.write_tasks(tasklist_path, [])

    assert tasklist_path.read_text(encoding="utf-8") == ""
    assert task.read_tasks(tasklist_path) == []


def test_read_tasks_ignores_blank_lines(tmp_path):
    tasklist_path = tmp_path / "tasks.txt"
    tasklist_path.write_text("task 1\n\n  \ntask 2\n", encoding="utf-8")

    assert task.read_tasks(tasklist_path) == ["task 1", "task 2"]


def test_initialise_tasklist_creates_tasks_and_latest_pointer(isolated_paths, capsys):
    task.initialise_tasklist("queue", "run-001")

    tasklist_path = isolated_paths["tasklists_dir"] / "run-001" / "queue" / "tasks.txt"
    pointer_path = isolated_paths["latest_dir"] / "queue.txt"

    assert tasklist_path.read_text(encoding="utf-8") == (
        "| R001 | First task |\n"
        "| R002 | Second task |\n"
        "| R003 | Third task |\n"
    )
    assert pointer_path.read_text(encoding="utf-8") == "run-001\n"

    output = capsys.readouterr().out
    assert "Initialised" in output
    assert "with 3 tasks" in output
    assert "Run ID: run-001" in output


def test_initialise_tasklist_auto_creates_run_id(isolated_paths, capsys):
    task.initialise_tasklist("queue")

    output = capsys.readouterr().out
    assert "Run ID:" in output

    latest = task.get_latest_run_id("queue")
    tasklist_path = isolated_paths["tasklists_dir"] / latest / "queue" / "tasks.txt"

    assert tasklist_path.exists()


def test_initialise_tasklist_raises_when_rules_missing(isolated_paths, monkeypatch):
    monkeypatch.setattr(task, "RULES_PATH", isolated_paths["rules_path"].parent / "missing.md")

    with pytest.raises(FileNotFoundError, match="Rules file not found"):
        task.initialise_tasklist("queue", "run-001")


def test_initialise_tasklist_raises_when_tasklist_already_exists(isolated_paths):
    task.initialise_tasklist("queue", "run-001")

    with pytest.raises(FileExistsError, match="Task list already exists"):
        task.initialise_tasklist("queue", "run-001")


def test_get_next_task_uses_latest_run_and_removes_first_task(isolated_paths, capsys):
    task.initialise_tasklist("queue", "run-001")
    capsys.readouterr()

    task.get_next_task("queue")

    output = capsys.readouterr().out.strip()
    tasklist_path = isolated_paths["tasklists_dir"] / "run-001" / "queue" / "tasks.txt"

    assert output == "| R001 | First task |"
    assert task.read_tasks(tasklist_path) == [
        "| R002 | Second task |",
        "| R003 | Third task |",
    ]


def test_get_next_task_uses_explicit_run_id(isolated_paths, capsys):
    task.initialise_tasklist("queue", "run-001")
    task.initialise_tasklist("queue", "run-002")
    capsys.readouterr()

    task.get_next_task("queue", "run-001")

    assert capsys.readouterr().out.strip() == "| R001 | First task |"
    assert task.read_tasks(
        isolated_paths["tasklists_dir"] / "run-001" / "queue" / "tasks.txt"
    ) == [
        "| R002 | Second task |",
        "| R003 | Third task |",
    ]
    assert task.read_tasks(
        isolated_paths["tasklists_dir"] / "run-002" / "queue" / "tasks.txt"
    ) == [
        "| R001 | First task |",
        "| R002 | Second task |",
        "| R003 | Third task |",
    ]


def test_get_next_task_prints_all_completed_when_empty(isolated_paths, capsys):
    task.initialise_tasklist("queue", "run-001")

    tasklist_path = isolated_paths["tasklists_dir"] / "run-001" / "queue" / "tasks.txt"
    task.write_tasks(tasklist_path, [])

    capsys.readouterr()

    task.get_next_task("queue", "run-001")

    assert capsys.readouterr().out.strip() == "All tasks completed"


def test_get_next_task_raises_when_tasklist_missing(isolated_paths):
    with pytest.raises(FileNotFoundError, match="Task list not found"):
        task.get_next_task("queue", "run-001")


def test_task_lock_creates_and_removes_lock_directory(tmp_path):
    task_dir = tmp_path / "queue"
    task_dir.mkdir()

    with task.task_lock(task_dir):
        assert (task_dir / ".lock").is_dir()

    assert not (task_dir / ".lock").exists()


def test_task_lock_times_out_when_lock_exists(tmp_path, monkeypatch):
    task_dir = tmp_path / "queue"
    lock_dir = task_dir / ".lock"

    task_dir.mkdir()
    lock_dir.mkdir()

    monkeypatch.setattr(task, "LOCK_TIMEOUT_SECONDS", 0.01)

    start = time.monotonic()

    with pytest.raises(TimeoutError, match="Timed out waiting for task lock"):
        with task.task_lock(task_dir):
            pass

    assert time.monotonic() - start < 1


def test_build_parser_accepts_positional_name():
    parser = task.build_parser()

    args = parser.parse_args(["queue", "--get"])

    assert args.name == "queue"
    assert args.name_flag is None
    assert args.get is True
    assert args.start is False


def test_build_parser_accepts_name_flag():
    parser = task.build_parser()

    args = parser.parse_args(["--f", "queue", "--start", "--run-id", "run-001"])

    assert args.name is None
    assert args.name_flag == "queue"
    assert args.start is True
    assert args.run_id == "run-001"


def test_main_initialises_by_default(isolated_paths, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["task.py", "queue", "--run-id", "run-001"])

    task.main()

    assert (isolated_paths["tasklists_dir"] / "run-001" / "queue" / "tasks.txt").exists()
    assert "Initialised" in capsys.readouterr().out


def test_main_initialises_with_start(isolated_paths, monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["task.py", "queue", "--run-id", "run-001", "--start"],
    )

    task.main()

    assert (isolated_paths["tasklists_dir"] / "run-001" / "queue" / "tasks.txt").exists()
    assert "Initialised" in capsys.readouterr().out


def test_main_gets_task(isolated_paths, monkeypatch, capsys):
    task.initialise_tasklist("queue", "run-001")
    capsys.readouterr()

    monkeypatch.setattr(
        sys,
        "argv",
        ["task.py", "queue", "--run-id", "run-001", "--get"],
    )

    task.main()

    assert capsys.readouterr().out.strip() == "| R001 | First task |"


def test_main_prefers_name_flag_over_positional_name(isolated_paths, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["task.py", "positional-name", "--f", "flag-name", "--run-id", "run-001"],
    )

    task.main()

    assert (
        isolated_paths["tasklists_dir"] / "run-001" / "flag-name" / "tasks.txt"
    ).exists()
    assert not (
        isolated_paths["tasklists_dir"] / "run-001" / "positional-name" / "tasks.txt"
    ).exists()


def test_main_exits_with_error_for_missing_name(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["task.py"])

    with pytest.raises(SystemExit) as exc:
        task.main()

    assert exc.value.code == 2
    assert "Task list name required" in capsys.readouterr().err


def test_main_exits_with_error_for_validation_failure(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["task.py", "../bad"])

    with pytest.raises(SystemExit) as exc:
        task.main()

    captured = capsys.readouterr()

    assert exc.value.code == 1
    assert "Error:" in captured.err
    assert "Task list name must contain only" in captured.err
