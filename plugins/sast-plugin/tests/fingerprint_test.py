from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fingerprint import build_fingerprint


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
PLUGIN_ROOT = DATA


def fingerprint(path: str, line: int, vuln_class: str = "sql-injection") -> str:
    result = build_fingerprint(vuln_class, DATA / path, str(PLUGIN_ROOT), line)
    return str(result["fingerprint"])


@pytest.mark.parametrize(
    ("line", "expected_symbol"),
    [
        (9, "data_sanitiser::sanitise_data"),
        (10, "data_sanitiser::sanitise_data"),
        (13, "data_sanitiser::sanitise_data"),
        (14, "data_sanitiser::sanitise_data"),
        (20, "data_sanitiser::create_instance"),
        (22, "data_sanitiser::create_instance"),
        (28, "data_sanitiser::__construct"),
        (34, "my_trait::apply"),
        (41, "webhook_auth::with_body"),
        (49, "WebhookStatus::label"),
        (50, "WebhookStatus::label"),
    ],
)
def test_named_class_like_symbols_and_unnamed_fallbacks(line, expected_symbol):
    assert fingerprint("symbol_cases.php", line) == f"sql-injection:symbol_cases.php#{expected_symbol}"


def test_class_body_declaration_anchors_to_class():
    assert fingerprint("symbol_cases.php", 6) == "sql-injection:symbol_cases.php#data_sanitiser"
    assert fingerprint("symbol_cases.php", 7) == "sql-injection:symbol_cases.php#data_sanitiser"


def test_free_and_nested_functions():
    assert fingerprint("symbol_cases.php", 56) == "sql-injection:symbol_cases.php#handle_webhook_error"
    assert fingerprint("symbol_cases.php", 57) == "sql-injection:symbol_cases.php#inner_helper"


def test_script_level_switch_case_anchor():
    assert fingerprint("symbol_cases.php", 64) == "sql-injection:symbol_cases.php#<case:delete>"
    assert fingerprint("symbol_cases.php", 67) == "sql-injection:symbol_cases.php#<case:create>"


def test_script_level_if_action_anchor():
    assert fingerprint("symbol_cases.php", 72) == "sql-injection:symbol_cases.php#<case:archive>"


def test_script_level_setup_and_script_fallback():
    assert fingerprint("symbol_cases.php", 2) == "sql-injection:symbol_cases.php#<setup>"
    assert fingerprint("symbol_cases.php", 76) == "sql-injection:symbol_cases.php#<script>"


def test_file_scope_if_without_action_string_uses_setup_then_script():
    assert fingerprint("script_cases.php", 4) == "sql-injection:script_cases.php#<setup>"
    assert fingerprint("script_cases.php", 11) == "sql-injection:script_cases.php#<script>"


def test_single_class_preamble_anchors_to_primary_class_current_policy():
    assert (
        fingerprint("single_class_preamble.php", 3)
        == "sql-injection:single_class_preamble.php#resend_totara_webhook_dlq_item"
    )


def test_interface_bodyless_method_expected_behavior():
    assert (
        fingerprint("symbol_cases.php", 40)
        == "sql-injection:symbol_cases.php#webhook_auth::authorise_request"
    )


def test_file_scope_anonymous_class_expected_behavior():
    assert fingerprint("anonymous_class.php", 3) == "sql-injection:anonymous_class.php#<anon-class>"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
