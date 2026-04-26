import asyncio
import time
from ai import generate_story_report
from models import TestCase, Environment, TestResult, StepLog
from adapters.webrover_adapter import WebRoverAdapter
from runner import build_analytics


async def _run_single_test(tc: TestCase, env: Environment, adapter: WebRoverAdapter) -> TestResult:
    step_logs: list[StepLog] = []
    start_ms = int(time.time() * 1000)

    setup_ok = await adapter.setup(env.url)
    if not setup_ok:
        return TestResult(
            id=tc.id, name=tc.name, persona=tc.persona,
            severity=tc.severity, status="FAILED",
            story="WebRover could not initialize the browser for this test.",
            impact="Browser setup failed — check that WebRover is running and Chrome is accessible.",
            technical="WEBROVER SETUP FAILED",
            step_logs=[], duration_ms=0,
        )

    try:
        for i, step in enumerate(tc.steps, 1):
            log = await adapter.execute_step(step, env, i)
            step_logs.append(log)
    except Exception as e:
        step_logs.append(StepLog(
            step_number=len(step_logs) + 1,
            step="Unexpected error",
            success=False,
            log=str(e)[:200]
        ))
    finally:
        await adapter.cleanup()

    duration_ms = int(time.time() * 1000) - start_ms

    verify_logs  = [l for l in step_logs if l.step.lower().startswith(("verify", "confirm", "check"))]
    action_logs  = [l for l in step_logs if not l.step.lower().startswith(("verify", "confirm", "check"))]
    verify_failures  = [l for l in verify_logs  if not l.success]
    critical_actions = [l for l in action_logs  if not l.success and not l.step.lower().startswith("leave")]

    if verify_failures:
        success = False
    elif len(critical_actions) >= 1:
        success = False
    else:
        success = True

    status = "PASSED" if success else ("WARNING" if tc.severity == "WARNING" else "FAILED")

    technical = "\n".join(
        f"{'✓' if l.success else '✗'} [{l.step_number}] {l.log}"
        for l in step_logs
    )

    try:
        narrative = generate_story_report(
            tc, success,
            [{"step": l.step, "success": l.success, "log": l.log} for l in step_logs],
            env.url
        )
        story  = narrative.get("story",  "Test completed.")
        impact = narrative.get("impact")
    except Exception:
        story  = "Test completed successfully." if success else "The test encountered issues."
        impact = None if success else "Review this test case manually."

    return TestResult(
        id=tc.id, name=tc.name, persona=tc.persona,
        severity=tc.severity, status=status,
        story=story, impact=impact, technical=technical,
        step_logs=step_logs, duration_ms=duration_ms,
    )


async def run_all_tests_hybrid(test_cases: list[TestCase], env: Environment) -> list[TestResult]:
    """
    Run tests using WebRover if available, otherwise fall back to Playwright.
    """
    adapter = WebRoverAdapter()

    if not await adapter.is_available():
        # WebRover server not running — fall back to existing Playwright runner
        from runner import run_all_tests
        return await asyncio.to_thread(run_all_tests, test_cases, env)

    results = []
    for tc in test_cases:
        try:
            result = await _run_single_test(tc, env, adapter)
        except Exception as e:
            result = TestResult(
                id=tc.id, name=tc.name, persona=tc.persona,
                severity=tc.severity, status="FAILED",
                story="This test could not be executed due to an unexpected error.",
                impact="Review this test case manually.",
                technical=f"EXCEPTION: {str(e)[:300]}",
                step_logs=[], duration_ms=0,
            )
        results.append(result)

    return results
