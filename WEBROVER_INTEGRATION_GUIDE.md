# WebRover Integration Guide for TestSense

## Executive Summary

WebRover is an AI-powered web automation agent that acts like a human user. By integrating WebRover with TestSense, we can replace basic Playwright automation with intelligent, adaptive web interactions that:

- ✅ Understand page context (not just CSS selectors)
- ✅ Recover from errors automatically
- ✅ Stream real-time actions to the user
- ✅ Adapt to dynamic UI changes
- ✅ Generate intelligent test reports

## Current Architecture

```
TestSense Backend
├── Generate Tests (AI)
├── Setup Environment (validation)
├── Run Tests (Playwright)
│   ├── Navigate to URLs
│   ├── Fill forms
│   ├── Click buttons
│   └── Verify outcomes
└── Report Analytics
```

## Integration Architecture

```
TestSense Backend                WebRover Backend
├── Generate Tests               FastAPI @ 8000
├── Setup Environment            ├── task_agent.py
├── Integration Layer (NEW)  ←→  ├── browser_manager.py
│   ├── API calls                └── /query endpoint
│   ├── Credential handling
│   ├── Result mapping
│   └── Error recovery
└── Report Analytics
```

## Integration Plan

### Phase 1: Understanding WebRover (This Session)

**Location**: `/tmp/WebRover`

**Key Components**:
- `backend/app/main.py` - FastAPI endpoints
- `backend/app/task_agent.py` - Task automation logic
- `backend/app/browser_manager.py` - Browser session management
- `backend/Browser/webrover_browser.py` - Playwright wrapper

**Setup**:
```bash
cd /tmp/WebRover/backend
# Install dependencies (requires Poetry or pip)
poetry install
# Run backend
poetry run uvicorn app.main:app --reload --port 8000
```

### Phase 2: Create Adapter Layer (Next Session)

**File**: `testsense-backend/adapters/webrover_adapter.py`

```python
class WebRoverAdapter:
    """Adapter to use WebRover for test execution"""
    
    def __init__(self, webrover_url: str = "http://localhost:8000"):
        self.webrover_url = webrover_url
        self.session = None
    
    async def setup_browser(self, url: str):
        """Setup browser for testing"""
        response = await http_client.post(
            f"{self.webrover_url}/setup-browser",
            json={"url": url}
        )
        return response.json()
    
    async def execute_step(self, step: str, context: dict):
        """Execute a test step using WebRover"""
        response = await http_client.post(
            f"{self.webrover_url}/query",
            json={
                "query": step,
                "agent_type": "task"
            }
        )
        return response.json()
    
    async def cleanup(self):
        """Cleanup browser session"""
        response = await http_client.post(
            f"{self.webrover_url}/cleanup"
        )
        return response.json()
```

### Phase 3: Modify Test Runner

**Current File**: `testsense-backend/runner.py`

**Changes**:
1. Add WebRover option for test execution
2. Keep existing Playwright as fallback
3. Stream results in real-time
4. Handle errors gracefully

```python
# Current approach (direct Playwright)
def run_all_tests(test_cases, environment):
    results = []
    for test_case in test_cases:
        result = execute_test_case_direct(test_case, environment)
        results.append(result)
    return results

# New approach (with WebRover)
async def run_all_tests_with_webrover(test_cases, environment, use_webrover=True):
    results = []
    adapter = WebRoverAdapter()
    
    try:
        # Setup WebRover browser
        await adapter.setup_browser(environment.url)
        
        for test_case in test_cases:
            # Execute step by step
            result = await execute_test_case_webrover(
                test_case, 
                environment,
                adapter
            )
            results.append(result)
            
            # Stream result in real-time
            yield result
    
    finally:
        # Cleanup
        await adapter.cleanup()
```

### Phase 4: Update Endpoints

**File**: `testsense-backend/main.py`

**New Endpoint**:
```python
@app.post("/api/run-tests-streaming")
async def run_tests_streaming(body: RunTestsRequest):
    """Run tests with real-time streaming using WebRover"""
    async def event_generator():
        adapter = WebRoverAdapter()
        try:
            for result in run_all_tests_with_webrover(
                body.test_cases,
                body.environment
            ):
                # Stream each result as it completes
                yield json.dumps(result.dict()) + "\n"
        finally:
            await adapter.cleanup()
    
    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson"
    )
```

