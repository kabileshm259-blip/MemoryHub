#!/usr/bin/env python3
"""
Comprehensive Browser Verification Script for Milestone 6.0:
Interactive Workflow Demonstrations & Dedicated AI Knowledge Chat.
Uses real headless Google Chrome via CDP (Chrome DevTools Protocol).
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
BACKEND_URL = "http://127.0.0.1:8000"


async def main():
    print("=== Milestone 6.0 Interactive Feature Verification ===")
    
    # 1. Verify backend readiness
    try:
        with urllib.request.urlopen(f"{BACKEND_URL}/health/readiness", timeout=5) as r:
            health = json.loads(r.read().decode())
            print(f"[*] Backend health: {health.get('status')} (database_mode: {health.get('database_mode')})")
    except Exception as e:
        print(f"[!] Backend unreachable: {e}")
        return False

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
        "--window-size=1400,900",
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
            pending = {}

            async def send(method, params=None):
                nonlocal req_id
                req_id += 1
                cid = req_id
                fut = asyncio.get_event_loop().create_future()
                pending[cid] = fut
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
                        mid = data.get("id")
                        if mid is not None and mid in pending:
                            fut = pending.pop(mid)
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

            async def wait_for(predicate_js, timeout=12.0, interval=0.4):
                start = time.time()
                while time.time() - start < timeout:
                    val = await eval_js(predicate_js)
                    if val:
                        return val
                    await asyncio.sleep(interval)
                return None

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

            async def set_textarea(selector, val):
                js = f"""
                (() => {{
                    const el = document.querySelector('{selector}');
                    if (!el) return false;
                    const desc = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value');
                    if (desc && desc.set) {{ desc.set.call(el, {json.dumps(val)}); }}
                    else {{ el.value = {json.dumps(val)}; }}
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return true;
                }})()
                """
                return await eval_js(js)

            # --- STEP 1: Log in with demo account ---
            print("\n[TEST 1] Logging in as Alice (Owner)...")
            await send("Page.navigate", {"url": f"{BASE_URL}/login"})
            await asyncio.sleep(2.5)  # wait for Next.js React hydration

            await set_input('input[type="email"]', "alice@example.com")
            await set_input('input[type="password"]', "DemoPassword2026!")
            await asyncio.sleep(0.5)

            # Submit form
            await eval_js("document.querySelector('button[type=\"submit\"]').click()")
            await asyncio.sleep(3.0)

            dashboard_reached = await eval_js("window.location.pathname === '/dashboard'")
            token = await eval_js("localStorage.getItem('memoryhub_auth_token')")
            print(f" -> Logged in successfully: {dashboard_reached} (token length: {len(token) if token else 0})")
            assert dashboard_reached, "Failed to reach /dashboard after login"

            # --- STEP 2: Navigate to /chat ---
            print("\n[TEST 2] Navigating to Dedicated AI Knowledge Chat (/chat)...")
            await send("Page.navigate", {"url": f"{BASE_URL}/chat"})
            await asyncio.sleep(2.5)  # wait for React hydration
            chat_ready = await wait_for("document.querySelector('#chat-project-select') !== null", timeout=8.0)
            print(f" -> /chat loaded: {chat_ready}")
            assert chat_ready, "Failed to load /chat page"

            # Select the E-Commerce Platform project which contains the seeded sources
            await eval_js("""
                (() => {
                    const sel = document.querySelector('#chat-project-select');
                    const opt = Array.from(sel.options).find(o => o.text.includes('E-Commerce'));
                    if (opt) {
                        sel.value = opt.value;
                        sel.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                })()
            """)
            await asyncio.sleep(1.0)

            active_project = await eval_js("document.querySelector('#chat-project-select').value")
            print(f" -> Active project ID in selector: {active_project}")

            suggested_count = await eval_js("document.querySelectorAll('button span.block').length")
            print(f" -> Suggested demo questions rendered: {suggested_count}")
            assert suggested_count >= 4, f"Expected at least 4 suggested questions, found {suggested_count}"

            # --- STEP 3: Ask grounded question ---
            print("\n[TEST 3] Asking grounded question: Redis session-cache issue under flash-sale traffic...")
            grounded_q = "What Redis session-cache issue was documented under flash-sale traffic?"
            await set_textarea("textarea", grounded_q)
            await eval_js("document.querySelector('button[type=\"submit\"]').click()")

            # Wait for assistant response
            print(" -> Waiting for assistant response...")
            asst_answered = await wait_for(
                "document.querySelectorAll('.rounded-2xl.whitespace-pre-wrap').length >= 2",
                timeout=15.0
            )
            # Wait for spinner in chat to finish
            await wait_for("!document.querySelector('textarea').disabled", timeout=10.0)
            print(f" -> Answer bubble rendered: {bool(asst_answered)}")
            assert asst_answered, "Assistant did not return an answer in time"

            # Inspect answer content, provider badge, citations
            answer_text = await eval_js("""
                (() => {
                    const bubbles = document.querySelectorAll('.rounded-2xl.whitespace-pre-wrap');
                    return bubbles.length > 0 ? bubbles[bubbles.length - 1].innerText : '';
                })()
            """)
            print(f" -> Answer snippet: {answer_text[:120]}...")
            assert len(answer_text) > 30, "Answer text was unexpectedly empty"

            citations_rendered = await eval_js("document.querySelectorAll('button .truncate.font-semibold').length")
            print(f" -> Number of verified citation cards: {citations_rendered}")
            assert citations_rendered > 0, "Expected at least 1 verified citation card"

            provider_badge = await eval_js("""
                (() => {
                    const badges = Array.from(document.querySelectorAll('span'));
                    const p = badges.find(b => b.innerText.includes('Flash') || b.innerText.includes('Heuristic') || b.innerText.includes('Engine'));
                    return p ? p.innerText : '';
                })()
            """)
            print(f" -> Active provider badge: {provider_badge}")
            assert provider_badge, "No provider badge found"

            # --- STEP 4: Ask ungrounded question (Honest Abstention) ---
            print("\n[TEST 4] Asking out-of-scope question for honest abstention test...")
            out_of_scope_q = "What was the closing price of bitcoin in November 2011?"
            await set_textarea("textarea", out_of_scope_q)
            await eval_js("document.querySelector('button[type=\"submit\"]').click()")

            await asyncio.sleep(2.0)
            abstention_rendered = await wait_for(
                "Array.from(document.querySelectorAll('strong')).some(s => s.innerText.includes('Insufficient Evidence'))",
                timeout=12.0
            )
            print(f" -> Honest abstention alert triggered: {bool(abstention_rendered)}")
            assert abstention_rendered, "Honest abstention banner was not rendered for out-of-scope question"

            # --- STEP 5: Test Animated Workflow Dialog (Project Creation) ---
            print("\n[TEST 5] Testing Workflow Execution Dialog on Project Creation...")
            await send("Page.navigate", {"url": f"{BASE_URL}/dashboard"})
            await asyncio.sleep(2.5)  # wait for React hydration
            await wait_for("document.querySelector('button') !== null")

            # Click "+ Create Project" button
            await eval_js("""
                (() => {
                    const btns = Array.from(document.querySelectorAll('button'));
                    const b = btns.find(btn => btn.innerText.includes('Create Project'));
                    if (b) b.click();
                })()
            """)

            await wait_for("document.querySelector('input[placeholder*=\"Mobile Core\"]') !== null")
            test_proj_name = f"Demo Platform {int(time.time()) % 10000}"
            await set_input('input[placeholder*="Mobile Core"]', test_proj_name)
            await set_textarea('textarea[placeholder*="Brief summary"]', "Automated E2E workflow verification project")

            # Click Create Project inside modal to trigger workflow execution dialog
            await eval_js("""
                (() => {
                    const modal = document.querySelector('div[role=\"dialog\"]');
                    const btn = Array.from(modal.querySelectorAll('button')).find(b => b.innerText.includes('Create Project'));
                    if (btn) btn.click();
                })()
            """)

            # Verify Workflow Execution Dialog appears
            dialog_appeared = await wait_for(
                "Array.from(document.querySelectorAll('h3, h2')).some(h => h.innerText.includes('Project Workspace Creation'))",
                timeout=6.0
            )
            print(f" -> Workflow Execution Dialog opened: {bool(dialog_appeared)}")
            assert dialog_appeared, "WorkflowExecutionDialog did not open on project creation"

            # Verify completion and result summary
            workflow_completed = await wait_for(
                "Array.from(document.querySelectorAll('button')).some(b => b.innerText === 'Done')",
                timeout=10.0
            )
            print(f" -> Workflow execution completed with 'Done' button: {bool(workflow_completed)}")
            assert workflow_completed, "Workflow execution did not reach complete state"

            # Dismiss workflow dialog
            await eval_js("""
                (() => {
                    const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText === 'Done');
                    if (btn) btn.click();
                })()
            """)
            print(" -> Clicked 'Done' and dismissed workflow dialog.")

            # --- STEP 6: Test Handoffs page ---
            print("\n[TEST 6] Verifying Handoffs Page & AI Handoff Generation...")
            await send("Page.navigate", {"url": f"{BASE_URL}/handoffs"})
            await asyncio.sleep(2.5)  # wait for React hydration
            handoffs_ready = await wait_for("document.querySelector('select') !== null", timeout=8.0)
            print(f" -> /handoffs loaded: {handoffs_ready}")
            assert handoffs_ready, "Failed to load /handoffs"

            # Ensure E-Commerce Platform is selected
            await eval_js("""
                (() => {
                    const sel = document.querySelector('select');
                    const opt = Array.from(sel.options).find(o => o.text.includes('E-Commerce'));
                    if (opt) {
                        sel.value = opt.value;
                        sel.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                })()
            """)
            await asyncio.sleep(1.0)

            # Open AI Generate Modal
            await eval_js("""
                (() => {
                    const btns = Array.from(document.querySelectorAll('button'));
                    const b = btns.find(btn => btn.innerText.includes('AI Handoff Generator'));
                    if (b) b.click();
                })()
            """)
            await wait_for("document.querySelector('div[role=\"dialog\"] form') !== null", timeout=5.0)

            # Submit generation
            await eval_js("""
                (() => {
                    const form = document.querySelector('div[role=\"dialog\"] form');
                    if (form) {
                        const submit = form.querySelector('button[type=\"submit\"]');
                        if (submit) submit.click();
                    }
                })()
            """)

            handoff_dialog = await wait_for(
                "Array.from(document.querySelectorAll('h3, h2')).some(h => h.innerText.includes('Operational Handoff Generation'))",
                timeout=6.0
            )
            print(f" -> Handoff Generation Workflow Dialog opened: {bool(handoff_dialog)}")
            assert handoff_dialog, "Handoff generation workflow dialog did not open"

            handoff_complete = await wait_for(
                "Array.from(document.querySelectorAll('button')).some(b => b.innerText === 'Done')",
                timeout=12.0
            )
            print(f" -> Handoff Generation completed with result summary: {bool(handoff_complete)}")
            assert handoff_complete, "Handoff generation workflow did not complete in time"

            # Dismiss
            await eval_js("""
                (() => {
                    const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText === 'Done');
                    if (btn) btn.click();
                })()
            """)

            # --- STEP 7: Test Knowledge Sources Ingestion Workflow ---
            print("\n[TEST 7] Verifying Source Ingestion Workflow on /sources...")
            await send("Page.navigate", {"url": f"{BASE_URL}/sources"})
            await asyncio.sleep(2.5)

            # Ensure E-Commerce Platform is selected
            await eval_js("""
                (() => {
                    const sel = document.querySelector('select');
                    const opt = Array.from(sel.options).find(o => o.text.includes('E-Commerce'));
                    if (opt) {
                        sel.value = opt.value;
                        sel.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                })()
            """)
            await asyncio.sleep(1.0)

            # Click "Ingest Document"
            await eval_js("""
                (() => {
                    const btns = Array.from(document.querySelectorAll('button'));
                    const b = btns.find(btn => btn.innerText.includes('Ingest Document'));
                    if (b) b.click();
                })()
            """)
            await wait_for("document.querySelector('input[placeholder*=\"Checkout Service\"]') !== null")
            await set_input('input[placeholder*="Checkout Service"]', f"Redis Cluster Topology Runbook {int(time.time()) % 1000}")
            await set_textarea('textarea[placeholder*="Paste operational"]', "# Redis Sharding Runbook\n\nEnsure maxmemory-policy is set to allkeys-lru.")

            # Submit
            await eval_js("""
                (() => {
                    const form = document.querySelector('div[role=\"dialog\"] form');
                    if (form) form.querySelector('button[type=\"submit\"]').click();
                })()
            """)

            ingest_dialog = await wait_for(
                "Array.from(document.querySelectorAll('h3, h2')).some(h => h.innerText.includes('Knowledge Source Ingestion'))",
                timeout=6.0
            )
            print(f" -> Source Ingestion Workflow Dialog opened: {bool(ingest_dialog)}")
            assert ingest_dialog, "Source Ingestion workflow dialog did not open"

            ingest_complete = await wait_for(
                "Array.from(document.querySelectorAll('button')).some(b => b.innerText === 'Done')",
                timeout=10.0
            )
            print(f" -> Source Ingestion completed successfully: {bool(ingest_complete)}")
            assert ingest_complete, "Source Ingestion workflow did not complete in time"

            await eval_js("""
                (() => {
                    const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText === 'Done');
                    if (btn) btn.click();
                })()
            """)

            # --- STEP 8: Test Integrations Sync Workflow ---
            print("\n[TEST 8] Verifying Simulated Integration Sync on /integrations...")
            await send("Page.navigate", {"url": f"{BASE_URL}/integrations"})
            await asyncio.sleep(2.5)

            # Ensure E-Commerce Platform is selected
            await eval_js("""
                (() => {
                    const sel = document.querySelector('select');
                    const opt = Array.from(sel.options).find(o => o.text.includes('E-Commerce'));
                    if (opt) {
                        sel.value = opt.value;
                        sel.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                })()
            """)
            await asyncio.sleep(1.0)

            # Click Sync Jira Issues Now on Jira connector
            await eval_js("""
                (() => {
                    const btns = Array.from(document.querySelectorAll('button'));
                    const syncBtn = btns.find(b => b.innerText.includes('Sync Jira Issues Now'));
                    if (syncBtn) syncBtn.click();
                })()
            """)

            sync_dialog = await wait_for(
                "Array.from(document.querySelectorAll('h3, h2')).some(h => h.innerText.includes('Synchronization'))",
                timeout=6.0
            )
            print(f" -> Integration Sync Workflow Dialog opened: {bool(sync_dialog)}")
            assert sync_dialog, "Integration sync workflow dialog did not open"

            sync_complete = await wait_for(
                "Array.from(document.querySelectorAll('button')).some(b => b.innerText === 'Done')",
                timeout=10.0
            )
            print(f" -> Integration Sync completed with evidence summary: {bool(sync_complete)}")
            assert sync_complete, "Integration sync workflow did not complete in time"

            await eval_js("""
                (() => {
                    const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText === 'Done');
                    if (btn) btn.click();
                })()
            """)

            disp_task.cancel()
            print("\n=== ALL REAL BROWSER TESTS PASSED (8/8) ===")
            return True

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        exit(1)
