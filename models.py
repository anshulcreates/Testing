from pydantic import BaseModel
from typing import Optional, List


# ── Chat ─────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str       # "user" | "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    requirements: str = ""  # accumulated requirements text built up by the frontend

class ChatResponse(BaseModel):
    type: str                           # "message" | "test_cases"
    reply: Optional[str] = None
    scenarios: Optional[List[str]] = None
    test_cases: Optional[List["TestCase"]] = None


# ── Plan Tests ───────────────────────────────────────────────────────────────

class PlanTestsRequest(BaseModel):
    requirements: str

class PlanTestsResponse(BaseModel):
    summary: str
    scenarios: List[str]


# ── Generate Tests ──────────────────────────────────────────────────────────

class GenerateTestsRequest(BaseModel):
    requirements: str


class TestCase(BaseModel):
    id: str
    name: str
    persona: str
    description: str
    severity: str          # CRITICAL | WARNING | MINOR
    steps: List[str] = []


class GenerateTestsResponse(BaseModel):
    test_cases: List[TestCase]


# ── Environment ─────────────────────────────────────────────────────────────

class Environment(BaseModel):
    url: str
    validEmail: str
    validPassword: str
    invalidEmail: Optional[str] = ""
    invalidPassword: Optional[str] = ""


class ValidateEnvironmentRequest(BaseModel):
    environment: Environment


class ValidateEnvironmentResponse(BaseModel):
    reachable: bool
    status_code: Optional[int] = None
    page_title: Optional[str] = None
    has_login_form: bool = False
    message: str


# ── Run Tests ───────────────────────────────────────────────────────────────

class StepLog(BaseModel):
    step_number: int
    step: str
    success: bool
    log: str


class TestResult(BaseModel):
    id: str
    name: str
    persona: str
    severity: str
    status: str                        # PASSED | FAILED | WARNING
    story: str
    impact: Optional[str] = None
    technical: Optional[str] = None
    step_logs: List[StepLog] = []
    duration_ms: Optional[int] = None


class AnalyticsSeverity(BaseModel):
    critical_passed: int
    critical_failed: int
    warning_passed: int
    warning_failed: int
    minor_passed: int
    minor_failed: int


class RunTestsRequest(BaseModel):
    test_cases: List[TestCase]
    environment: Environment
    use_webrover: bool = False


class RunTestsResponse(BaseModel):
    results: List[TestResult]
    total: int
    passed: int
    failed: int
    warnings: int
    pass_rate: int
    severity_breakdown: AnalyticsSeverity
    duration_ms: int
