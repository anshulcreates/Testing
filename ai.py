import os
import json
import re
from groq import Groq
from dotenv import load_dotenv
from models import TestCase

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

STEP_FORMAT_EXAMPLES = """
LEARN FROM THESE EXAMPLES. FOLLOW THIS EXACT FORMAT FOR EVERY STEP YOU WRITE.

EXAMPLE 1 — Successful Signup
1. Navigate to the signup page at `https://bhavishyayaan.com/signup`.
2. Enter a valid email in the 'Email/Username' field.
3. Enter a password that is exactly 6 characters long in the 'Password' field.
4. Click on the 'Sign Up' button.
5. Verify that the account is created successfully.
6. Confirm that the user is redirected to the login page or auto-logged in.

EXAMPLE 2 — Duplicate Email Error
1. Navigate to the signup page at `https://bhavishyayaan.com/signup`.
2. Enter an email that is already registered in the 'Email/Username' field.
3. Enter a valid password (6-8 characters) in the 'Password' field.
4. Click on the 'Sign Up' button.
5. Verify that the error message 'User already exists' is displayed.

EXAMPLE 3 — Invalid Email Format
1. Navigate to the signup page at `https://bhavishyayaan.com/signup`.
2. Enter an invalid email format (e.g., 'invalidemail') in the 'Email/Username' field.
3. Enter a valid password (6-8 characters) in the 'Password' field.
4. Click on the 'Sign Up' button.
5. Verify that a clear error message is displayed regarding the invalid email format.

EXAMPLE 4 — Empty Fields Validation
1. Navigate to the signup page at `https://bhavishyayaan.com/signup`.
2. Leave the 'Email/Username' field empty.
3. Leave the 'Password' field empty.
4. Click on the 'Sign Up' button.
5. Verify that the error message 'All fields are required' is displayed.

EXAMPLE 5 — Successful Login
1. Navigate to the login page at `https://bhavishyayaan.com/login`.
2. Enter a valid email address in the 'User ID / Email' field.
3. Enter a valid password in the 'Password' field.
4. Click the 'Login' button.
5. Verify that the user is authenticated and redirected to the Dashboard.
6. Confirm that a session is created successfully.

EXAMPLE 6 — Invalid Login Credentials
1. Navigate to the login page at `https://bhavishyayaan.com/login`.
2. Enter a valid email address in the 'User ID / Email' field.
3. Enter an incorrect password in the 'Password' field.
4. Click the 'Login' button.
5. Verify that the error message 'Invalid login credentials. Please try again.' is displayed.
6. Confirm that the user remains on the login screen and no session is created.

STEP WRITING RULES:
- Start every step with: Navigate, Enter, Leave, Click, Select, Check, Verify, Confirm, Wait, Submit
- Navigate → always include full URL in backticks
- Enter → say exactly WHAT to enter and name the FIELD in single quotes
- Leave → say the FIELD name in single quotes and 'empty'
- Click → name the exact BUTTON or LINK label in single quotes
- Verify/Confirm → state the EXACT expected outcome (error text in quotes, redirect URL, element name)
- Never write vague steps — be specific about values, fields, buttons, and outcomes
- 4 to 7 steps per test case
"""

HOW_TO_ANALYSE = """
HOW TO READ ANY REQUIREMENT FORMAT:

Requirements arrive in many forms. Always extract:
1. FEATURE/MODULE — what is being tested (Login, Signup, Checkout, Profile, etc.)
2. FIELD NAMES — exact names of inputs (Email, Password, User ID, Phone, etc.)
3. VALIDATION RULES — min/max length, format, required/optional
4. EXACT ERROR MESSAGES — copy them word for word from the requirements
5. SUCCESS OUTCOMES — what happens on success (redirect URL, session created, confirmation shown)
6. FAILURE OUTCOMES — what stays/shows on failure (stay on page, error text, no session)
7. ALTERNATIVE FLOWS — Google login, OTP, Apple ID, guest checkout, etc.
8. EDGE CASES — empty fields, duplicate data, wrong format, spaces, boundary values

Cover both POSITIVE (happy path) and NEGATIVE (error/edge case) scenarios.
"""


