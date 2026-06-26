#!/usr/bin/env bash
# SEC-Manager scan script. This is an alternative to running the scan through the UI, and is intended for users who prefer the command line or want to integrate the scan into existing shell-based workflows.

# Usage:
#   ./run_sec_manager_scan.sh /path/to/repo/or/path
#
# Reports are written under:
#   /tmp/sec-agent/security/<timestamp>

set -euo pipefail

ORIGINAL_PARAM_PATH="${1:-.}"

if [[ ! -d "$ORIGINAL_PARAM_PATH" ]]; then
  echo "ERROR: Base path not found: $ORIGINAL_PARAM_PATH" >&2
  exit 1
fi

ORIGINAL_PARAM_PATH="$(cd "$ORIGINAL_PARAM_PATH" && pwd)"
PARAM_PATH=""

TIMESTAMP="$(date +"%d_%m_%Y_%H_%M_%S")"
REPORT_DIR="/tmp/sec-agent/security/$TIMESTAMP"

PLUGIN_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$REPORT_DIR/logs"

RED="$REPORT_DIR/red-team-report.md"
LINT="$REPORT_DIR/lint-task-report.md"
BLUE="$REPORT_DIR/blue-team-report.md"
FINAL="$REPORT_DIR/consolidated-review.md"

FINDINGS_MODEL="claude-opus-4-8"
CONSOLIDATION_MODEL="claude-haiku-4-5"

ALLOWED_TOOLS="Read,Grep,Glob,LS,Bash,Write"
OUT="json"

readonly_rules='
Do not run claude.
Do not run run_sec_manager_scan.sh.
Do not use Bash to start another agent.
Do not create another timestamped directory.
Bash may only be used for bounded repository inspection commands such as find, grep, wc, file, php -l, and jq.
Use the Write tool when writing the requested report file.
'

mkdir -p "$REPORT_DIR" "$LOG_DIR"

SOURCE_SNAPSHOT_DIR="$REPORT_DIR/source-snapshot"

create_source_snapshot() {
  if [[ -e "$SOURCE_SNAPSHOT_DIR" ]]; then
    echo "ERROR: Source snapshot already exists: $SOURCE_SNAPSHOT_DIR" >&2
    exit 1
  fi

  mkdir -p "$SOURCE_SNAPSHOT_DIR"

  if command -v rsync >/dev/null 2>&1; then
    rsync -a \
      --exclude='.git' \
      --exclude='.claude' \
      --exclude='.mypy_cache' \
      --exclude='.pytest_cache' \
      --exclude='node_modules' \
      "$ORIGINAL_PARAM_PATH"/ "$SOURCE_SNAPSHOT_DIR"/
  else
    (
      cd "$ORIGINAL_PARAM_PATH"
      tar \
        --exclude='./.git' \
        --exclude='./.claude' \
        --exclude='./.mypy_cache' \
        --exclude='./.pytest_cache' \
        --exclude='./node_modules' \
        -cf - .
    ) | tar -xf - -C "$SOURCE_SNAPSHOT_DIR"
  fi

  if find "$SOURCE_SNAPSHOT_DIR" \
      \( -type d -name .git -o -type f -name .git \) \
      -print -quit | grep -q .; then
    echo "ERROR: Git metadata found in source snapshot: $SOURCE_SNAPSHOT_DIR" >&2
    exit 1
  fi

  PARAM_PATH="$SOURCE_SNAPSHOT_DIR"
}

create_source_snapshot


require_nonempty() {
  local file="$1"

  [[ -e "$file" ]] || {
    echo "ERROR: Missing required file: $file" >&2
    exit 1
  }

  [[ -s "$file" ]] || {
    echo "ERROR: Required file is empty: $file" >&2
    exit 1
  }
}

write_usage_summary() {
  local name="$1"
  local log="$2"
  local model="$3"
  local summary="$LOG_DIR/$name.usage.txt"

  {
    echo "name=$name"
    echo "model=$model"
    echo "log=$log"
    echo "session_id=$(jq -r '.session_id // "unknown"' "$log" 2>/dev/null)"
    echo "duration_ms=$(jq -r '.duration_ms // "unknown"' "$log" 2>/dev/null)"
    echo "total_cost_usd=$(jq -r '.total_cost_usd // "unknown"' "$log" 2>/dev/null)"
    echo "subtype=$(jq -r '.subtype // "unknown"' "$log" 2>/dev/null)"
  } > "$summary"
}

claude_run() {
  local model="$1"
  local prompt="$2"

  (
    cd "$PARAM_PATH"

    claude -p "$prompt" \
        --plugin-dir "$PLUGIN_DIR" \
        --model "$model" \
        --permission-mode bypassPermissions \
        --add-dir "$PARAM_PATH" \
        --add-dir "$PLUGIN_DIR" \
        --add-dir "$REPORT_DIR" \
        --allowedTools "$ALLOWED_TOOLS" \
        --output-format "$OUT"
  )
}

