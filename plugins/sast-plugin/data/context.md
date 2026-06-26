# SAST Agent — Totara Context & Key Signals

This file is loaded by the SAST Agent alongside `rules.md`. It describes how Totara's security model works in practice — the patterns to enforce, the flows to track, and the heuristics to apply when scanning Totara PHP code.

---

## Core Heuristics (Encode These First)

| Heuristic | Rule |
|-----------|------|
| No input without PARAM_* | Every value from `$_GET`/`$_POST`/`$_REQUEST` must pass through `required_param()` or `optional_param()` |
| No state change without sesskey | Any POST handler that mutates data must call `require_sesskey()` |
| No sensitive action without capability | DB writes, file access, and sensitive reads must be gated by `require_capability()` |
| No output without escaping | User-derived data must be escaped at the point of output |
| No SQL without placeholders | String concatenation into SQL is always a finding |

## False Positive Guidance

- `eval()` inside `// @codingStandards ignore` with documented justification — downgrade to INFO
- `shell_exec()` in CLI-only scripts (check for `CLI_SCRIPT` constant) — downgrade to LOW
- `$DB->get_records_sql()` using only `PARAM_INT`-validated variables — not an injection finding
- `unserialize()` on data that was previously `serialize()`d in the same request with no user influence — downgrade to LOW
- Output wrapped in `s()`, `format_string()`, or `format_text()` — not an XSS finding

---

## 1. Input Validation

### The Rule
Never read from superglobals directly. All input must pass through Totara's param validation API.

### Banned Patterns (flag these)
```php
$_GET['id']
$_POST['data']
$_REQUEST['filter']
```

### Required Patterns
```php
required_param($name, PARAM_*)
optional_param($name, $default, PARAM_*)
required_param_array($name, PARAM_*)
optional_param_array($name, [], PARAM_*)
```

### PARAM_* Type Strictness
| Value type | Required type |
|------------|---------------|
| IDs, numeric | `PARAM_INT` |
| Short tokens, slugs | `PARAM_ALPHANUM` / `PARAM_ALPHANUMEXT` |
| Free-form text | `PARAM_TEXT` |
| URLs | `PARAM_URL` |
| Raw HTML (last resort) | `PARAM_RAW` — flag if used where not justified |

### Additional Flags
- `PARAM_RAW` used where a stricter type would suffice → flag as **medium**
- `clean_param()` called on a value already returned by `required_param()` / `optional_param()` → flag as double-cleaning (low, logic error)
- Array inputs not using `*_param_array()` variant → flag as **high**

---

## 2. Access Control

### Baseline Requirements
Almost all web-accessible endpoints must have, in order:
```php
require_login();                              // authentication
require_capability('component:action', $context); // authorisation
require_sesskey();                            // CSRF (state-changing only)
```

### Flag These
| Condition | Severity |
|-----------|----------|
| Web-accessible PHP file with no `require_login()` | **critical** |
| DB write, file access, or sensitive read without `require_capability()` | **high** |
| State-changing POST handler without `require_sesskey()` | **high** |
| Capability checked against wrong context level (e.g. system when course expected) | **high** |
| Record fetched by user-supplied ID with no ownership/relationship validation (IDOR) | **high** |

### Context Levels (validate correctness)
- `context_system::instance()` — site-wide admin actions only
- `context_course::instance($courseid)` — course-level actions
- `context_module::instance($cmid)` — activity-level actions
- `context_user::instance($userid)` — user profile actions

Using a broader context (e.g. system) for an action that should be scoped to a course is a privilege escalation risk.

### IDOR Heuristic
Any `$DB->get_record()` or equivalent using a user-supplied ID must have one of:
- A capability check that implicitly restricts to context
- An explicit ownership check (e.g. `$record->userid === $USER->id`)
- A relationship validation (e.g. user enrolled in course)

If none of these follow the fetch, flag as **high** IDOR.

### State-Change Heuristic
If code matches all of:
- Receives POST data
- Writes to the database, modifies files, or sends emails

Then it **must** have `require_login()` + `require_capability()` + `require_sesskey()`. Any missing item is a finding.

---

## 3. SQL Safety (DML API)

### Safe Patterns
```php
// High-level (preferred)
$DB->get_record('table', ['id' => $id]);
$DB->get_records('table', ['userid' => $userid]);

// Parameterised raw SQL
$DB->get_records_sql(
    "SELECT * FROM {tablename} WHERE id = :id",
    ['id' => $id]
);

// IN clause — mandatory pattern
[$insql, $params] = $DB->get_in_or_equal($ids, SQL_PARAMS_NAMED, 'id');
$sql = "SELECT id FROM {tablename} WHERE id $insql";
$records = $DB->get_records_sql($sql, $params);
```