def _call(prompt: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw


def chat_with_qa(message: str, history: list, requirements: str) -> dict:
    history_text = "\n".join(
        f"{'User' if m['role'] == 'user' else 'TestSense'}: {m['content']}"
        for m in history[-6:]
    )
    prompt = f"""You are TestSense, a friendly QA assistant helping a startup founder plan software tests.

CONVERSATION SO FAR:
{history_text or "(new conversation)"}

USER'S MESSAGE:
{message}

REQUIREMENTS GATHERED SO FAR:
{requirements or "(none yet)"}

Your goal:
- Understand what feature or flow the user wants to test
- Ask one short clarifying question if you're missing key details (field names, error messages, success outcomes)
- Once you have enough context, list 3-5 plain-English test scenarios you'll cover
- Tell the user to type /create when they're ready to generate the actual test cases

Rules:
- Warm, conversational tone — no technical jargon
- 2-4 sentences max in your reply
- Only list scenarios when you have enough context to be specific

Return ONLY valid JSON. No markdown. No explanation.

{{
  "reply": "your conversational response here",
  "scenarios": ["scenario title 1", "scenario title 2"]
}}
"""
    try:
        return json.loads(_call(prompt))
    except Exception:
        return {"reply": "Tell me more about what you'd like to test!", "scenarios": []}


def plan_tests(requirements: str) -> dict:
    prompt = f"""
You are a QA engineer explaining your test plan to a non-technical startup founder.

Read the requirements below and explain in simple, warm, plain English what you will test.
No technical jargon. Write like you're talking to a friend.

REQUIREMENTS:
{requirements}

Return a JSON with exactly two keys:
- "summary": 2-3 sentences explaining what the feature does and what you'll verify (conversational tone)
- "scenarios": list of 5-7 short plain-English test scenario titles — what situation you'll test, not how

Example scenario titles:
- "User logs in with the correct email and password"
- "User tries to log in with the wrong password"
- "User leaves the email field empty and submits"

Return ONLY valid JSON. No markdown. No explanation.

{{
  "summary": "...",
  "scenarios": ["...", "...", "..."]
}}
"""
    try:
        return json.loads(_call(prompt))
    except Exception:
        return {"summary": "I'll test the core flows from your requirements.", "scenarios": []}


def generate_test_cases(requirements: str) -> list[TestCase]:
    prompt = f"""
You are a senior QA engineer who writes precise, step-by-step test cases.

{STEP_FORMAT_EXAMPLES}

{HOW_TO_ANALYSE}

---
NOW ANALYSE THESE REQUIREMENTS AND GENERATE TEST CASES:

{requirements}

---
GENERATION RULES:
- Read every word of the requirements before generating
- Use the EXACT field names, button labels, and error messages from the requirements
- Use Indian first names for personas: Priya, Arjun, Mahesh, Sneha, Kavya, Rohan, Neha, Vikram
- If a URL is mentioned use it; otherwise use `https://yourapp.com/[page]`
- Generate exactly 6 test cases — mix of positive and negative scenarios
- Severity: CRITICAL (auth/payment/core flows), WARNING (performance/UX), MINOR (cosmetic/optional)

Return ONLY a valid JSON array. No explanation. No markdown. No code blocks.

[
  {{
    "id": "TC-001",
    "name": "Descriptive test name",
    "persona": "Indian name — context (e.g. first time user, returning customer)",
    "description": "One sentence describing what is being tested and the expected outcome.",
    "severity": "CRITICAL",
    "steps": [
      "Navigate to the page at `https://yourapp.com/page`.",
      "Enter a valid email in the 'Email' field.",
      "Enter a valid password (6-8 characters) in the 'Password' field.",
      "Click the 'Submit' button.",
      "Verify that the user is redirected to the Dashboard.",
      "Confirm that a session token is created."
    ]
  }}
]
"""
    data = json.loads(_call(prompt))
    return [
        TestCase(
            id=tc["id"],
            name=tc["name"],
            persona=tc["persona"],
            description=tc["description"],
            severity=tc["severity"].upper(),
            steps=tc.get("steps", []),
        )
        for tc in data
    ]


def ai_verify_step(step: str, url: str, body: str) -> dict:
    prompt = f"""You are a test automation engine evaluating a verification step.

VERIFICATION STEP: {step}

CURRENT PAGE STATE:
- URL: {url}
- Page content: {body[:3000]}

Did this verification PASS or FAIL based on the current page state?
Return ONLY valid JSON. No markdown. No explanation.

{{"success": true, "reason": "brief explanation of what you found"}}
"""
    try:
        return json.loads(_call(prompt))
    except Exception:
        return {"success": False, "reason": "AI could not evaluate this verification step"}


def generate_story_report(tc: TestCase, success: bool, step_logs: list, url: str) -> dict:
    status = "PASSED" if success else "FAILED"
    logs_text = "\n".join(
        f"  Step {i+1}: {'✓' if sl['success'] else '✗'} {sl['step']} → {sl['log']}"
        for i, sl in enumerate(step_logs)
    )
    prompt = f"""
You are writing a plain-English test report for a non-technical startup founder.

TEST:
- Name: {tc.name}
- Persona: {tc.persona}
- Tested: {tc.description}
- URL: {url}
- Result: {status}

Step-by-step execution log:
{logs_text}

Write a 3-5 sentence story from the persona's first-person perspective.
Use their first name. Make it human and emotional — not technical.
If FAILED: describe where exactly it broke and the frustration.
If PASSED: describe the smooth, satisfying experience.

If FAILED or WARNING: add one "Business Impact" sentence explaining the real-world consequence for the founder.

Return ONLY valid JSON. No markdown. No explanation.

{{
  "story": "...",
  "impact": "..." or null
}}
"""
    return json.loads(_call(prompt))
