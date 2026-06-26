<?php
/**
 * SAST Baseline Test File
 *
 * Vulnerable PHP patterns for 50 Moodle Security Advisories (MSA-25-0023 through MSA-26-0011).
 * Each function/class demonstrates the vulnerable pattern a SAST scanner should detect.
 * For baselining SAST agent detection capabilities.
 *
 * WARNING: This file is intentionally vulnerable. Do NOT deploy to production.
 */

// ============================================================================
// MSA-26-0011 (CVE-2026-7278) - CSRF and missing capability check in admin/mnet/peers.php
// ============================================================================

function vuln_msa_26_0011_csrf_missing_capability() {
    global $DB;

    require_login();

    $action = optional_param('action', '', PARAM_ALPHA);
    $id = required_param('id', PARAM_INT);

    // Missing: require_sesskey();
    // Missing: require_capability('moodle/site:config', context_system::instance());

    if ($action === 'delete') {
        $DB->delete_records('mnet_host', ['id' => $id]);
        redirect(new moodle_url('/admin/mnet/peers.php'), 'Host deleted');
    }
}

// ============================================================================
// MSA-26-0010 (CVE-2025-14761) - AWS SDK for PHP upstream security fix
// ============================================================================

// Vulnerable: Outdated third-party library with known vulnerability
// composer.json snippet:
// "require": { "aws/aws-sdk-php": "3.295.0" }
// Fix: Update to patched version via composer update aws/aws-sdk-php

// ============================================================================
// MSA-26-0009 (CVE-2026-7277) - CSRF in reset penalty rules functionality
// ============================================================================

function vuln_msa_26_0009_csrf_penalty_reset() {
    global $DB, $PAGE;

    require_login();

    $cmid = required_param('cmid', PARAM_INT);
    $reset = optional_param('reset', 0, PARAM_INT);

    // Missing: require_sesskey();
    if ($reset) {
        $DB->delete_records('quiz_penalty_rules', ['quizid' => $cmid]);
        redirect($PAGE->url, get_string('penaltiesreset', 'mod_quiz'));
    }
}

// ============================================================================
// MSA-26-0008 (CVE-2026-24765) - PHPUnit upstream PPE/security risk
// ============================================================================

// Vulnerable: PHPUnit accessible in production or outdated version with eval risks
// composer.json:
// "require-dev": { "phpunit/phpunit": "^9.5.0" }
// Risk: PHPUnit < 10.5.38 / < 11.5.3 has code execution via test doubles
// Also: vendor/bin/phpunit accessible on web if vendor not protected

// ============================================================================
// MSA-26-0007 (CVE-2026-7276) - Messaging DoS with deleted users
// ============================================================================

function vuln_msa_26_0007_messaging_dos_deleted_users() {
    global $DB, $USER;

    require_login();

    $userid = required_param('userid', PARAM_INT);
    $message = required_param('message', PARAM_TEXT);

    // Missing: Check if target user is deleted/suspended
    // Missing: Rate limiting
    $userto = $DB->get_record('user', ['id' => $userid]);
    // No check: if ($userto->deleted) { throw new moodle_exception('userdeleted'); }

    \core\message\manager::send_message($USER, $userto, $message);
}

// ============================================================================
// MSA-26-0006 (CVE-2026-7275) - RCE risk via Google Drive repository plugin
// ============================================================================

class vuln_repository_googledocs extends repository {
    public function get_file($reference, $filename = '') {
        $url = $this->get_download_url($reference);
        $path = $this->prepare_file($filename);
        // Vulnerable: No validation of file content/type from external source
        // Could allow .php or other executable files to be stored in dataroot
        $content = download_file_content($url);
        file_put_contents($path, $content);
        // Missing: File type validation, content scanning
        return ['path' => $path];
    }
}

// ============================================================================
// MSA-26-0005 (CVE-2026-7274) - SQL injection in external database auth plugin
// ============================================================================