### Flag These
| Pattern | Severity |
|---------|----------|
| String concatenation into any `$DB->*_sql()` call | **critical** |
| Variable interpolated directly into SQL string | **critical** |
| `IN (...)` clause built by hand without `get_in_or_equal()` | **high** |
| Table name hardcoded as `mdl_tablename` or `ttr_tablename` instead of `{tablename}` | **low** |
| Raw SQL where `$DB->get_record()` / `$DB->get_records()` would suffice | **low** (code quality + risk) |

### Second-Order SQL Injection
Track values that originate from DB reads and are later interpolated into new SQL queries without re-validation. Flag as **medium**.

---

## 4. Output Escaping (XSS)

### Escape at the Sink

| Output context | Required function |
|----------------|-------------------|
| Plain text in HTML | `s($str)` |
| Names / titles | `format_string($name, true, ['context' => $context])` |
| Rich text / user content | `format_text($content, $format, $options)` |
| URLs in `href`, `action` | Build with `new moodle_url(...)` |
| Mustache templates | `{{var}}` (auto-escaped) — never `{{{var}}}` with tainted data |

### Flag These
| Pattern | Severity |
|---------|----------|
| `echo $variable` where variable derives from user input or DB | **high** |
| `echo $record->content` where column stores arbitrary text | **high** |
| `PARAM_RAW` value output without `format_text()` | **high** |
| `{{{var}}}` in Mustache template where var is user-derived | **high** |
| `format_text()` called but `$format` is hardcoded to `FORMAT_HTML` for user content | **medium** |

### Taint Tracking Flow
```
$_GET/$_POST → required_param()/optional_param() → business logic → OUTPUT
                                                                    ↑
                              must pass through s() / format_string() / format_text()
```
If the chain from input to output does not pass through an escaping function, flag as XSS.

---

## 5. Parameter → Sink Flow Tracking

Track these flows end-to-end:

| Source | Sink | Risk | Must Pass Through |
|--------|------|------|-------------------|
| User input | SQL query | SQL injection | `PARAM_INT` / named placeholders |
| User input | HTML output | XSS | `s()` / `format_string()` / `format_text()` |
| User input | File path | Path traversal | `realpath()` + directory check, or File API |
| User input | `exec()`/`eval()` | RCE | Should never reach this sink |
| User input | `header()` redirect | Open redirect | `moodle_url` validation or allowlist |
| DB value | SQL query | 2nd-order SQLi | Re-parameterise — never concatenate |
| DB value | HTML output | Stored XSS | Same escaping rules as direct input |

---

## 6. File Access (File API Only)

### Valid Pattern
```php
$fs = get_file_storage();
// Serve via pluginfile.php with component callback in lib.php
```

### Required Validations in `pluginfile.php` Callbacks
```php
function mycomponent_pluginfile($course, $cm, $context, $filearea, $args, $forcedownload) {
    require_login($course, false, $cm);
    require_capability('mod/mycomponent:view', $context); // must be present
    // validate $filearea, $itemid from $args
}
```

### Flag These
| Pattern | Severity |
|---------|----------|
| `file_get_contents($CFG->dataroot . '/' . $path)` | **high** |
| `fopen($CFG->dataroot . '/' . $userInput, 'r')` | **critical** |
| `pluginfile.php` callback with no capability check | **high** |
| Missing `$forcedownload` for user-uploaded files | **medium** |
| File served without validating `$filearea` or `$itemid` | **high** |

---

## 7. External Web Service APIs

### Required Structure
```php
public static function myfunction($param) {
    $params = self::validate_parameters(self::myfunction_parameters(), ['param' => $param]);
    $context = context_system::instance();
    self::validate_context($context);
    require_capability('component:action', $context);
    // ... business logic
}
```

### Flag These
| Condition | Severity |
|-----------|----------|
| Missing `self::validate_parameters()` | **high** |
| Missing `self::validate_context()` | **high** |
| Missing `require_capability()` | **high** |
| Capability checked after business logic executed | **high** |

---

## 8. Page / Endpoint Structure

### Expected Execution Order
```php
require_once('../../config.php');

// 1. Parameter validation
$id = required_param('id', PARAM_INT);

// 2. Authentication
require_login();

// 3. Context resolution
$context = context_course::instance($courseid);

// 4. Capability check
require_capability('mod/example:view', $context);

// 5. CSRF (if POST)
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    require_sesskey();
}

// 6. Business logic / DB access
```

### Flag These
| Pattern | Severity |
|---------|----------|
| Business logic or DB access before `require_login()` | **high** |
| Capability check after DB write | **high** |
| `require_sesskey()` called after state has already been mutated | **high** |
| Auth checks inside conditional branches (can be bypassed) | **medium** |

---

## 9. CSRF Protection

### Rule
Any endpoint or action that:
- Accepts POST data AND
- Mutates state (DB write, file operation, email, external call)

Must call `require_sesskey()` before the mutation.

