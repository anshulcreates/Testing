# Environment Setup Guide

## Overview

The environment setup phase validates and configures the test environment before running test scenarios. The chatbot collects the website URL and authentication credentials (valid and invalid), verifies the environment is accessible, and then uses this configuration to execute automated tests.

## Workflow

### Phase 1: Data Collection
The chatbot collects:
1. **Website URL** - The URL of the application to be tested
2. **Valid Credentials** - A working username/email and password
3. **Invalid Credentials** - An intentionally wrong username/email and password

### Phase 2: Environment Validation
The backend validates:
- ✓ URL is properly formatted (starts with http:// or https://)
- ✓ URL is reachable (HTTP request succeeds)
- ✓ Page contains a login form
- ✓ All credential fields are provided
- ✓ Status code and page title

### Phase 3: Test Execution
Once validated, the environment is used to:
- Execute test scenarios against the live website
- Simulate user actions (navigation, form filling, clicking buttons)
- Verify expected behaviors
- Collect analytics (pass/fail counts, severity breakdown)

## API Endpoint: `/api/setup-environment`

### Request

**Method:** `POST`

**Content-Type:** `application/json`

**Body:**
```json
{
  "environment": {
    "url": "https://yourapp.com/login",
    "validEmail": "test.user@example.com",
    "validPassword": "SecurePassword123!",
    "invalidEmail": "nonexistent@example.com",
    "invalidPassword": "WrongPassword456"
  }
}
```

### Response (Success)

**Status:** `200 OK`

```json
{
  "reachable": true,
  "status_code": 200,
  "page_title": "Login - MyApp",
  "has_login_form": true,
  "message": "URL reachable — 'Login - MyApp' (HTTP 200)"
}
```

### Response (Failure - Invalid URL)

**Status:** `400 Bad Request`

```json
{
  "detail": "Invalid URL — must start with http:// or https://"
}
```

### Response (Failure - Unreachable URL)

**Status:** `400 Bad Request`

```json
{
  "detail": "Cannot reach URL: Connection refused"
}
```

### Response (Failure - Missing Credentials)

**Status:** `400 Bad Request`

```json
{
  "detail": "Valid email/username cannot be empty."
}
```

## Error Codes

| Status | Error | Reason |
|--------|-------|--------|
| 400 | URL cannot be empty | No URL provided |
| 400 | Invalid URL — must start with http:// or https:// | Malformed URL |
| 400 | Valid email/username cannot be empty | Missing valid credentials |
| 400 | Valid password cannot be empty | Missing valid password |
| 400 | Invalid email/username cannot be empty | Missing invalid credentials |
| 400 | Invalid password cannot be empty | Missing invalid password |
| 400 | Cannot reach URL: [...] | Server unreachable |
| 500 | Environment setup failed: [...] | Unexpected error |

## Full Workflow Example

### Step 1: User Provides Requirements
```
User: "I want to test the login feature of my app at https://myapp.com/login"
```

### Step 2: Chatbot Asks for Environment Setup
```
Chatbot: 
"Great! To test your login feature, I need:
1. A valid username/email and password
2. An invalid username/email and password (for negative testing)

Valid Email: user@myapp.com
Valid Password: TestPass123!
Invalid Email: fake@notexist.com
Invalid Password: WrongPassword
```

### Step 3: Backend Validates Environment
```
POST /api/setup-environment
Request Body:
{
  "environment": {
    "url": "https://myapp.com/login",
    "validEmail": "user@myapp.com",
    "validPassword": "TestPass123!",
    "invalidEmail": "fake@notexist.com",
    "invalidPassword": "WrongPassword"
  }
}

Response:
{
  "reachable": true,
  "status_code": 200,
  "page_title": "MyApp Login",
  "has_login_form": true,
  "message": "URL reachable — 'MyApp Login' (HTTP 200)"
}
```

### Step 4: Generate Test Cases
```
POST /api/generate-tests
Request Body:
{
  "requirements": "..."
}

Response:
{
  "test_cases": [
    {
      "id": "TC-001",
      "name": "Successful Login with Valid Credentials",
      "persona": "Priya - Returning User",
      "description": "User successfully logs in with valid email and password",
      "severity": "CRITICAL",
      "steps": [...]
    },
    ...
  ]
}
```

### Step 5: Run Tests with Environment
```
POST /api/run-tests
Request Body:
{
  "test_cases": [...],
  "environment": {
    "url": "https://myapp.com/login",
    "validEmail": "user@myapp.com",
    "validPassword": "TestPass123!",
    "invalidEmail": "fake@notexist.com",
    "invalidPassword": "WrongPassword"
  }
}

Response:
{
  "results": [...],
  "total": 6,
  "passed": 4,
  "failed": 2,
  "warnings": 0,
  "pass_rate": 67,
  "severity_breakdown": {
    "critical_passed": 2,
    "critical_failed": 1,
    "warning_passed": 1,
    "warning_failed": 0,
    "minor_passed": 1,
    "minor_failed": 1
  },
  "duration_ms": 45000
}
```

### Step 6: Provide Analytics
```
Chatbot Output:
"Test Execution Complete! 📊

SUMMARY:
- Total Tests: 6
- Passed: 4 ✓
- Failed: 2 ✗
- Pass Rate: 67%

CRITICAL ISSUES:
- 1 critical test failed (login authentication)

RECOMMENDED ACTIONS:
1. Fix the password validation logic
2. Add rate limiting for failed login attempts

DETAILED REPORT: [Link to full results]"
```

## Key Features

✅ **URL Validation** - Ensures the website is accessible before testing
✅ **Credentials Management** - Stores both valid and invalid credentials for comprehensive testing
✅ **Form Detection** - Automatically detects if the page has a login form
✅ **Error Handling** - Clear, actionable error messages
✅ **Timeout Protection** - 12-second timeout for URL checks
✅ **Browser Automation** - Uses Playwright for reliable website interaction

## Technical Details

- **Frontend Communication**: The frontend collects environment details and sends them to `/api/setup-environment`
- **Validation Layer**: FastAPI validates all inputs before processing
- **Playwright Integration**: Browser automation checks URL reachability and form presence
- **Credential Storage**: Credentials are passed to test runners securely
- **Analytics Generation**: Test results are analyzed for pass rates and severity breakdown

## Next Steps After Setup

Once the environment is validated:
1. Test cases are generated based on requirements
2. The runner uses the environment configuration to execute tests
3. Results are collected and categorized by severity
4. Human-readable reports are generated using AI narrative generation
5. Analytics are provided to inform decision-making

## Notes

- Credentials are only stored in memory during the test session
- The system uses headless browser automation for security
- All HTTP requests have timeout protection (12 seconds default)
- URL validation is case-insensitive
- Login form detection uses multiple CSS selectors for compatibility