class vuln_auth_plugin_db extends auth_plugin_base {
    public function user_login($username, $password) {
        $extdb = $this->db_init();
        $table = $this->config->table;
        $fielduser = $this->config->fielduser;
        $fieldpass = $this->config->fieldpass;

        // VULNERABLE: User-controlled field names concatenated into SQL
        $sql = "SELECT * FROM $table WHERE $fielduser = '$username' AND $fieldpass = '$password'";
        $rs = $extdb->Execute($sql);
        return ($rs && $rs->RecordCount() > 0);
    }
}

// ============================================================================
// MSA-26-0004 (CVE-2024-51736) - Symfony Process upstream command-injection on Windows
// ============================================================================

function vuln_msa_26_0004_symfony_process_injection() {
    // On Windows, cmd.exe shell expansion allows injection
    $filename = $_GET['file']; // e.g., "test&calc.exe"
    $process = new \Symfony\Component\Process\Process(['cat', $filename]);
    $process->run();
    // Fix: Update symfony/process to >= 5.4.46 / 6.4.14 / 7.1.7
}

// ============================================================================
// MSA-26-0003 (CVE-2026-26047) - DoS risk in TeX formula editor
// ============================================================================

function vuln_msa_26_0003_tex_dos() {
    global $CFG;

    // No length limit on input
    // No timeout on processing
    // No complexity limit
    $texexp = required_param('tex', PARAM_RAW); // Arbitrary length TeX input

    // Catastrophic backtracking or infinite loop possible
    $cmd = "$CFG->pathtomimetex --png $texexp";
    exec($cmd, $output, $retval);
    // Missing: Input length validation, execution timeout, resource limits
}

// ============================================================================
// MSA-26-0002 (CVE-2026-26046) - RCE risk in TeX filter admin setting
// ============================================================================

function vuln_msa_26_0002_tex_rce_admin_setting() {
    global $CFG;

    // Admin setting allows arbitrary command path without validation
    // Later used directly in exec():
    $tex = required_param('tex', PARAM_RAW);
    $cmd = $CFG->filter_tex_pathtomimetex . " -e '$tex'";
    exec($cmd); // Admin-controlled path = RCE if admin account compromised
}

// ============================================================================
// MSA-26-0001 (CVE-2026-26045) - RCE risk via file restore
// Also covers: MSA-25-0051 (CVE-2025-67847) - same pattern
// ============================================================================

class vuln_restore_controller {
    public function extract_file($filerecord, $content) {
        global $CFG;

        $filepath = $filerecord->filepath . $filerecord->filename;
        // VULNERABLE: No path traversal check, no filetype restriction
        // Attacker crafts backup with ../../ paths or .php files
        $fullpath = $CFG->dataroot . '/filedir/' . $filepath;
        file_put_contents($fullpath, $content);
        // Missing: Path canonicalization, extension whitelist, directory traversal check
    }
}

// ============================================================================
// MSA-25-0061 (CVE-2025-67857) - User IDs exposed in URLs with anonymous submissions
// ============================================================================

function vuln_msa_25_0061_userid_in_anonymous_url($submission) {
    // Even when blind marking is enabled, the URL contains real userid
    return new moodle_url('/mod/assign/view.php', [
        'action' => 'grading',
        'userid' => $submission->userid, // Exposes identity in anonymous mode
    ]);
    // Fix: Use anonymous ID mapping when blind marking enabled
}

// ============================================================================
// MSA-25-0060 (CVE-2025-67856) - Badges with role criterion awarded incorrectly
// ============================================================================

class vuln_award_criteria_role extends award_criteria {
    public function review($userid) {
        $roles = get_user_roles(context_system::instance(), $userid);
        // BUG: Only checks system context, not course context
        // User with role in ANY context triggers award
        foreach ($this->params as $param) {
            if (isset($roles[$param['role']])) {
                return true; // Incorrectly awards badge
            }
        }
        return false;
    }
}

// ============================================================================
// MSA-25-0059 (CVE-2025-67855) - Reflected XSS in policy tool
// Same pattern as MSA-25-0025 (CVE-2025-3643) below
// ============================================================================

// ============================================================================
// MSA-25-0058 (CVE-2025-67854) - Forum ratings accessible without permission
// ============================================================================