### Flag These
| Pattern | Severity |
|---------|----------|
| POST handler with DB write and no `require_sesskey()` | **high** |
| Form `action` URL that writes without `sesskey` hidden field | **high** |
| Mutable operation triggered via GET request | **high** |

---

## 10. Dangerous Functions

### Always Flag
| Function | Risk | Severity |
|----------|------|----------|
| `eval()` | Code injection | **critical** |
| `exec()`, `system()`, `shell_exec()`, `passthru()`, `popen()` | Command injection | **critical** if user-tainted, **high** otherwise |
| `unserialize()` on non-static data | Object injection / RCE | **critical** |
| `preg_replace('/pattern/e', ...)` | Code injection via regex | **critical** |
| `assert($stringVar)` | Code injection | **high** |
| `mb_ereg_replace(..., 'e')` | Code injection | **high** |
| `extract($_GET)` / `extract($_POST)` | Variable overwrite | **high** |

### Preferred Alternatives
| Avoid | Use instead |
|-------|-------------|
| `serialize()` / `unserialize()` | `json_encode()` / `json_decode()` |
| `exec()` for system info | Native PHP functions |
| `eval()` | Refactor — there is no safe use of eval |

---

## 11. Capability + Context Mapping

### Track
- The capability string: `mod/component:action` or `totara/component:action`
- The context level it is checked against

### Flag These
| Pattern | Severity |
|---------|----------|
| `context_system` used for per-course or per-module action | **high** (over-scoped, privilege risk) |
| Capability string used but not defined in `db/access.php` | **medium** |
| `has_capability()` used without acting on the result | **medium** |
| Admin-only capability checked but context is not system | **medium** |

---

## 12. Plugin Awareness

### Plugin Types to Scan
- `server/mod/*` — activity modules (high impact)
- `server/totara/*` — Totara-specific (business logic, often privileged)
- `server/local/*` — third-party extensions (least scrutinised)
- `server/blocks/*` — blocks (often render user-facing content)
- `server/auth/*` — authentication (critical)
- `server/admin/tool/*` — admin tools (high privilege)

### Flag These
| Pattern | Severity |
|---------|----------|
| Sensitive action in a plugin with no capability check | **high** |
| Plugin defines no capabilities in `db/access.php` but performs privileged operations | **high** |
| Plugin uses `context_system` for actions that should be course-scoped | **high** |

---

## 13. CLI Scripts and Scheduled Tasks

### Context
CLI scripts (`define('CLI_SCRIPT', true)`) and scheduled tasks have no authenticated user session. Assumptions about `$USER` being valid are dangerous.

### Flag These
| Pattern | Severity |
|---------|----------|
| CLI script reading from `$argv` without validation | **high** |
| Scheduled task accepting external input without sanitisation | **high** |
| CLI script assuming `$USER->id` is set and non-zero | **medium** |
| Shell commands in scheduled tasks with interpolated config values | **medium** |

---

## 14. High-Signal Detection Priorities

Scan for these first — they are the highest-impact findings in Totara:

| Priority | Pattern | Impact |
|----------|---------|--------|
| 1 | Missing `require_capability()` before DB write or file access | AuthZ bypass |
| 2 | Missing `require_sesskey()` on POST handler | CSRF |
| 3 | Unescaped `echo` of user-derived or DB data | XSS |
| 4 | String concatenation into SQL | SQL injection |
| 5 | Incorrect context level (system vs course vs module) | Privilege escalation |
| 6 | Direct `$_GET`/`$_POST` usage | Input validation bypass |
| 7 | `unserialize()` on non-static input | RCE |
| 8 | `eval()` anywhere | RCE |
| 9 | IDOR — record fetched by ID without ownership check | Data exposure |
| 10 | Missing `require_login()` on web-accessible endpoint | Unauthenticated access |

---

## 15. Totara-Specific Safe Patterns Reference

When suggesting fixes, always use these canonical Totara patterns:

```php
// Input validation
$id     = required_param('id', PARAM_INT);
$filter = optional_param('filter', '', PARAM_ALPHANUMEXT);
$ids    = optional_param_array('ids', [], PARAM_INT);

// Authentication + authorisation
require_login($course, false, $cm);
require_capability('mod/example:view', $context);

// CSRF
require_sesskey();

// SQL — parameterised
$record = $DB->get_record('table', ['id' => $id], '*', MUST_EXIST);
[$insql, $params] = $DB->get_in_or_equal($ids, SQL_PARAMS_NAMED, 'id');
$rows = $DB->get_records_sql("SELECT * FROM {table} WHERE id $insql", $params);

// Output escaping
echo s($usertext);                                           // plain text
echo format_string($title, true, ['context' => $context]);  // names/titles
echo format_text($content, $format, ['context' => $context]); // rich text
$url = new moodle_url('/path/to/page.php', ['id' => $id]);  // URLs

// File API
$fs = get_file_storage();
$file = $fs->get_file($contextid, $component, $filearea, $itemid, $filepath, $filename);
```