run_findings_task() {
  local log="$LOG_DIR/findings-opus.log"

  if [[ -s "$RED" && -s "$LINT" && -s "$BLUE" ]]; then
    echo "Using existing source reports:"
    echo "- $RED"
    echo "- $LINT"
    echo "- $BLUE"
    return 0
  fi

  for output in "$RED" "$LINT" "$BLUE"; do
    if [[ -e "$output" && ! -s "$output" ]]; then
      echo "ERROR: Existing report is empty: $output" >&2
      return 1
    fi
  done

  mkdir -p "$REPORT_DIR" "$LOG_DIR"

  echo "Generating source reports with $FINDINGS_MODEL:"
  echo "- red-team:  $RED"
  echo "- lint-task: $LINT"
  echo "- blue-team: $BLUE"
  echo "Claude log: $log"

  if claude_run "$FINDINGS_MODEL" "
PARAM_PATH=$PARAM_PATH
PLUGIN_DIR=$PLUGIN_DIR
REPORT_DIR=$REPORT_DIR

Run one sequential findings task using Opus.

You must generate these three source reports in this exact order:

1. Red-team report
   - Load and apply the skill /sast-plugin:red-team.
   - Review PARAM_PATH using the red-team skill method.
   - Write the complete standard report to: $RED
   - Use the Write tool to create that file.
   - Preserve source finding identifiers.
   - Include file:line references where available.
   - Do not invent findings.
   - If the report cannot be generated, stop and document the blocker instead of writing a misleading report.

2. Lint-task report
   - Load and apply the skill /sast-plugin:lint-task.
   - Review PARAM_PATH using the lint-task skill method.
   - Write the complete standard report to: $LINT
   - Use the Write tool to create that file.
   - Preserve source finding identifiers.
   - Include file:line references where available.
   - Do not invent findings.
   - If the report cannot be generated, stop and document the blocker instead of writing a misleading report.

3. Blue-team report
   - Load and apply the skill /sast-plugin:blue-team.
   - Review PARAM_PATH using the blue-team skill method.
   - Focus on defensive recommendations, compensating controls, detection, and operational handoff.
   - Write the complete standard report to: $BLUE
   - Use the Write tool to create that file.
   - Preserve source finding identifiers.
   - Include file:line references where available.
   - Do not invent findings.
   - If the report cannot be generated, stop and document the blocker instead of writing a misleading report.

Execution requirements:
- Complete red-team first, then lint-task, then blue-team.
- Do not start the next skill until the previous report has been written.
- Do not consolidate findings in this task.
- Do not write the final consolidated review in this task.
- Do not invent findings.
- If any source report cannot be generated, stop and document the blocker.

$readonly_rules
" > "$log" 2>&1; then
    echo "[findings-opus] Claude exited 0" >> "$log"
    write_usage_summary "findings-opus" "$log" "$FINDINGS_MODEL"
  else
    rc="$?"
    echo "[findings-opus] Claude exited non-zero: $rc" >> "$log"
    echo "ERROR: findings task failed. Check log: $log" >&2
    return "$rc"
  fi

  require_nonempty "$RED"
  require_nonempty "$LINT"
  require_nonempty "$BLUE"
}

run_consolidation() {
  local log="$LOG_DIR/sec-manager-haiku.log"

  echo "Generating consolidated review with $CONSOLIDATION_MODEL: $FINAL"
  echo "Claude log: $log"

  if claude_run "$CONSOLIDATION_MODEL" "
PARAM_PATH=$PARAM_PATH
PLUGIN_DIR=$PLUGIN_DIR
REPORT_DIR=$REPORT_DIR

Load and apply the skill /sast-plugin:sec-manager as the source of truth for process and output format.

Read these source reports end-to-end:
- $RED
- $LINT
- $BLUE

Apply the sec-manager methodology exactly:
- correspondence mapping
- exploit-chain synthesis
- compensating control analysis
- contradiction resolution
- joint severity calibration
- shared root-cause clustering
- operational-defence handoff aggregation

Output contract:
- Use the exact deliverable skeleton defined in /sast-plugin:sec-manager.
- Preserve source finding identifiers such as R*, L*, and B*.
- Include file:line references from source reports.
- Do not invent findings.
- Include a substantive Operational Defence Handoff section.
- If any source report is missing or empty, stop and report which file failed.
- Write the final consolidated review to: $FINAL
- Use the Write tool to create that file.

$readonly_rules
" > "$log" 2>&1; then
    echo "[sec-manager-haiku] Claude exited 0" >> "$log"
    write_usage_summary "sec-manager-haiku" "$log" "$CONSOLIDATION_MODEL"
  else
    rc="$?"
    echo "[sec-manager-haiku] Claude exited non-zero: $rc" >> "$log"
    echo "ERROR: sec-manager failed. Check log: $log" >&2
    return "$rc"
  fi

  require_nonempty "$FINAL"
}

echo "To watch progress run:
watch -n 2 '
date
echo
echo \"Claude processes:\"
ps -eo pid,ppid,stat,etime,%cpu,%mem,cmd | grep \"[c]laude\"
echo
echo \"Scan script:\"
ps -eo pid,ppid,stat,etime,%cpu,%mem,cmd | grep \"[r]un_sec_manager_scan\"
echo
echo \"Reports and logs:\"
ls -lh \"$REPORT_DIR\"/*.md \"$LOG_DIR\"/*.log 2>/dev/null
'"

run_findings_task

require_nonempty "$RED"
require_nonempty "$LINT"
require_nonempty "$BLUE"

run_consolidation

echo "Done."
echo "Red-team report:      $RED"
echo "Lint-task report:     $LINT"
echo "Blue-team report:     $BLUE"
echo "Consolidated review:  $FINAL"
echo "Logs:                 $LOG_DIR"