function vuln_msa_25_0058_forum_ratings_no_capability($postid) {
    global $DB;

    // Missing: capability check for mod/forum:viewrating
    $ratings = $DB->get_records('rating', ['itemid' => $postid, 'component' => 'mod_forum']);
    return $ratings; // Returns ratings to users without permission
    // Fix: require_capability('mod/forum:viewrating', $context);
}

// ============================================================================
// MSA-25-0057 (CVE-2025-67853) - Password brute-force risk in confirmation email web service
// Same pattern as MSA-25-0048 (CVE-2025-62399) below
// ============================================================================

// ============================================================================
// MSA-25-0056 (CVE-2025-67852) - Open redirect in OAuth login
// ============================================================================

function vuln_msa_25_0056_open_redirect() {
    global $CFG;

    $wantsurl = required_param('wantsurl', PARAM_URL);

    // After successful OAuth authentication...
    $code = required_param('code', PARAM_RAW);
    $user = authenticate_via_oauth($code);
    complete_user_login($user);

    // VULNERABLE: No validation that redirect is to same site
    redirect($wantsurl);
    // Fix: if (strpos($wantsurl, $CFG->wwwroot) !== 0) { $wantsurl = $CFG->wwwroot; }
}

// ============================================================================
// MSA-25-0055 (CVE-2025-67851) - Formula injection in CSV/Excel exports
// ============================================================================

function vuln_msa_25_0055_csv_formula_injection($grades) {
    $fp = fopen('php://output', 'w');
    header('Content-Type: text/csv');

    foreach ($grades as $grade) {
        // VULNERABLE: Cell content starting with =, +, -, @ triggers formula execution
        fputcsv($fp, [
            $grade->username,
            $grade->feedback, // Could contain "=CMD('calc')" or "+cmd|'/C calc'!A0"
            $grade->grade,
        ]);
        // Fix: Prepend tab/apostrophe to cells starting with formula chars
    }
}

// ============================================================================
// MSA-25-0054 (CVE-2025-67850) - XSS in formula editor
// ============================================================================

function vuln_msa_25_0054_formula_xss($tex) {
    // User-supplied TeX rendered into HTML without sanitisation
    $output = '<span class="filter_mathjaxloader_equation">';
    $output .= $tex; // VULNERABLE: Raw user input in HTML context
    $output .= '</span>';
    return $output;
    // Fix: Use s() or htmlspecialchars() on $tex before embedding in HTML
}

// ============================================================================
// MSA-25-0053 (CVE-2025-67849) - XSS via AI prompt injection
// ============================================================================

function vuln_msa_25_0053_ai_xss($prompt, $response) {
    // AI response may contain HTML/JS injected via prompt manipulation
    $output = '<div class="ai-response">';
    $output .= format_text($response, FORMAT_HTML); // Trusts AI output as safe HTML
    $output .= '</div>';
    return $output;
    // Fix: Use FORMAT_PLAIN or aggressive sanitisation on AI responses
}

// ============================================================================
// MSA-25-0052 (CVE-2025-67848) - Suspended users authenticate via LTI Provider
// ============================================================================

class vuln_enrol_lti_tool_provider {
    public function authenticate($params) {
        global $DB;

        $user = $DB->get_record('user', ['email' => $params['lis_person_contact_email_primary']]);
        if ($user) {
            // Missing: Check if user is suspended
            // if ($user->suspended) { throw new moodle_exception('suspended'); }
            complete_user_login($user);
            return true;
        }
        return false;
    }
}

// ============================================================================
// MSA-25-0050 (CVE-2025-62401) - Timed assignment timer bypass
// ============================================================================

class vuln_mod_assign_submission {
    public function save_submission($data) {
        global $USER;

        $instance = $this->get_instance();
        $timestart = $this->get_user_timestart($USER->id);

        // VULNERABLE: Only checks if current time > due date
        // Does not enforce timelimit from when user started
        if ($instance->duedate && time() > $instance->duedate) {
            return false;
        }
        // Missing: if (time() - $timestart > $instance->timelimit) { return false; }

        $this->process_save($data);
        return true;
    }
}

