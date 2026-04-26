import re
import time
from playwright.sync_api import sync_playwright, Page, BrowserContext, TimeoutError as PWTimeout
from models import TestCase, Environment, TestResult, StepLog, AnalyticsSeverity


# ──────────────────────────────────────────────────────────────
#  ENVIRONMENT VALIDATOR
# ──────────────────────────────────────────────────────────────

def validate_environment(env):
    """Check if the URL is reachable and has a login form."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            response = page.goto(env.url, timeout=30000, wait_until="domcontentloaded")
            status   = response.status if response else 0
            title    = page.title()

            # detect login form
            has_login = (
                page.locator('input[type="password"]').count() > 0 or
                page.locator('input[name*="email" i], input[name*="user" i]').count() > 0 or
                page.locator('button:has-text("Login"), button:has-text("Sign in"), button:has-text("Log in")').count() > 0
            )

            browser.close()
            return {
                "reachable": True,
                "status_code": status,
                "page_title": title,
                "has_login_form": has_login,
                "message": f"URL reachable — '{title}' (HTTP {status})"
            }
        except Exception as e:
            browser.close()
            return {
                "reachable": False,
                "status_code": None,
                "page_title": None,
                "has_login_form": False,
                "message": f"Cannot reach URL: {str(e)[:120]}"
            }


# ──────────────────────────────────────────────────────────────
#  ELEMENT FINDERS
# ──────────────────────────────────────────────────────────────

def _find_input(page: Page, field_name: str):
    """Find an input by label, placeholder, name, id, or aria-label."""
    fn_lower = field_name.lower()

    # common semantic keywords → input types
    if any(k in fn_lower for k in ["password"]):
        el = page.locator('input[type="password"]').first
        if el.count() > 0:
            return el

    if any(k in fn_lower for k in ["email", "user", "username", "user id"]):
        for sel in [
            'input[type="email"]',
            'input[name*="email" i]',
            'input[name*="user" i]',
            'input[placeholder*="email" i]',
            'input[placeholder*="user" i]',
        ]:
            el = page.locator(sel).first
            if el.count() > 0:
                return el

    # generic: try by label text
    for label in page.locator("label").all():
        try:
            label_text = (label.inner_text() or "").lower()
            if fn_lower in label_text or any(word in label_text for word in fn_lower.split()):
                for_attr = label.get_attribute("for")
                if for_attr:
                    el = page.locator(f"#{for_attr}").first
                    if el.count() > 0:
                        return el
        except Exception:
            pass

    # generic: try by placeholder / name / id / aria-label
    for attr in ["placeholder", "name", "id", "aria-label"]:
        for word in fn_lower.split():
            if len(word) < 3:
                continue
            el = page.locator(f'input[{attr}*="{word}" i]').first
            if el.count() > 0:
                return el
        el = page.locator(f'input[{attr}*="{fn_lower}" i]').first
        if el.count() > 0:
            return el

    # last resort: nth input
    inputs = page.locator("input:not([type='hidden']):not([type='submit']):not([type='checkbox'])")
    if "password" in fn_lower and inputs.count() >= 2:
        return inputs.nth(1)
    if inputs.count() >= 1:
        return inputs.first
    return None


def _find_button(page: Page, label: str):
    """Find a button by visible text, value, or role."""
    label_lower = label.lower()

    strategies = [
        f'button:has-text("{label}")',
        f'[role="button"]:has-text("{label}")',
        f'input[type="submit"][value*="{label}" i]',
        f'a:has-text("{label}")',
    ]
    for sel in strategies:
        try:
            el = page.locator(sel).first
            if el.count() > 0:
                return el
        except Exception:
            pass

    # partial match on all buttons
    for btn in page.locator("button").all():
        try:
            if label_lower in (btn.inner_text() or "").lower():
                return btn
        except Exception:
            pass

    # fallback: any submit button
    submit = page.locator('button[type="submit"], input[type="submit"]').first
    if submit.count() > 0:
        return submit

    return None


# ──────────────────────────────────────────────────────────────
#  CREDENTIAL RESOLVER
# ──────────────────────────────────────────────────────────────

def _resolve_value(step: str, env: Environment) -> tuple:
    """Map a step description to the actual credential/value. Returns (value, error)."""
    s = step.lower()

    # passwords
    if "incorrect password" in s or "wrong password" in s or "invalid password" in s:
        if not env.invalidPassword:
            return None, "invalidPassword not configured in environment"
        return env.invalidPassword, None

    if "less than" in s and "character" in s:
        if not env.validPassword:
            return None, "validPassword not configured in environment"
        return env.validPassword[:2], None  # derive dynamically: too-short slice

    if "exactly 6" in s:
        if not env.validPassword:
            return None, "validPassword not configured in environment"
        return env.validPassword[:6], None

    if "6-8 character" in s or "valid password" in s or "correct password" in s:
        if not env.validPassword:
            return None, "validPassword not configured in environment"
        return env.validPassword, None

    # emails / usernames
    if "already registered" in s or "duplicate email" in s:
        if not env.validEmail:
            return None, "validEmail not configured in environment"
        return env.validEmail, None

    if "invalid email" in s or "invalid format" in s or "invalidemail" in s:
        if env.invalidEmail:
            return env.invalidEmail, None
        if env.validEmail:
            # derive an invalid-format email dynamically from the valid one
            return env.validEmail.replace("@", "").replace(".", ""), None
        return None, "Cannot derive invalid email — neither invalidEmail nor validEmail configured"

    if "invalid user" in s or "wrong user" in s or "incorrect user" in s:
        if not env.invalidEmail:
            return None, "invalidEmail not configured in environment"
        return env.invalidEmail, None

    if "valid email" in s or "correct email" in s or "valid username" in s:
        if not env.validEmail:
            return None, "validEmail not configured in environment"
        return env.validEmail, None

    if any(k in s for k in ["user id", "user name", "username"]):
        if not env.validEmail:
            return None, "validEmail not configured in environment"
        return env.validEmail, None

    if "phone" in s or "otp" in s:
        field = "phone" if "phone" in s else "otp"
        return None, f"'{field}' credential not configured in environment"

    # default: valid email
    if not env.validEmail:
        return None, "validEmail not configured in environment"
    return env.validEmail, None


def _resolve_url(raw: str, base_url: str) -> str:
    """Replace any non-real placeholder domain with the actual app URL."""
    raw = raw.strip().strip("`")
    base = base_url.rstrip("/")

    # detect placeholder: URL has a domain but it doesn't match the real base
    if raw.startswith("http"):
        import urllib.parse
        raw_host = urllib.parse.urlparse(raw).netloc
        real_host = urllib.parse.urlparse(base_url).netloc
        if raw_host and raw_host != real_host:
            # extract path from placeholder URL and rebase onto real host
            path = urllib.parse.urlparse(raw).path
            if path and not path.startswith("/"):
                path = "/" + path
            return base + path

    if not raw.startswith("http"):
        if not raw.startswith("/"):
            raw = "/" + raw
        return base + raw

    return raw


# ──────────────────────────────────────────────────────────────
#  SINGLE STEP EXECUTOR
# ──────────────────────────────────────────────────────────────

def execute_step(page: Page, step: str, env: Environment, step_num: int) -> StepLog:
    s = step.strip()
    sl = s.lower()

    try:
        # ── NAVIGATE ──────────────────────────────────────────
        if sl.startswith("navigate"):
            url_match = re.search(r"`([^`]+)`", s)
            if url_match:
                url = _resolve_url(url_match.group(1), env.url)
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_load_state("domcontentloaded", timeout=15000)
                return StepLog(step_number=step_num, step=s, success=True,
                               log=f"Navigated to {url} | Title: {page.title()}")
            return StepLog(step_number=step_num, step=s, success=False,
                           log="No URL found in Navigate step")

        # ── LEAVE EMPTY ───────────────────────────────────────
        elif sl.startswith("leave"):
            field_match = re.search(r"'([^']+)'", s)
            field = field_match.group(1) if field_match else "field"
            # actively clear the field if it has content
            el = _find_input(page, field)
            if el:
                el.fill("")
            return StepLog(step_number=step_num, step=s, success=True,
                           log=f"Left '{field}' empty")

        # ── ENTER ─────────────────────────────────────────────
        elif sl.startswith("enter"):
            field_match = (
                re.search(r"in the '([^']+)'\s+field", s, re.IGNORECASE) or
                re.search(r"in the '([^']+)'", s, re.IGNORECASE) or
                re.search(r"'([^']+)'\s+field", s, re.IGNORECASE)
            )
            field_name = field_match.group(1) if field_match else None
            value, err = _resolve_value(s, env)

            if err:
                return StepLog(step_number=step_num, step=s, success=False,
                               log=f"Credential error: {err}")

            if field_name:
                el = _find_input(page, field_name)
                if el:
                    el.click()
                    el.fill(value)
                    masked = "••••••" if "password" in field_name.lower() else value
                    return StepLog(step_number=step_num, step=s, success=True,
                                   log=f"Typed '{masked}' into '{field_name}'")
                return StepLog(step_number=step_num, step=s, success=False,
                               log=f"Field '{field_name}' not found on page")
            return StepLog(step_number=step_num, step=s, success=False,
                           log="Could not parse field name from step")

        # ── CLICK ─────────────────────────────────────────────
        elif sl.startswith("click"):
            btn_match = re.search(r"'([^']+)'", s)
            btn_label = btn_match.group(1) if btn_match else None
            if btn_label:
                btn = _find_button(page, btn_label)
                if btn:
                    btn.scroll_into_view_if_needed()
                    btn.click()
                    page.wait_for_timeout(2500)
                    return StepLog(step_number=step_num, step=s, success=True,
                                   log=f"Clicked '{btn_label}' | Now at: {page.url}")
                return StepLog(step_number=step_num, step=s, success=False,
                               log=f"Button '{btn_label}' not found on page")
            return StepLog(step_number=step_num, step=s, success=False,
                           log="No button label found in step")

        # ── VERIFY / CONFIRM / CHECK ───────────────────────────
        elif sl.startswith(("verify", "confirm", "check")):
            return _verify(page, s, step_num)

        # ── WAIT ──────────────────────────────────────────────
        elif sl.startswith("wait"):
            secs = re.search(r"(\d+)\s*second", sl)
            ms = int(secs.group(1)) * 1000 if secs else 2000
            page.wait_for_timeout(ms)
            return StepLog(step_number=step_num, step=s, success=True,
                           log=f"Waited {ms}ms")

        # ── SELECT ────────────────────────────────────────────
        elif sl.startswith("select"):
            opt_match = re.search(r"'([^']+)'", s)
            if opt_match:
                page.locator(f'text="{opt_match.group(1)}"').first.click()
                return StepLog(step_number=step_num, step=s, success=True,
                               log=f"Selected '{opt_match.group(1)}'")
            return StepLog(step_number=step_num, step=s, success=False,
                           log="No option found to select")

        return StepLog(step_number=step_num, step=s, success=True,
                       log="Step acknowledged")

    except PWTimeout:
        return StepLog(step_number=step_num, step=s, success=False,
                       log="Timeout — page too slow or element not found")
    except Exception as e:
        return StepLog(step_number=step_num, step=s, success=False,
                       log=f"Error: {str(e)[:180]}")


# ──────────────────────────────────────────────────────────────
#  VERIFY STEP HANDLER
# ──────────────────────────────────────────────────────────────

def _verify(page: Page, step: str, step_num: int) -> StepLog:
    from ai import ai_verify_step
    sl = step.lower()

    def log(success, msg):
        return StepLog(step_number=step_num, step=step, success=success, log=msg)

    def page_body():
        try:
            return page.inner_text("body")
        except Exception:
            return ""

    # ── exact quoted message — deterministic string match ─────
    msg_match = re.search(r"message '([^']+)'", step, re.IGNORECASE)
    if msg_match:
        expected = msg_match.group(1)
        found = expected.lower() in page_body().lower()
        return log(found, f"Message '{expected}' {'✓ found' if found else '✗ NOT found'} in page")

    # ── no session created — structural cookie/storage check ──
    if "no session" in sl:
        cookies = page.context.cookies()
        has_auth = any(
            any(k in c.get("name", "").lower() for k in ["session", "token", "auth", "jwt", "sid"])
            for c in cookies
        )
        return log(not has_auth, f"Auth cookie present: {has_auth} (expected: none)")

    # ── session / token created — structural cookie/storage check
    if "session" in sl and "created" in sl:
        cookies = page.context.cookies()
        has_auth = any(
            any(k in c.get("name", "").lower() for k in ["session", "token", "auth", "jwt", "sid"])
            for c in cookies
        )
        if not has_auth:
            try:
                token = page.evaluate(
                    "() => localStorage.getItem('token') || localStorage.getItem('authToken') || localStorage.getItem('jwt')"
                )
                has_auth = bool(token)
            except Exception:
                pass
        return log(has_auth, f"Auth cookie/token found: {has_auth}")

    # ── password masked/revealed — structural input type check ─
    if "masked" in sl or "hidden" in sl:
        ok = page.locator('input[type="password"]').count() > 0
        return log(ok, f"Password field is {'masked' if ok else 'NOT masked'}")

    if "revealed" in sl:
        ok = page.locator('input[type="text"]').count() > 0
        return log(ok, f"Password field {'revealed' if ok else 'still masked'}")

    # ── specific redirect URL — deterministic URL match ───────
    if "redirected" in sl:
        url_match = re.search(r"`([^`]+)`", step)
        if url_match:
            expected = url_match.group(1).lower()
            ok = expected in page.url.lower()
            return log(ok, f"Expected URL '{expected}', got '{page.url}'")

    # ── error message present — structural DOM scan ───────────
    if "error" in sl or "error message" in sl:
        error_selectors = [
            '[class*="error"]', '[class*="alert"]', '[role="alert"]',
            '[class*="invalid"]', '[class*="danger"]', '[class*="warning"]',
            'p[style*="red"]', 'span[style*="red"]',
        ]
        for sel in error_selectors:
            if page.locator(sel).count() > 0:
                txt = page.locator(sel).first.inner_text()
                return log(True, f"Error element found: '{txt[:80]}'")

    # ── AI-powered verification for all remaining cases ───────
    result = ai_verify_step(step, page.url, page_body())
    return log(result.get("success", False), result.get("reason", "AI verification completed"))


# ──────────────────────────────────────────────────────────────
#  SINGLE TEST CASE RUNNER
# ──────────────────────────────────────────────────────────────

def run_single_test(tc: TestCase, env: Environment, context: BrowserContext) -> TestResult:
    from ai import generate_story_report

    page = context.new_page()
    step_logs = []
    start_ms = int(time.time() * 1000)

    try:
        for i, step in enumerate(tc.steps, 1):
            log = execute_step(page, step, env, i)
            step_logs.append(log)
    except Exception as e:
        step_logs.append(StepLog(
            step_number=len(step_logs) + 1,
            step="Unexpected error",
            success=False,
            log=str(e)[:200]
        ))
    finally:
        try:
            page.close()
        except Exception:
            pass

    duration_ms = int(time.time() * 1000) - start_ms

    # ── determine pass / fail ─────────────────────────────────
    verify_logs = [l for l in step_logs if l.step.lower().startswith(("verify", "confirm", "check"))]
    action_logs = [l for l in step_logs if not l.step.lower().startswith(("verify", "confirm", "check"))]

    verify_failures  = [l for l in verify_logs  if not l.success]
    critical_actions = [l for l in action_logs  if not l.success and not l.step.lower().startswith("leave")]

    if verify_failures:
        success = False
    elif len(critical_actions) > len(action_logs) // 2:
        success = False
    else:
        success = True

    if success:
        status = "PASSED"
    elif tc.severity == "WARNING":
        status = "WARNING"
    else:
        status = "FAILED"

    # ── technical log ─────────────────────────────────────────
    technical = "\n".join(
        f"{'✓' if l.success else '✗'} [{l.step_number}] {l.log}"
        for l in step_logs
    )

    # ── AI story ──────────────────────────────────────────────
    try:
        narrative = generate_story_report(
            tc, success,
            [{"step": l.step, "success": l.success, "log": l.log} for l in step_logs],
            env.url
        )
        story  = narrative.get("story",  f"{tc.name} — {status}")
        impact = narrative.get("impact")
    except Exception:
        first_name = tc.persona.split()[0]
        failed_steps = [l for l in step_logs if not l.success]
        if success:
            story = f"{first_name} completed '{tc.name}' — all {len(step_logs)} steps passed."
        else:
            fail_detail = f" Failed at: {failed_steps[0].log}" if failed_steps else ""
            story = f"{first_name} could not complete '{tc.name}'.{fail_detail}"
        impact = None if success else f"'{tc.name}' needs manual review before release."

    return TestResult(
        id=tc.id,
        name=tc.name,
        persona=tc.persona,
        severity=tc.severity,
        status=status,
        story=story,
        impact=impact,
        technical=technical,
        step_logs=step_logs,
        duration_ms=duration_ms,
    )


# ──────────────────────────────────────────────────────────────
#  RUN ALL TESTS
# ──────────────────────────────────────────────────────────────

def run_all_tests(test_cases: list[TestCase], env: Environment) -> list[TestResult]:
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for tc in test_cases:
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                ignore_https_errors=True,
            )
            try:
                result = run_single_test(tc, env, context)
            except Exception as e:
                result = TestResult(
                    id=tc.id, name=tc.name, persona=tc.persona,
                    severity=tc.severity, status="FAILED",
                    story="This test could not be executed due to an unexpected error.",
                    impact="Review this test case manually.",
                    technical=f"EXCEPTION: {str(e)[:300]}",
                    step_logs=[], duration_ms=0,
                )
            finally:
                context.close()
            results.append(result)

        browser.close()
    return results


# ──────────────────────────────────────────────────────────────
#  ANALYTICS BUILDER
# ──────────────────────────────────────────────────────────────

def build_analytics(results: list[TestResult]) -> AnalyticsSeverity:
    def count(sev, status):
        return sum(1 for r in results if r.severity == sev and r.status == status)

    return AnalyticsSeverity(
        critical_passed=count("CRITICAL", "PASSED"),
        critical_failed=count("CRITICAL", "FAILED"),
        warning_passed=count("WARNING",  "PASSED"),
        warning_failed=count("WARNING",  "WARNING"),
        minor_passed=count("MINOR",    "PASSED"),
        minor_failed=count("MINOR",    "FAILED"),
    )