## Comparison: Direct Playwright vs WebRover

### Element Detection

**Direct Playwright**:
```python
# Hardcoded selectors
email_input = page.locator('input[name="email"]')
password_input = page.locator('input[type="password"]')
```

**WebRover**:
```python
# AI-powered detection
response = await adapter.execute_step(
    "Fill email field with user@test.com"
    # Agent finds field dynamically
)
```

### Error Handling

**Direct Playwright**:
```python
try:
    page.click('button:has-text("Login")')
except TimeoutError:
    # Test fails, move to next
    pass
```

**WebRover**:
```python
# Agent adapts automatically
response = await adapter.execute_step(
    "Click the login button"
    # If button not found, agent searches for alternatives
)
```

### Real-time Feedback

**Direct Playwright**:
```python
# Collect all results, then return
results = run_all_tests(test_cases)
return {"results": results}  # Batch response
```

**WebRover**:
```python
# Stream results as they complete
async def event_generator():
    for result in run_all_tests(test_cases):
        yield json.dumps(result) + "\n"  # Real-time
```

## Implementation Steps

### Step 1: Setup WebRover Locally
```bash
# Clone and setup
cd /tmp/WebRover
cd backend
poetry install  # Install dependencies
poetry run uvicorn app.main:app --reload --port 8000

# In another terminal, verify it's running
curl http://localhost:8000/docs
```

### Step 2: Create Adapter
```python
# File: testsense-backend/adapters/webrover_adapter.py
import aiohttp
from typing import Dict, Any

class WebRoverAdapter:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()
    
    async def setup_browser(self, url: str) -> Dict[str, Any]:
        """Setup browser for testing"""
        async with self.session.post(
            f"{self.base_url}/setup-browser",
            json={"url": url}
        ) as resp:
            return await resp.json()
    
    async def query(self, query: str, agent_type: str = "task"):
        """Execute query using specified agent"""
        async with self.session.post(
            f"{self.base_url}/query",
            json={"query": query, "agent_type": agent_type}
        ) as resp:
            return await resp.json()
    
    async def cleanup(self):
        """Cleanup browser session"""
        async with self.session.post(
            f"{self.base_url}/cleanup"
        ) as resp:
            return await resp.json()
```

### Step 3: Create Hybrid Runner
```python
# File: testsense-backend/hybrid_runner.py
from adapters.webrover_adapter import WebRoverAdapter

async def execute_test_step_hybrid(
    step: str,
    environment: Environment,
    context: Dict[str, Any],
    use_webrover: bool = True
) -> StepLog:
    """Execute step, using WebRover if available, fallback to Playwright"""
    
    if use_webrover:
        try:
            async with WebRoverAdapter() as adapter:
                result = await adapter.query(step, agent_type="task")
                return StepLog(
                    step_number=context.get("step_num", 0),
                    step=step,
                    success=result.get("success", False),
                    log=result.get("message", ""),
                    metadata=result
                )
        except Exception as e:
            print(f"WebRover failed: {e}, falling back to direct Playwright")
            # Fall back to direct Playwright
    
    # Direct Playwright execution
    return execute_test_step_direct(step, environment, context)
```

### Step 4: Update Main Endpoint
```python
# In main.py
@app.post("/api/run-tests")
async def run_tests(body: RunTestsRequest):
    """Run tests with WebRover integration"""
    use_webrover = body.use_webrover if hasattr(body, 'use_webrover') else False
    
    if use_webrover:
        return await run_tests_with_webrover(body)
    else:
        return run_tests_direct(body)
```

## Testing the Integration

### Test 1: Basic Setup
```bash
# Terminal 1: Start WebRover
cd /tmp/WebRover/backend
poetry run uvicorn app.main:app --reload --port 8000

# Terminal 2: Start TestSense
cd /Users/anshullalawat/testsense-backend
source venv/bin/activate
uvicorn main:app --reload --port 8001

# Terminal 3: Test
curl -X POST http://localhost:8001/api/run-tests \
  -H "Content-Type: application/json" \
  -d '{
    "test_cases": [...],
    "environment": {...},
    "use_webrover": true
  }'
```

