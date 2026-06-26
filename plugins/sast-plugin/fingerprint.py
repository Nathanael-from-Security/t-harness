#!/usr/bin/env python3
"""Build deterministic security finding fingerprints for PHP source."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_PLUGIN_ROOT = "server/totara/webhook"
VULN_CLASS_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
IDENT_RE = re.compile(r"[A-Za-z_\x80-\xff][A-Za-z0-9_\x80-\xff]*")
CLASS_LIKE = {"class", "trait", "interface", "enum"}
NAMED_SCOPE_KINDS = {"class", "trait", "interface", "enum", "function", "method"}


@dataclass
class Token:
    kind: str
    value: str
    line: int
    depth: int = 0


@dataclass
class Scope:
    kind: str
    name: str
    start_line: int
    body_depth: int
    end_line: int | None = None
    class_name: str | None = None

    def contains(self, line: int) -> bool:
        if self.end_line is None:
            return self.start_line <= line
        return self.start_line <= line <= self.end_line


def validate_vuln_class(value: str) -> str:
    if not VULN_CLASS_RE.fullmatch(value):
        raise ValueError("vuln-class must be kebab-case using lowercase letters, numbers, and dashes")
    return value


def normalise_path_text(value: str) -> str:
    return value.replace("\\", "/").lstrip("./")


def compute_plugin_relative_path(source_path: Path, plugin_root: str) -> str:
    raw_path = normalise_path_text(str(source_path))
    raw_root = normalise_path_text(plugin_root).rstrip("/")
    default_root_prefix = f"{DEFAULT_PLUGIN_ROOT}/"

    try:
        resolved_path = source_path.resolve()
        resolved_root = Path(plugin_root).resolve()
        relative_path = resolved_path.relative_to(resolved_root).as_posix()
        if relative_path.startswith(default_root_prefix):
            return relative_path[len(default_root_prefix) :]
        return relative_path
    except (OSError, ValueError):
        pass

    root_prefix = f"{raw_root}/"
    if raw_path.startswith(root_prefix):
        relative_path = raw_path[len(root_prefix) :]
        if relative_path.startswith(default_root_prefix):
            return relative_path[len(default_root_prefix) :]
        return relative_path

    marker = f"/{root_prefix}"
    marker_index = raw_path.find(marker)
    if marker_index >= 0:
        relative_path = raw_path[marker_index + len(marker) :]
        if relative_path.startswith(default_root_prefix):
            return relative_path[len(default_root_prefix) :]
        return relative_path

    if not source_path.is_absolute():
        return raw_path

    raise ValueError(
        f"path is absolute and is not under plugin root {plugin_root!r}; "
        "pass --plugin-root or use a plugin-relative --path"
    )


def resolve_source_path(source_path: Path, plugin_root: str) -> Path:
    if source_path.is_absolute():
        return source_path

    candidates = [Path(plugin_root) / source_path, source_path]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def consume_quoted_string(source: str, index: int, quote: str, line: int) -> tuple[str, int, int]:
    index += 1
    value_chars: list[str] = []
    while index < len(source):
        char = source[index]
        if char == "\\":
            if index + 1 < len(source):
                value_chars.append(source[index + 1])
                index += 2
                continue
        if char == quote:
            return "".join(value_chars), index + 1, line
        if char == "\n":
            line += 1
        value_chars.append(char)
        index += 1
    return "".join(value_chars), index, line


def consume_comment(source: str, index: int, line: int) -> tuple[int, int]:
    if source.startswith("/*", index):
        index += 2
        while index < len(source) and not source.startswith("*/", index):
            if source[index] == "\n":
                line += 1
            index += 1
        return min(index + 2, len(source)), line

    while index < len(source) and source[index] != "\n":
        index += 1
    return index, line


def lex_php(source: str) -> list[Token]:
    tokens: list[Token] = []
    index = 0
    line = 1

    while index < len(source):
        char = source[index]

        if char in " \t\r":
            index += 1
            continue
        if char == "\n":
            line += 1
            index += 1
            continue
        if source.startswith("//", index) or source.startswith("/*", index) or char == "#":
            index, line = consume_comment(source, index, line)
            continue
        if source.startswith("<?", index):
            end = source.find("?>", index + 2)
            # Treat PHP open tags as syntax, not as a string/comment region.
            tokens.append(Token("symbol", "<?", line))
            index += 2
            continue
        if source.startswith("?>", index):
            tokens.append(Token("symbol", "?>", line))
            index += 2
            continue
        if char in {"'", '"'}:
            start_line = line
            value, index, line = consume_quoted_string(source, index, char, line)
            tokens.append(Token("string", value, start_line))
            continue
        if char == "$":
            match = IDENT_RE.match(source, index + 1)
            if match:
                tokens.append(Token("variable", f"${match.group(0)}", line))
                index = match.end()
                continue
        match = IDENT_RE.match(source, index)
        if match:
            value = match.group(0)
            tokens.append(Token("identifier", value, line))
            index = match.end()
            continue
        if index + 2 <= len(source) and source[index : index + 3] in {"===", "!=="}:
            tokens.append(Token("operator", source[index : index + 3], line))
            index += 3
            continue
        if index + 1 < len(source) and source[index : index + 2] in {"==", "!=", "::", "=>", "->", "<=", ">="}:
            tokens.append(Token("operator", source[index : index + 2], line))
            index += 2
            continue

        tokens.append(Token("symbol", char, line))
        index += 1

    annotate_depths(tokens)
    return tokens


def annotate_depths(tokens: list[Token]) -> None:
    depth = 0
    for token in tokens:
        if token.value == "}":
            token.depth = depth
            depth = max(0, depth - 1)
            continue
        token.depth = depth
        if token.value == "{":
            depth += 1


def next_non_modifier_identifier(tokens: list[Token], index: int) -> tuple[str | None, int]:
    modifiers = {
        "public",
        "protected",
        "private",
        "static",
        "abstract",
        "final",
        "readonly",
        "&",
    }
    index += 1
    while index < len(tokens):
        token = tokens[index]
        value = token.value.lower()
        if value in modifiers:
            index += 1
            continue
        if token.kind == "identifier":
            return token.value, index
        return None, index
    return None, index


def nearest_active_class(scopes: list[Scope], brace_depth: int) -> Scope | None:
    classes = [
        scope
        for scope in scopes
        if scope.kind in CLASS_LIKE and scope.body_depth <= brace_depth and scope.end_line is None
    ]
    if not classes:
        return None
    return max(classes, key=lambda scope: scope.body_depth)


def nearest_active_anon_class(scopes: list[Scope], brace_depth: int) -> Scope | None:
    anon_classes = [
        scope
        for scope in scopes
        if scope.kind == "anon_class" and scope.body_depth <= brace_depth and scope.end_line is None
    ]
    if not anon_classes:
        return None
    return max(anon_classes, key=lambda scope: scope.body_depth)


def parse_scopes(tokens: list[Token]) -> list[Scope]:
    scopes: list[Scope] = []
    active: list[Scope] = []
    pending: Scope | None = None
    brace_depth = 0

    for index, token in enumerate(tokens):
        value = token.value
        lower = value.lower()

        if value == "}":
            for scope in reversed(active):
                if scope.body_depth == brace_depth and scope.end_line is None:
                    scope.end_line = token.line
            active = [scope for scope in active if scope.end_line is None]
            brace_depth = max(0, brace_depth - 1)
            continue

        if value == "{":
            brace_depth += 1
            if pending is not None:
                pending.body_depth = brace_depth
                active.append(pending)
                scopes.append(pending)
                pending = None
            continue

        if value == ";":
            if pending is not None and pending.kind in {"function", "method"}:
                pending.end_line = token.line
                scopes.append(pending)
            pending = None
            continue

        if token.kind == "identifier" and lower in CLASS_LIKE:
            name, name_index = next_non_modifier_identifier(tokens, index)
            if name and tokens[name_index].value.lower() not in {"extends", "implements"}:
                pending = Scope(lower, name, token.line, brace_depth + 1)
            else:
                pending = Scope("anon_class", "<anon-class>", token.line, brace_depth + 1)
            continue

        if token.kind == "identifier" and lower == "function":
            name, _ = next_non_modifier_identifier(tokens, index)
            if not name:
                continue
            if nearest_active_anon_class(active, brace_depth) is not None:
                continue
            active_class = nearest_active_class(active, brace_depth)
            if active_class is not None and brace_depth == active_class.body_depth:
                pending = Scope("method", name, token.line, brace_depth + 1, class_name=active_class.name)
            else:
                pending = Scope("function", name, token.line, brace_depth + 1)
            continue

    last_line = tokens[-1].line if tokens else 1
    for scope in scopes:
        if scope.end_line is None:
            scope.end_line = last_line
    return scopes


def find_matching_brace(tokens: list[Token], open_index: int) -> int | None:
    depth = 0
    for index in range(open_index, len(tokens)):
        if tokens[index].value == "{":
            depth += 1
        elif tokens[index].value == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def find_statement_end(tokens: list[Token], start_index: int) -> int:
    for index in range(start_index, len(tokens)):
        if tokens[index].value in {";", "}"}:
            return index
    return len(tokens) - 1


def extract_condition_string_label(tokens: list[Token], start_index: int) -> str | None:
    depth = 0
    seen_open = False
    for index in range(start_index, len(tokens)):
        token = tokens[index]
        if token.value == "(":
            seen_open = True
            depth += 1
            continue
        if token.value == ")":
            depth -= 1
            if seen_open and depth == 0:
                return None
            continue
        if seen_open and depth > 0 and token.kind == "string":
            return token.value
    return None


def file_scope_case_symbol(tokens: list[Token], line: int) -> tuple[str | None, int | None]:
    first_dispatch_line: int | None = None

    for index, token in enumerate(tokens):
        lower = token.value.lower()
        if lower == "case":
            label_token = tokens[index + 1] if index + 1 < len(tokens) else None
            if label_token is None or label_token.kind != "string":
                continue
            first_dispatch_line = min(first_dispatch_line or token.line, token.line)
            end_index = len(tokens) - 1
            for probe in range(index + 1, len(tokens)):
                probe_token = tokens[probe]
                if probe_token.depth == token.depth and probe_token.value.lower() in {"case", "default"}:
                    end_index = probe - 1
                    break
                if probe_token.value == "}" and probe_token.depth == token.depth:
                    end_index = probe
                    break
            end_line = tokens[end_index].line
            if token.line <= line <= end_line:
                return f"<case:{label_token.value}>", first_dispatch_line

        if lower in {"if", "elseif"}:
            label = extract_condition_string_label(tokens, index)
            if not label:
                continue
            first_dispatch_line = min(first_dispatch_line or token.line, token.line)
            body_start = None
            for probe in range(index + 1, len(tokens)):
                if tokens[probe].value == "{":
                    body_start = probe
                    break
                if tokens[probe].value == ";":
                    body_start = probe
                    break
            if body_start is None:
                continue
            if tokens[body_start].value == "{":
                end_index = find_matching_brace(tokens, body_start) or body_start
            else:
                end_index = find_statement_end(tokens, body_start)
            if token.line <= line <= tokens[end_index].line:
                return f"<case:{label}>", first_dispatch_line

    return None, first_dispatch_line


def anon_class_symbol(scopes: list[Scope], line: int) -> str | None:
    matches = [scope for scope in scopes if scope.kind == "anon_class" and scope.contains(line)]
    if matches:
        return "<anon-class>"
    return None


def primary_class_preamble_symbol(scopes: list[Scope], line: int) -> str | None:
    class_scopes = [scope for scope in scopes if scope.kind in CLASS_LIKE]
    if len(class_scopes) != 1:
        return None

    primary_class = class_scopes[0]
    if line < primary_class.start_line:
        return primary_class.name
    return None


def resolve_symbol(source: str, line: int) -> str:
    tokens = lex_php(source)
    scopes = parse_scopes(tokens)
    named_matches = [
        scope for scope in scopes if scope.kind in NAMED_SCOPE_KINDS and scope.contains(line)
    ]

    if named_matches:
        scope = max(named_matches, key=lambda item: item.body_depth)
        if scope.kind == "method":
            return f"{scope.class_name}::{scope.name}"
        if scope.kind == "function":
            return scope.name
        return scope.name

    case_symbol, first_dispatch_line = file_scope_case_symbol(tokens, line)
    if case_symbol:
        return case_symbol

    preamble_symbol = primary_class_preamble_symbol(scopes, line)
    if preamble_symbol:
        return preamble_symbol

    anon_symbol = anon_class_symbol(scopes, line)
    if anon_symbol:
        return anon_symbol

    if first_dispatch_line is not None and line < first_dispatch_line:
        return "<setup>"
    return "<script>"


def build_fingerprint(vuln_class: str, source_path: Path, plugin_root: str, line: int) -> dict[str, object]:
    vuln_class = validate_vuln_class(vuln_class)
    source_path = resolve_source_path(source_path, plugin_root)
    if not source_path.exists():
        raise FileNotFoundError(f"file not found: {source_path.resolve(strict=False)}")

    source = source_path.read_text(encoding="utf-8")
    total_lines = len(source.splitlines()) or 1
    if line < 1 or line > total_lines:
        raise ValueError(f"line must be between 1 and {total_lines}")

    plugin_relative_path = compute_plugin_relative_path(source_path, plugin_root)
    symbol = resolve_symbol(source, line)
    fingerprint = f"{vuln_class}:{plugin_relative_path}#{symbol}"

    return {
        "fingerprint": fingerprint,
        "vuln_class": vuln_class,
        "plugin_relative_path": plugin_relative_path,
        "symbol": symbol,
        "line": line,
        "partial": False,
        "unresolved": [],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic finding fingerprint from a PHP file, vulnerability class, "
            "and 1-based line number."
        )
    )
    parser.add_argument("--vuln-class", required=True, help="Kebab-case vulnerability class")
    parser.add_argument("--path", required=True, help="PHP file path to read and fingerprint")
    parser.add_argument("--line", required=True, type=int, help="1-based finding line number")
    parser.add_argument(
        "--plugin-root",
        default=DEFAULT_PLUGIN_ROOT,
        help=f"Plugin root used for relative paths (default: {DEFAULT_PLUGIN_ROOT})",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON output")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        result = build_fingerprint(args.vuln_class, Path(args.path), args.plugin_root, args.line)
    except (FileNotFoundError, OSError, UnicodeDecodeError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(result["fingerprint"])


if __name__ == "__main__":
    main()
