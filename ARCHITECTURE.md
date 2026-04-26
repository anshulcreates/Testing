# TestSense Architecture - Environment Setup Phase

## System Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                         TESTSENSE CHATBOT                          │
│                  (Frontend/Chat Interface)                         │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                    HTTP/JSON API
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────────┐  ┌──────────────┐
│ Generate     │  │ Setup            │  │ Run Tests    │
│ Test Cases   │  │ Environment      │  │              │
│              │  │ (NEW)            │  │              │
└──────────────┘  └──────────────────┘  └──────────────┘
```

## Setup Environment Phase Detail

```
┌─────────────────────────────────────────────────────────────┐
│              CHATBOT / FRONTEND                             │
│                                                             │
│  "What's the URL and login credentials?"                  │
└────────────────────┬────────────────────────────────────┘
                     │
              POST /api/setup-environment
                     │
                     ▼
    ┌────────────────────────────────────┐
    │    FASTAPI ENDPOINT                │
    │  (main.py lines 37-75)             │
    │                                    │
    │  1. Validate URL Format            │
    │  2. Validate Credentials           │
    │  3. Call validate_environment()    │
    │  4. Return Status & Metadata       │
    └────────────────────┬───────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │    validate_environment()      │
        │    (runner.py)                 │
        │                                │
        │  Uses: Playwright              │
        │  - Launch headless browser     │
        │  - Navigate to URL             │
        │  - Check HTTP status           │
        │  - Extract page title          │
        │  - Detect login form           │
        │  - Handle timeouts             │
        └────────────────┬───────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │    REAL WEBSITE/URL            │
        │                                │
        │  https://example.com/login     │
        └────────────────────────────────┘
                         │
              ◄──────────┘
              │
              └─── HTTP 200
                  Page Title: "Login"
                  Has Login Form: true
                  
              ┌─ HTTP 404
              │  Page not found
              │
              └─ Connection Error
                 Cannot reach URL
                 
                     │
                     ▼
        ┌────────────────────────────────┐
        │    Response Object             │
        │                                │
        │  {                             │
        │    "reachable": true/false,    │
        │    "status_code": 200,         │
        │    "page_title": "...",        │
        │    "has_login_form": true,     │
        │    "message": "..."            │
        │  }                             │
        └────────────────────┬───────────┘
                             │
              ┌──────────────┘
              │
              ▼
    ┌────────────────────────────────────┐
    │    FASTAPI - Return Response       │
    │    HTTP 200 / 400 / 500            │
    └────────────────────┬───────────────┘
                         │
                   JSON Response
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              CHATBOT / FRONTEND                             │
│                                                             │
│  "✓ Environment ready! URL is accessible."                │
│   "Generating test cases..."                              │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow - Complete Testing Cycle

```
User Input
    │
    ├─ Software Requirements
    │  └─► Generate Test Cases
    │      └─► Receive 6 Test Cases
    │
    ├─ Environment Details
    │  ├─ Website URL
    │  ├─ Valid Credentials (email/password)
    │  └─ Invalid Credentials (email/password)
    │
    └─► Setup Environment (NEW)
        ├─ Validate URL Format
        ├─ Validate All Credentials Present
        ├─ Check URL Reachability
        ├─ Detect Login Form
        └─► Return Environment Status
            
                    │
                    ▼ (If Valid)
                    
         Run Tests Against Environment
         ├─ Navigate to URLs in test steps
         ├─ Fill forms with credentials
         ├─ Click buttons
         ├─ Verify expected outcomes
         └─► Collect Test Results
             
                    │
                    ▼
                    
         Generate Analytics Report
         ├─ Total tests: 6
         ├─ Passed: 5 ✓
         ├─ Failed: 1 ✗
         ├─ Pass rate: 83%
         └─► Display to User
```

## Component Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                        TESTSENSE BACKEND                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  main.py (FastAPI Application)                                 │
│  ├─ GET /                   → Health check                     │
│  ├─ POST /api/generate-tests    → AI-powered test generation   │
│  ├─ POST /api/setup-environment → ✨ NEW - Environment setup   │
│  └─ POST /api/run-tests        → Execute tests                 │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  models.py (Data Models)                                       │
│  ├─ TestCase                → Test case definition            │
│  ├─ Environment            → Environment configuration        │
│  ├─ ValidateEnvironmentRequest    → ✨ NEW input model        │
│  ├─ ValidateEnvironmentResponse   → ✨ NEW output model       │
│  └─ TestResult            → Test execution result             │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ai.py (AI/LLM Integration)                                    │
│  ├─ generate_test_cases()  → Uses Groq LLM                    │
│  └─ generate_story_report() → Creates human-readable reports  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  runner.py (Test Execution Engine)                            │
│  ├─ validate_environment()  → ✨ Called by new endpoint       │
│  ├─ run_all_tests()        → Browser automation              │
│  ├─ _find_input()          → Dynamic element detection       │
│  └─ execute_step()         → Single test step execution      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  External Dependencies                                         │
│  ├─ FastAPI      → Web framework                             │
│  ├─ Playwright   → Browser automation (Chromium)             │
│  ├─ Groq         → LLM API for test generation               │
│  ├─ Pydantic     → Data validation                           │
│  └─ Uvicorn      → ASGI server                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Request/Response Cycle