// ============================================================================
// MSA-25-0049 (CVE-2025-62400) - Hidden group names visible via calendar events
// ============================================================================

function vuln_msa_25_0049_hidden_groups_calendar($userid) {
    global $DB;

    $events = $DB->get_records_sql("
        SELECT e.*, g.name as groupname
        FROM {event} e
        JOIN {groups} g ON g.id = e.groupid
        WHERE e.userid = ? OR e.groupid IN (
            SELECT groupid FROM {groups_members} WHERE userid = ?
        )", [$userid, $userid]);
    // VULNERABLE: No check for groups_get_activity_group / visible groups mode
    // Hidden group names leak through calendar event titles
    return $events;
}

// ============================================================================
// MSA-25-0048 (CVE-2025-62399) - Password brute-force risk when mobile/web services enabled
// Also covers: MSA-25-0057 (CVE-2025-67853) - same pattern
// ============================================================================

function vuln_msa_25_0048_brute_force_no_ratelimit($username, $password, $service) {
    // No failed attempt counting
    // No lockout mechanism
    // No CAPTCHA after N failures
    $user = authenticate_user_login($username, $password);
    if ($user) {
        $token = external_generate_token_for_current_user($service);
        return ['token' => $token];
    }
    // Only returns generic error - but no rate limiting allows brute force
    throw new moodle_exception('invalidlogin');
}

// ============================================================================
// MSA-25-0047 (CVE-2025-62398) - MFA bypass after valid username/password
// ============================================================================

function vuln_msa_25_0047_mfa_bypass($username, $password) {
    $user = authenticate_user_login($username, $password);
    if ($user) {
        complete_user_login($user); // Sets session as authenticated
        // MFA check happens AFTER session is already valid
        if (tool_mfa_is_required($user)) {
            redirect('/admin/tool/mfa/auth.php');
            // But session cookie already issued - MFA page can be skipped
        }
    }
}

// ============================================================================
// MSA-25-0046 (CVE-2025-62397) - Course ID enumeration via router response
// ============================================================================

function vuln_msa_25_0046_course_id_enumeration($courseid) {
    global $DB;

    $course = $DB->get_record('course', ['id' => $courseid]);
    if (!$course) {
        throw new moodle_exception('coursenotfound'); // 404-like response
    }
    if (!is_enrolled(context_course::instance($courseid))) {
        throw new moodle_exception('nopermission'); // 403-like response
    }
    // VULNERABLE: Attacker can distinguish "exists but no access" from "doesn't exist"
    // Fix: Return same error for both cases
    return $course;
}

// ============================================================================
// MSA-25-0045 (CVE-2025-62396) - Application directory listing via router error handling
// ============================================================================

function vuln_msa_25_0045_path_disclosure() {
    set_exception_handler(function($e) {
        // In debug mode or via specific error conditions
        echo '<pre>';
        echo 'Error: ' . $e->getMessage() . "\n";
        echo 'File: ' . $e->getFile() . "\n"; // Reveals full server path
        echo 'Trace: ' . $e->getTraceAsString(); // Reveals directory structure
        echo '</pre>';
        // Fix: Never expose file paths in production; use $CFG->debugdisplay
    });
}

// ============================================================================
// MSA-25-0044 (CVE-2025-62395) - External cohort search leaks system cohort data
// ============================================================================

function vuln_msa_25_0044_cohort_search_leak($query) {
    global $DB;

    // VULNERABLE: Searches all cohorts regardless of context permissions
    $cohorts = $DB->get_records_select('cohort',
        "name LIKE ? OR idnumber LIKE ?",
        ["%$query%", "%$query%"]
    );
    // Missing: Filter by context and check cohort:view capability per cohort
    // System cohorts with sensitive names (e.g., "VIP Customers") exposed
    return $cohorts;
}

// ============================================================================
// MSA-25-0043 (CVE-2025-62394) - Quiz notifications sent to suspended participants
// ============================================================================

function vuln_msa_25_0043_notify_suspended($quiz, $attempt) {
    $recipients = get_enrolled_users(context_module::instance($quiz->cmid));
    foreach ($recipients as $user) {
        // Missing: if ($user->suspended) { continue; }
        // Missing: Check enrolment status is active
        $message = new \core\message\message();
        $message->userto = $user;
        message_send($message);
    }
}

// ============================================================================
// MSA-25-0042 (CVE-2025-54869) - FPDI upstream security fix
// ============================================================================

// Vulnerable: Outdated FPDI library (PDF parsing) with known vulnerability
// composer.json: "setasign/fpdi": "2.3.6"
// FPDI parses PDF cross-reference tables; malformed PDF can trigger
// buffer overflow or object injection during parsing
// Fix: Update to setasign/fpdi >= 2.6.2

// ============================================================================
// MSA-25-0041 (CVE-2025-62393) - Course overview fragment leaks inaccessible course info
// ============================================================================

function vuln_msa_25_0041_course_fragment_leak($args) {
    global $PAGE;

    $courseid = $args['courseid'];
    $course = get_course($courseid);
    // VULNERABLE: No access check before returning course data
    // Missing: require_login($course) or can_access_course($course)
    $output = $PAGE->get_renderer('core_course');
    return $output->course_overview($course); // Leaks title, summary, teachers
}

// ============================================================================
// MSA-25-0040 (CVE-2025-62438) - Profile access callback/capability checks fail in web services
// ============================================================================

function vuln_msa_25_0040_profile_field_leak($field, $values) {
    global $DB;

    $users = $DB->get_records_list('user', $field, $values);
    $result = [];
    foreach ($users as $user) {
        // VULNERABLE: Returns all profile fields without checking
        // user_can_view_profile() or custom field visibility settings
        $result[] = (array)$user;
        // Fix: Apply user_get_user_details() which respects visibility
    }
    return $result;
}

// ============================================================================
// MSA-25-0039 (CVE-2025-62437) - Feedback results ignore Separate Groups mode
// Also covers: MSA-25-0038 (CVE-2025-62436) - Course logs ignore Separate Groups mode
// ============================================================================

function vuln_msa_25_0039_feedback_ignores_groups($feedback, $cm) {
    global $DB;

    $responses = $DB->get_records('feedback_completed', ['feedback' => $feedback->id]);
    // VULNERABLE: No group filtering applied
    // Missing check:
    // $groupmode = groups_get_activity_groupmode($cm);
    // if ($groupmode == SEPARATEGROUPS && !has_capability('moodle/site:accessallgroups', $context)) {
    //     $allowedgroups = groups_get_activity_allowed_groups($cm);
    //     // Filter responses by group membership
    // }
    return $responses;
}

// ============================================================================
// MSA-25-0037 (CVE-2025-62435) - BBB playback leaks sesskey to external BBB service
// ============================================================================

function vuln_msa_25_0037_sesskey_leak_to_external($recording) {
    global $CFG;

    // VULNERABLE: sesskey (CSRF token) appended to external redirect URL
    $url = $recording->playback_url;
    $url .= '?redirect=' . urlencode($CFG->wwwroot . '/mod/bigbluebuttonbn/view.php?sesskey=' . sesskey());
    // sesskey leaked to external BBB server via Referer header or URL parameter
    return $url;
    // Fix: Don't include sesskey in URLs that go to external services
}

// ============================================================================
// MSA-25-0036 (CVE-2025-49518) - IDOR fetching recently accessed courses for other users
// ============================================================================

function vuln_msa_25_0036_idor_recent_courses() {
    global $DB, $USER;

    // VULNERABLE: Accepts arbitrary userid without ownership check
    $userid = required_param('userid', PARAM_INT);
    // Missing: if ($userid != $USER->id) { require_capability(...); }
    $courses = $DB->get_records('user_lastaccess', ['userid' => $userid], 'timeaccess DESC');
    return $courses; // Returns another user's course access history
}

// ============================================================================
// MSA-25-0035 (CVE-2025-49517) - Missing authorisation checks in BigBlueButton view page
// ============================================================================

function vuln_msa_25_0035_bbb_no_access_check() {
    global $DB, $OUTPUT;

    $id = required_param('id', PARAM_INT);
    $cm = get_coursemodule_from_id('bigbluebuttonbn', $id);
    // Missing: require_login($course, true, $cm);
    // Missing: require_capability('mod/bigbluebuttonbn:view', context_module::instance($cm->id));

    $instance = $DB->get_record('bigbluebuttonbn', ['id' => $cm->instance]);
    // Directly renders BBB meeting info without access control
    echo $OUTPUT->render_meeting($instance);
}

// ============================================================================
// MSA-25-0034 (CVE-2025-49516) - CSRF in badges backpack management
// Same pattern as MSA-26-0011 - missing sesskey check on state-changing action
// ============================================================================

function vuln_msa_25_0034_csrf_badges_backpack() {
    global $DB;

    require_login();
    $action = required_param('action', PARAM_ALPHA);
    $badgeid = required_param('badgeid', PARAM_INT);

    // Missing: require_sesskey();
    if ($action === 'disconnect') {
        $DB->delete_records('badge_backpack', ['badgeid' => $badgeid]);
    }
}

// ============================================================================
// MSA-25-0033 (CVE-2025-49515) - Hidden course details exposed due to inconsistent visibility checks
// ============================================================================

function vuln_msa_25_0033_hidden_course_visibility($field, $value) {
    global $DB;

    $courses = $DB->get_records('course', [$field => $value]);
    $result = [];
    foreach ($courses as $course) {
        // VULNERABLE: Returns course even if visibility = 0
        // and user lacks moodle/course:viewhiddencourses
        if (!$course->visible) {
            // Missing: Check capability before including
            // $ctx = context_course::instance($course->id);
            // if (!has_capability('moodle/course:viewhiddencourses', $ctx)) continue;
        }
        $result[] = $course;
    }
    return $result;
}

// ============================================================================
// MSA-25-0032 (CVE-2025-49514) - SSRF risk via DNS rebinding / cURL handling
// ============================================================================

function vuln_msa_25_0032_ssrf_dns_rebinding($url) {
    $ch = curl_init($url);
    // VULNERABLE: DNS lookup happens at connect time
    // Attacker's DNS returns public IP for first lookup (passes allowlist)
    // Then returns 127.0.0.1 for second lookup (actual connection)
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    // Missing: CURLOPT_RESOLVE to pin IP, or re-check IP after connection
    // Missing: Block private/internal IP ranges after DNS resolution
    $result = curl_exec($ch);
    curl_close($ch);
    return $result;
}

// ============================================================================
// MSA-25-0031 (CVE-2025-46337) - ADOdb upstream SQL injection risk
// ============================================================================

// Vulnerable: Outdated ADOdb library with SQL injection in specific drivers
// lib/adodb/ contains ADOdb < 5.22.9
// Certain database drivers improperly escape parameters
function vuln_msa_25_0031_adodb_sqli($userInput) {
    $db = ADONewConnection('mysql');
    $db->Execute("SELECT * FROM users WHERE name = ?", [$userInput]);
    // Even parameterised queries vulnerable in affected ADOdb versions
    // Fix: Update lib/adodb to >= 5.22.9
}

// ============================================================================
// MSA-25-0030 (CVE-2025-49513) - Password cached/revealed on login page after logout
// ============================================================================

function vuln_msa_25_0030_password_cache() {
    global $CFG;

    echo '<form method="post" action="' . $CFG->wwwroot . '/login/index.php">';
    echo '<input type="text" name="username" id="username">';
    // VULNERABLE: Missing autocomplete="off" or autocomplete="new-password"
    echo '<input type="password" name="password" id="password">';
    // After logout, browser autofills the password field
    // Fix: Add autocomplete="off" and implement proper cache-control headers
    echo '</form>';
}

// ============================================================================
// MSA-25-0029 (CVE-2025-49512) - MathJax XSS risk because safe extension not loaded
// ============================================================================

function vuln_msa_25_0029_mathjax_no_safe_extension() {
    $config = [
        'tex2jax' => ['inlineMath' => [['\\(', '\\)']]],
        // VULNERABLE: Safe extension not loaded
        // MathJax can execute arbitrary JS via \href{javascript:...}{text}
        // or \unicode commands
    ];
    // Fix: Add 'Safe' to extensions list:
    // 'extensions' => ['Safe.js'],
    // 'Safe' => ['allow' => ['URLs' => 'none', 'classes' => 'none', 'cssIDs' => 'none']]
    return json_encode($config);
}

// ============================================================================
// MSA-25-0028 (CVE-2025-3647) - IDOR in cohorts report
// ============================================================================

function vuln_msa_25_0028_idor_cohort_report($cohortid) {
    global $DB;

    $cohort = $DB->get_record('cohort', ['id' => $cohortid], '*', MUST_EXIST);
    // VULNERABLE: No capability check in the cohort's context
    // Missing: $context = context::instance_by_id($cohort->contextid);
    // Missing: require_capability('moodle/cohort:view', $context);
    $members = $DB->get_records('cohort_members', ['cohortid' => $cohortid]);
    return $members; // Any authenticated user can enumerate cohort membership
}

// ============================================================================
// MSA-25-0027 (CVE-2025-3645) - IDOR in messaging web service exposes user details
// ============================================================================

function vuln_msa_25_0027_idor_messaging_user_details($userid) {
    global $DB;

    $user = $DB->get_record('user', ['id' => $userid]);
    // VULNERABLE: Returns full user details to any authenticated caller
    // Missing: Check if requesting user can view target user's profile
    return [
        'id' => $user->id,
        'fullname' => fullname($user),
        'email' => $user->email, // Sensitive - should check profile visibility
        'city' => $user->city,
        'country' => $user->country,
    ];
}

// ============================================================================
// MSA-25-0026 (CVE-2025-3644) - AJAX section delete permission check failure
// ============================================================================

function vuln_msa_25_0026_ajax_section_delete($sectionid) {
    global $DB;

    $section = $DB->get_record('course_sections', ['id' => $sectionid], '*', MUST_EXIST);
    $context = context_course::instance($section->course);
    // VULNERABLE: Missing or insufficient capability check
    // Only checks course:update but should also check course:delete and
    // verify section-specific permissions
    // Missing: require_capability('moodle/course:update', $context);
    course_delete_section($section->course, $section);
}

// ============================================================================
// MSA-25-0025 (CVE-2025-3643) - Reflected XSS in policy tool
// Also covers: MSA-25-0059 (CVE-2025-67855) - same pattern
// ============================================================================

function vuln_msa_25_0025_reflected_xss_policy() {
    $returnurl = optional_param('returnurl', '', PARAM_URL);

    // Later in the page output:
    echo '<a href="' . $returnurl . '">Return</a>';
    // VULNERABLE: PARAM_URL allows javascript: URIs or malformed URLs
    // with event handlers like: " onmouseover="alert(1)
    // Fix: Use s() for HTML attribute context: echo '<a href="' . s($returnurl) . '">';
}

// ============================================================================
// MSA-25-0024 (CVE-2025-3642) - Authenticated RCE in EQUELLA repository
// ============================================================================

class vuln_repository_equella extends repository {
    public function get_file($url, $filename = '') {
        $endpoint = $this->get_option('equella_url');
        // VULNERABLE: URL from user/external source used without sanitisation
        // Could be manipulated to execute commands if passed to system functions
        $cmd = "curl -o '$filename' '$endpoint/$url'";
        exec($cmd); // Command injection via $url or $filename
        // Fix: Use PHP curl functions instead of exec, validate/escape all inputs
    }
}

// ============================================================================
// MSA-25-0023 (CVE-2025-3641) - Authenticated RCE in Dropbox repository
// ============================================================================

class vuln_repository_dropbox extends repository {
    public function get_file($reference, $filename = '') {
        $source = json_decode($reference);
        $path = $source->path;
        // VULNERABLE: Unsanitised path in shell command
        $tempfile = make_temp_directory('repo_dropbox') . '/' . $filename;
        // If filename contains shell metacharacters: "; rm -rf / #"
        $cmd = "mv '/tmp/download' '$tempfile'";
        exec($cmd); // Shell injection via $filename
        // Fix: Use PHP rename()/copy() instead of exec, escapeshellarg()
    }
}
