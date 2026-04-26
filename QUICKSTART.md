# Quick Start - Environment Setup Backend

## What's New?

A new endpoint `/api/setup-environment` that validates the test environment before running tests.

**Endpoint**: `POST /api/setup-environment`  
**Status**: ✅ Ready to use

---

## 1. Start the Server

```bash
cd /Users/anshullalawat/testsense-backend

# Activate virtual environment
source venv/bin/activate

# Start server
uvicorn main:app --reload
```

**Expected Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

---

## 2. Test the Endpoint

### Simple Test
```bash
curl -X POST http://localhost:8000/api/setup-environment \
  -H "Content-Type: application/json" \
  -d '{
    "environment": {
      "url": "https://www.google.com",
      "validEmail": "test@example.com",
      "validPassword": "password123",
      "invalidEmail": "wrong@test.com",
      "invalidPassword": "wrongpass"
    }
  }'
```

**Response (Success):**
```json
{
  "reachable": true,
  "status_code": 200,
  "page_title": "Google",
  "has_login_form": false,
  "message": "URL reachable — 'Google' (HTTP 200)"
}
```

### Error Test
```bash
curl -X POST http://localhost:8000/api/setup-environment \
  -H "Content-Type: application/json" \
  -d '{
    "environment": {
      "url": "not-a-url",
      "validEmail": "test@example.com",
      "validPassword": "password123",
      "invalidEmail": "wrong@test.com",
      "invalidPassword": "wrongpass"
    }
  }'
```

**Response (Error):**
```json
{
  "detail": "Invalid URL — must start with http:// or https://"
}
```

---

## 3. Integration with Chatbot

### Workflow
1. **User tells chatbot**: "Test my login at https://myapp.com/login"
2. **Chatbot asks**: "What are your test credentials?"
3. **Backend validates** (NEW):
   ```
   POST /api/setup-environment
   {
     "environment": {
       "url": "https://myapp.com/login",
       "validEmail": "user@myapp.com",
       "validPassword": "SecurePass123!",
       "invalidEmail": "fake@test.com",
       "invalidPassword": "WrongPass456"
     }
   }
   ```
4. **Chatbot receives**:
   ```json
   {
     "reachable": true,
     "status_code": 200,
     "page_title": "MyApp Login",
     "has_login_form": true,
     "message": "✓ Environment ready!"
   }
   ```
5. **Chatbot continues**: "Great! Now I'll generate and run tests..."

---

## 4. Required Fields

All fields must be provided and non-empty:

| Field | Type | Example | Purpose |
|-------|------|---------|---------|
| `url` | string | `https://myapp.com/login` | Website to test |
| `validEmail` | string | `user@myapp.com` | Working username |
| `validPassword` | string | `SecurePass123!` | Working password |
| `invalidEmail` | string | `fake@noexist.com` | Non-working username |
| `invalidPassword` | string | `WrongPass456` | Wrong password |

---

## 5. Response Fields

| Field | Type | Meaning |
|-------|------|---------|
| `reachable` | boolean | Is the URL accessible? |
| `status_code` | integer | HTTP status code (200, 404, etc.) |
| `page_title` | string | HTML page title |
| `has_login_form` | boolean | Does page contain a login form? |
| `message` | string | Human-readable status message |

---

## 6. Error Responses

### Missing URL
```json
{"detail": "URL cannot be empty."}
```

### Invalid URL Format
```json
{"detail": "Invalid URL — must start with http:// or https://"}
```

### Missing Credentials
```json
{"detail": "Valid email/username cannot be empty."}
```

### URL Unreachable
```json
{"detail": "Cannot reach URL: Connection refused"}
```

### Server Error
```json
{"detail": "Environment setup failed: [error details]"}
```

---

## 7. Files Modified

**main.py** (Lines 37-75)
- Added `/api/setup-environment` endpoint
- Input validation
- Environment verification
- Response formatting

**No breaking changes** - All existing endpoints work as before.

---

## 8. Documentation

- **ENV_SETUP_GUIDE.md** - Complete workflow guide
- **IMPLEMENTATION.md** - Technical implementation details
- **ARCHITECTURE.md** - System architecture diagrams
- **SETUP_BACKEND_README.md** - Full overview

---

## 9. Testing Checklist

- ✅ Server starts without errors
- ✅ Valid URL returns `reachable: true`
- ✅ Invalid URL format rejected with 400 error
- ✅ Missing credentials rejected with 400 error
- ✅ Unreachable URL returns `reachable: false`
- ✅ Response includes all required fields
- ✅ No sensitive data in error messages

---

## 10. Next Steps

1. **Frontend/Chatbot**: Collect environment details from user
2. **Send**: POST request to `/api/setup-environment`
3. **Check**: `reachable` field in response
4. **Proceed**: Generate tests if environment is valid
5. **Run**: Execute tests using the same environment config

---

## Common Issues

### Issue: "Cannot reach URL"
**Solution**: Verify the URL is:
- Spelled correctly
- Includes `http://` or `https://`
- Actually accessible from your network

### Issue: "Valid email/username cannot be empty"
**Solution**: Provide all 4 credential fields (valid + invalid for each)

### Issue: "Browser timeout"
**Solution**: URL takes too long to load, try a faster website or check network connection

---

## Architecture

```
Frontend/Chatbot
       ↓
POST /api/setup-environment
       ↓
Validate URL Format
       ↓
Validate Credentials
       ↓
Launch Browser (Playwright)
       ↓
Navigate to URL
       ↓
Extract Metadata
       ↓
Close Browser
       ↓
Return Response
       ↓
Frontend/Chatbot
```

---

**Status**: ✅ Ready for Production

For detailed information, see the documentation files in this directory.