### Request Path
```
Chatbot Frontend
    │
    ├─ Collect URL
    ├─ Collect Valid Credentials
    ├─ Collect Invalid Credentials
    │
    └─► POST /api/setup-environment
        │
        └─► FastAPI Endpoint (main.py)
            │
            ├─ Validate URL format
            ├─ Validate all 4 credential fields
            │
            └─► Call validate_environment(env)
                │
                └─► runner.py
                    │
                    ├─ Launch Playwright browser (headless)
                    │
                    ├─ Navigate to URL
                    │
                    ├─ Wait for page load (timeout: 12s)
                    │
                    ├─ Extract:
                    │  ├─ HTTP status code
                    │  ├─ Page title
                    │  └─ Login form presence
                    │
                    └─► Close browser
```

### Response Path
```
Result Object (dict)
    │
    ├─ reachable: bool
    ├─ status_code: int
    ├─ page_title: str
    ├─ has_login_form: bool
    └─ message: str
        │
        └─► FastAPI Endpoint
            │
            ├─ Create ValidateEnvironmentResponse
            │
            └─► Return with HTTP 200
                │
                └─► Chatbot Frontend
                    │
                    └─► Display Status
```

## Error Handling Flow

```
Input Validation (Fast Path - No Browser)
    │
    ├─ URL empty?
    │  └─► 400: "URL cannot be empty."
    │
    ├─ URL format invalid?
    │  └─► 400: "Invalid URL — must start with http:// or https://"
    │
    ├─ Valid email empty?
    │  └─► 400: "Valid email/username cannot be empty."
    │
    ├─ Valid password empty?
    │  └─► 400: "Valid password cannot be empty."
    │
    ├─ Invalid email empty?
    │  └─► 400: "Invalid email/username cannot be empty."
    │
    ├─ Invalid password empty?
    │  └─► 400: "Invalid password cannot be empty."
    │
    └─► All valid → Browser check (Slow Path)
        │
        ├─ Connection timeout?
        │  └─► 400: "Cannot reach URL: timeout"
        │
        ├─ DNS failure?
        │  └─► 400: "Cannot reach URL: DNS failed"
        │
        ├─ Other network error?
        │  └─► 400: "Cannot reach URL: [error details]"
        │
        ├─ Unexpected exception?
        │  └─► 500: "Environment setup failed: [error details]"
        │
        └─► Success
            └─► 200: ValidateEnvironmentResponse
```

## State Transitions

```
┌─────────────────┐
│   User Input    │
│   (Start)       │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  Collecting Environment     │
│  Details                    │
│  - URL                      │
│  - Valid Creds              │
│  - Invalid Creds            │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Environment Setup Phase    │ ◄── NEW
│  (This Implementation)      │
│                             │
│  ├─ Validate inputs         │
│  ├─ Check URL reachable     │
│  ├─ Detect login form       │
│  └─ Return status           │
└────────┬────────────────────┘
         │
    ┌────┴────┐
    │          │
    ▼ (OK)     ▼ (Error)
┌────────┐  ┌──────────┐
│Generate│  │Ask User  │
│ Tests  │  │to Fix    │
└────┬───┘  └──────────┘
     │
     ▼
┌──────────────┐
│  Run Tests   │
│ (Using Env)  │
└────┬─────────┘
     │
     ▼
┌──────────────┐
│ Collect      │
│ Results      │
└────┬─────────┘
     │
     ▼
┌──────────────┐
│ Generate     │
│ Analytics    │
└────┬─────────┘
     │
     ▼
┌──────────────┐
│ Report to    │
│ User (End)   │
└──────────────┘
```

## Performance Characteristics

```
Input Validation:  ~1-5 ms   (fast, in-process)
│
Browser Launch:    ~2-3 sec  (Playwright startup)
│
URL Navigation:    ~1-4 sec  (depends on server)
│
Form Detection:    ~100 ms   (CSS selector matching)
│
Browser Close:     ~500 ms   (cleanup)
│
├─ TOTAL:          ~4-10 sec per validation
│
└─ Network latency is the dominant factor
   (Not a bottleneck for typical usage)
```

## Security Model

```
INPUT LAYER:
    ├─ URL validation
    ├─ Format checking
    └─ Empty field validation

EXECUTION LAYER:
    ├─ Headless browser (no UI exposure)
    ├─ Connection timeout (12 seconds)
    ├─ Sandboxed Playwright process
    └─ No credential logging

OUTPUT LAYER:
    ├─ No credentials in responses
    ├─ Safe error messages
    ├─ No stack traces in 4xx responses
    └─ Sanitized 5xx error details

DATA LAYER:
    ├─ Credentials passed in request body
    ├─ Not stored in database
    ├─ Not persisted to disk
    └─ Garbage collected after request
```

## Scalability Considerations

- Each request launches a new browser process
- Browser cleanup happens automatically
- No long-lived connections or sessions
- Suitable for containerization (Docker)
- Can be scaled horizontally with load balancer
- Rate limiting recommended in production

## Future Enhancement Areas

1. **Performance**: Browser process pooling
2. **Features**: Session reuse, proxy support
3. **Security**: Encrypted credential storage
4. **Observability**: Logging, tracing, metrics
5. **Resilience**: Retry logic, circuit breakers

---

For implementation details, see: `IMPLEMENTATION.md`
For workflow details, see: `ENV_SETUP_GUIDE.md`
For complete overview, see: `SETUP_BACKEND_README.md`
