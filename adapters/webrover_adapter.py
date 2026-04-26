import aiohttp
import asyncio
import json
import re
import os
from models import Environment, StepLog
from runner import _resolve_value, _resolve_url

WEBROVER_BASE_URL = os.getenv("WEBROVER_URL", "http://localhost:8000")
STEP_TIMEOUT = int(os.getenv("WEBROVER_TIMEOUT", "60"))

_FAILURE_PHRASES = [
    "could not", "couldn't", "unable to", "not found",
    "failed to", "cannot", "can't", "no such", "does not exist",
]


def _step_to_query(step: str, env: Environment) -> str:
    """Translate a TestSense step into a natural-language WebRover query."""
    s = step.strip()
    sl = s.lower()

    if sl.startswith("navigate"):
        url_match = re.search(r"`([^`]+)`", s)
        if url_match:
            url = _resolve_url(url_match.group(1), env.url)
            return f"Navigate to {url}"
        return s

    if sl.startswith("enter"):
        value = _resolve_value(s, env)
        field_match = (
            re.search(r"in the '([^']+)'\s+field", s, re.IGNORECASE) or
            re.search(r"in the '([^']+)'", s, re.IGNORECASE) or
            re.search(r"'([^']+)'\s+field", s, re.IGNORECASE)
        )
        field = field_match.group(1) if field_match else "field"
        # Mask password value in query so it's not leaked in logs
        display = "a password" if "password" in field.lower() else f"'{value}'"
        return f"Type {display} into the '{field}' input field"

    if sl.startswith("leave"):
        field_match = re.search(r"'([^']+)'", s)
        field = field_match.group(1) if field_match else "field"
        return f"Clear the '{field}' field and leave it empty"

    if sl.startswith("click"):
        btn_match = re.search(r"'([^']+)'", s)
        btn = btn_match.group(1) if btn_match else "button"
        return f"Click the '{btn}' button"

    # verify / confirm / check / wait / select — pass as natural language
    return s


async def _collect_sse(resp) -> dict:
    """Read an SSE stream and collect the key events."""
    result = {"final_response": None, "error": None}
    async for raw in resp.content:
        line = raw.decode("utf-8").strip()
        if not line.startswith("data:"):
            continue
        try:
            event = json.loads(line[5:].strip())
        except Exception:
            continue
        etype = event.get("type", "")
        if etype == "final_response":
            result["final_response"] = event.get("content", "")
        elif etype == "error":
            result["error"] = event.get("content", "")
        elif etype == "end":
            break
    return result


def _infer_success(response_text: str) -> bool:
    text = (response_text or "").lower()
    return not any(phrase in text for phrase in _FAILURE_PHRASES)


class WebRoverAdapter:
    def __init__(self, base_url: str = WEBROVER_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self._available: bool | None = None

    async def is_available(self) -> bool:
        """Ping WebRover to check if it's running."""
        if self._available is not None:
            return self._available
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    f"{self.base_url}/docs",
                    timeout=aiohttp.ClientTimeout(total=3)
                ) as r:
                    self._available = r.status < 500
        except Exception:
            self._available = False
        return self._available

    async def setup(self, url: str) -> bool:
        """Tell WebRover to launch/connect Chrome and navigate to the starting URL."""
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    f"{self.base_url}/setup-browser",
                    json={"url": url},
                    timeout=aiohttp.ClientTimeout(total=40)
                ) as r:
                    data = await r.json()
                    return data.get("status") == "success"
        except Exception:
            return False

    async def execute_step(self, step: str, env: Environment, step_num: int) -> StepLog:
        """Execute one test step via WebRover's task agent."""
        query = _step_to_query(step, env)
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    f"{self.base_url}/query",
                    json={"query": query, "agent_type": "task"},
                    timeout=aiohttp.ClientTimeout(total=STEP_TIMEOUT)
                ) as resp:
                    if resp.status != 200:
                        return StepLog(
                            step_number=step_num, step=step, success=False,
                            log=f"[WebRover] HTTP {resp.status}"
                        )
                    events = await _collect_sse(resp)

            if events["error"]:
                return StepLog(
                    step_number=step_num, step=step, success=False,
                    log=f"[WebRover] {events['error'][:180]}"
                )

            response_text = events["final_response"] or ""
            success = _infer_success(response_text)
            log_msg = f"[WebRover] {response_text[:200]}" if response_text else "[WebRover] Step executed"
            return StepLog(step_number=step_num, step=step, success=success, log=log_msg)

        except asyncio.TimeoutError:
            return StepLog(
                step_number=step_num, step=step, success=False,
                log="[WebRover] Timeout — step took too long"
            )
        except Exception as e:
            return StepLog(
                step_number=step_num, step=step, success=False,
                log=f"[WebRover] Adapter error: {str(e)[:150]}"
            )

    async def cleanup(self) -> None:
        """Release the browser session on the WebRover server."""
        try:
            async with aiohttp.ClientSession() as s:
                await s.post(
                    f"{self.base_url}/cleanup",
                    timeout=aiohttp.ClientTimeout(total=10)
                )
        except Exception:
            pass