### Test 2: Real-time Streaming
```python
import aiohttp
import asyncio

async def test_streaming():
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8001/api/run-tests-streaming",
            json={
                "test_cases": [...],
                "environment": {...},
                "use_webrover": true
            }
        ) as resp:
            async for line in resp.content:
                result = json.loads(line)
                print(f"Test: {result['name']} → {result['status']}")

asyncio.run(test_streaming())
```

## Configuration

### Environment Variables
```env
# WebRover connection
WEBROVER_URL=http://localhost:8000
WEBROVER_ENABLED=true

# Fallback strategy
FALLBACK_TO_PLAYWRIGHT=true
WEBROVER_TIMEOUT=30
```

### Updated Models
```python
# In models.py
class RunTestsRequest(BaseModel):
    test_cases: List[TestCase]
    environment: Environment
    use_webrover: bool = False  # NEW
    stream_results: bool = False  # NEW

class StepLog(BaseModel):
    step_number: int
    step: str
    success: bool
    log: str
    agent: str = "playwright"  # NEW - "playwright" or "webrover"
    metadata: Optional[Dict[str, Any]] = None  # NEW
```

## Benefits

| Benefit | Impact |
|---------|--------|
| AI-powered element detection | More reliable tests |
| Automatic error recovery | Fewer false negatives |
| Real-time streaming | Better user experience |
| Adaptive navigation | Works with dynamic UIs |
| Fallback support | No breaking changes |
| Research mode | Deeper analysis when needed |

## Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| Extra dependency | Keep as optional, provide fallback |
| Network latency | Cache common queries, optimize communication |
| State synchronization | Clear session management, explicit cleanup |
| Credential security | Pass credentials securely between services |
| Deployment complexity | Docker compose for local dev, separate containers for prod |

## Migration Path

### Phase 1 (Week 1-2): Parallel Deployment
- Deploy WebRover alongside TestSense
- Add adapter layer (non-breaking)
- Test both implementations

### Phase 2 (Week 3-4): Gradual Adoption
- Add `use_webrover` flag to API
- Default to current Playwright
- Monitor WebRover performance

### Phase 3 (Month 2): Full Integration
- Make WebRover primary (if stable)
- Keep Playwright as fallback
- Update documentation

### Phase 4 (Month 3): Optimization
- Fine-tune prompts
- Add caching
- Optimize performance

## Deployment

### Local Development
```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  testsense-backend:
    build: ./testsense-backend
    ports:
      - "8001:8000"
    environment:
      WEBROVER_URL: http://webrover:8000

  webrover-backend:
    build: ./WebRover/backend
    ports:
      - "8000:8000"
```

### Production
```bash
# Separate container deployment
# Each service can be scaled independently
docker run -p 8001:8000 testsense-backend
docker run -p 8000:8000 webrover-backend
```

## Success Metrics

- **Test Pass Rate**: Increase from current baseline
- **Execution Time**: Compare direct Playwright vs WebRover
- **Error Recovery Rate**: Measure automatic fallbacks
- **Real-time Feedback**: User satisfaction with streaming
- **Cost**: Monitor API usage for WebRover agents

## Next Steps

1. ✅ Review WebRover codebase
2. ✅ Understand architecture
3. → Create adapter implementation
4. → Test integration locally
5. → Deploy to staging
6. → Measure performance
7. → Full production rollout

## Resources

- WebRover GitHub: https://github.com/hrithikkoduri/WebRover
- TestSense Backend: `/Users/anshullalawat/testsense-backend`
- WebRover Local: `/tmp/WebRover`

## Questions?

Refer to:
- `WEBROVER_ANALYSIS.md` - Architecture overview
- WebRover README - Original project documentation
- Integration tests - See `/tests/integration/` (to be created)

---

**Status**: Ready for Phase 2 Implementation
**Maintainer**: Development Team
**Last Updated**: 2024
