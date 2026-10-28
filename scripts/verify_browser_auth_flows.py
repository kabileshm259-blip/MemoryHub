#!/usr/bin/env python3
"""
Comprehensive Browser Auth Flow Verification (Milestone 5.1 / Task 4)
Tests in real headless Google Chrome:
1. Valid login -> localStorage token set -> lands on /dashboard
2. Refresh /dashboard -> stays authenticated
3. Logout button -> clears localStorage -> redirects to /login
4. Invalid password -> stays on /login -> displays "Invalid email or password"
5. Unauthenticated /dashboard access -> redirects to /login
"""

import asyncio
import json
import os
import subprocess
import tempfile
import time
import urllib.request
import websockets

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CDP_PORT = 9222
BASE_URL = "http://localhost:3000"


async def run_auth_verification():
    temp_dir = tempfile.mkdtemp()
    chrome_cmd = [
        CHROME_PATH,
        "--headless=new",
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={temp_dir}",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--renderer-process-limit=2",
        "--disable-extensions",
        "--disable-background-networking",
        "--no-first-run",
        "--window-size=1366,850",
    ]
    proc = subprocess.Popen(chrome_cmd)
    time.sleep(2.0)

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json") as r:
            tabs = json.loads(r.read())
        page_tab = [t for t in tabs if t.get("type") == "page"][0]
        ws_url = page_tab["webSocketDebuggerUrl"]

        async with websockets.connect(ws_url, max_size=25_000_000) as ws:
            req_id = 0
            pending_responses = {}

            async def send(method, params=None):
                nonlocal req_id
                req_id += 1
                cid = req_id
                fut = asyncio.get_event_loop().create_future()
                pending_responses[cid] = fut
                payload = {"id": cid, "method": method}
                if params:
                    payload["params"] = params
                await ws.send(json.dumps(payload))
                return await fut

            async def dispatcher():
                try:
                    while True:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        msg_id = data.get("id")
                        if msg_id is not None and msg_id in pending_responses:
                            fut = pending_responses.pop(msg_id)
                            if "error" in data:
                                fut.set_exception(RuntimeError(data["error"]))
                            else:
                                fut.set_result(data.get("result", {}))
                except asyncio.CancelledError:
                    pass

            disp_task = asyncio.create_task(dispatcher())

            await send("Page.enable")
            await send("Runtime.enable")
            await send("DOM.enable")

            async def eval_js(js):
                res = await send("Runtime.evaluate", {"expression": js, "returnByValue": True, "awaitPromise": True})
                return res.get("result", {}).get("value")

            async def set_input(selector, val):
                js = f"""
                (() => {{
                    const el = document.querySelector('{selector}');
                    if (!el) return false;
                    const desc = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');
                    if (desc && desc.set) {{ desc.set.call(el, {json.dumps(val)}); }}
                    else {{ el.value = {json.dumps(val)}; }}
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return true;
                }})()
                """
                return await eval_js(js)

            async def click_el(selector):
                js = f"""
                (() => {{
                    const el = document.querySelector('{selector}');
                    if (!el) return false;
                    el.click();
                    return true;
                }})()
                """
                return await eval_js(js)

            print("==================================================================")
            print("  MEMORYHUB REAL BROWSER AUTHENTICATION SUITE VERIFICATION")
            print("==================================================================")

            # TEST 1: Valid Login
            print("\n[TEST 1] Valid Browser Login -> Dashboard Navigation")
            await send("Page.navigate", {"url": f"{BASE_URL}/login"})
            await asyncio.sleep(2.0)
            await set_input("input[type=\"email\"]", "alice@example.com")
            await set_input("input[type=\"password\"]", "DemoPassword2026!")
            await click_el("button[type=\"submit\"]")
            await asyncio.sleep(3.0)

            url1 = await eval_js("window.location.pathname")
            token1 = await eval_js("localStorage.getItem('memoryhub_auth_token')")
            dom1 = await eval_js("document.body.innerText")
            assert "/dashboard" in url1, f"Expected /dashboard, got {url1}"
            assert token1 and len(token1) > 20, "Missing localStorage token"
            assert "Welcome back, Alice Lead Engineer" in dom1, "Welcome heading missing from dashboard"
            print("  [+] PASSED: Logged in as Alice, token stored, navigated to /dashboard.")

            # TEST 2: Refresh Dashboard & Session Persistence
            print("\n[TEST 2] Page Refresh on Protected Route (/dashboard)")
            await send("Page.reload")
            await asyncio.sleep(2.5)
            url2 = await eval_js("window.location.pathname")
            dom2 = await eval_js("document.body.innerText")
            assert "/dashboard" in url2, f"Expected /dashboard after refresh, got {url2}"
            assert "Alice Lead Engineer" in dom2, "Session lost after refresh"
            print("  [+] PASSED: Session persisted across full page reload.")

            # TEST 3: Logout Flow
            print("\n[TEST 3] Logout Flow")
            await click_el("button[aria-label=\"Log out of account\"]")
            await asyncio.sleep(2.0)
            url3 = await eval_js("window.location.pathname")
            token3 = await eval_js("localStorage.getItem('memoryhub_auth_token')")
            assert "/login" in url3, f"Expected redirect to /login, got {url3}"
            assert not token3, f"Token was not cleared: {token3}"
            print("  [+] PASSED: Logout cleared token and redirected to /login.")

            # TEST 4: Invalid Password Rejection & Error Presentation
            print("\n[TEST 4] Invalid Password Rejection & Error Message")
            await set_input("input[type=\"email\"]", "alice@example.com")
            await set_input("input[type=\"password\"]", "WrongPassword123!")
            await click_el("button[type=\"submit\"]")
            await asyncio.sleep(2.0)
            url4 = await eval_js("window.location.pathname")
            dom4 = await eval_js("document.body.innerText")
            assert "/login" in url4, f"Should remain on /login, got {url4}"
            assert "Invalid email or password" in dom4, f"Expected 'Invalid email or password', got: {dom4[:200]}"
            print("  [+] PASSED: Bad password rejected with message: 'Invalid email or password'.")

            # TEST 5: Protected Route Guard for Unauthenticated Access
            print("\n[TEST 5] Route Guard Protection (Unauthenticated Direct Navigation)")
            await send("Page.navigate", {"url": f"{BASE_URL}/dashboard"})
            await asyncio.sleep(2.0)
            url5 = await eval_js("window.location.pathname")
            assert "/login" in url5, f"Unauthenticated access should redirect to /login, got {url5}"
            print("  [+] PASSED: Direct access to /dashboard redirected unauthenticated visitor to /login.")

            disp_task.cancel()

            print("\n" + "=" * 70)
            print("ALL 5 REAL BROWSER AUTHENTICATION CHECKS PASSED WITH 100% SUCCESS")
            print("=" * 70)

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    asyncio.run(run_auth_verification())

