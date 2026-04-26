import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from models import (
    ChatRequest, ChatResponse,
    PlanTestsRequest, PlanTestsResponse,
    GenerateTestsRequest, GenerateTestsResponse,
    RunTestsRequest, RunTestsResponse,
    ValidateEnvironmentRequest, ValidateEnvironmentResponse,
)
from ai import chat_with_qa, plan_tests, generate_test_cases
from runner import run_all_tests, validate_environment, build_analytics
from hybrid_runner import run_all_tests_hybrid

app = FastAPI(title="TestSense API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://localhost:5173", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(body: ChatRequest):
    message = body.message.strip()

    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # ── /create command → generate test cases ─────────────────
    if message.lower() == "/create":
        if not body.requirements.strip():
            raise HTTPException(
                status_code=400,
                detail="No requirements gathered yet. Describe what you want to test first."
            )
        try:
            test_cases = generate_test_cases(body.requirements)
            return ChatResponse(type="test_cases", test_cases=test_cases)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Test generation failed: {str(e)}")

    # ── normal chat message → conversational response ──────────
    try:
        result = chat_with_qa(
            message,
            [m.model_dump() for m in body.history],
            body.requirements,
        )
        return ChatResponse(
            type="message",
            reply=result.get("reply", ""),
            scenarios=result.get("scenarios", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.get("/")
def root():
    ui = Path(__file__).parent / "frontend" / "index.html"
    if ui.exists():
        return FileResponse(ui)
    return {"status": "TestSense API is running", "version": "1.0.0"}


@app.post("/api/plan-tests", response_model=PlanTestsResponse)
def plan_tests_endpoint(body: PlanTestsRequest):
    if not body.requirements.strip():
        raise HTTPException(status_code=400, detail="Requirements cannot be empty.")
    try:
        plan = plan_tests(body.requirements)
        return PlanTestsResponse(
            summary=plan.get("summary", ""),
            scenarios=plan.get("scenarios", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Planning failed: {str(e)}")


@app.post("/api/generate-tests", response_model=GenerateTestsResponse)
def generate_tests(body: GenerateTestsRequest):
    if not body.requirements.strip():
        raise HTTPException(status_code=400, detail="Requirements cannot be empty.")
    try:
        test_cases = generate_test_cases(body.requirements)
        return GenerateTestsResponse(test_cases=test_cases)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")


@app.post("/api/setup-environment", response_model=ValidateEnvironmentResponse)
def setup_environment(body: ValidateEnvironmentRequest):
    """Validate and set up the test environment (URL + credentials)."""
    env = body.environment
    
    # Validate URL format
    if not env.url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty.")
    if not env.url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid URL — must start with http:// or https://")
    
    # Validate credentials
    if not env.validEmail.strip():
        raise HTTPException(status_code=400, detail="Valid email/username cannot be empty.")
    if not env.validPassword.strip():
        raise HTTPException(status_code=400, detail="Valid password cannot be empty.")
    if not env.invalidEmail.strip():
        raise HTTPException(status_code=400, detail="Invalid email/username cannot be empty.")
    if not env.invalidPassword.strip():
        raise HTTPException(status_code=400, detail="Invalid password cannot be empty.")
    
    try:
        # Validate that the URL is reachable and has login form
        result = validate_environment(env)
        
        if not result["reachable"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        return ValidateEnvironmentResponse(
            reachable=result["reachable"],
            status_code=result["status_code"],
            page_title=result["page_title"],
            has_login_form=result["has_login_form"],
            message=result["message"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Environment setup failed: {str(e)}")


@app.post("/api/run-tests", response_model=RunTestsResponse)
async def run_tests(body: RunTestsRequest):
    if not body.environment.url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid URL — must start with http:// or https://")
    if not body.test_cases:
        raise HTTPException(status_code=400, detail="No test cases provided.")

    # Pre-check: verify environment is reachable before spending time on tests
    env_check = await asyncio.to_thread(validate_environment, body.environment)
    if not env_check["reachable"]:
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "ENV_UNREACHABLE",
                "message": "Your set environment is not reachable. Please reset the environment.",
                "reason": env_check["message"],
                "redirect_to": "/setup-environment",
            },
        )

    try:
        if body.use_webrover:
            results = await run_all_tests_hybrid(body.test_cases, body.environment)
        else:
            results = await asyncio.to_thread(run_all_tests, body.test_cases, body.environment)

        passed   = sum(1 for r in results if r.status == "PASSED")
        failed   = sum(1 for r in results if r.status == "FAILED")
        warnings = sum(1 for r in results if r.status == "WARNING")
        total    = len(results)
        pass_rate = round((passed / total) * 100) if total else 0

        severity_breakdown = build_analytics(results)
        duration_ms = sum((r.duration_ms or 0) for r in results)

        return RunTestsResponse(
            results=results,
            total=total,
            passed=passed,
            failed=failed,
            warnings=warnings,
            pass_rate=pass_rate,
            severity_breakdown=severity_breakdown,
            duration_ms=duration_ms,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test execution failed: {str(e)}")
