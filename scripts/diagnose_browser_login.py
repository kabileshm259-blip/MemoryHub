#!/usr/bin/env python3
"""
CDP Diagnostic Script to capture exact browser network & console events during login.
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


async def diagnose_login():
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
            network_events = []
            console_events = []

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

            # Background message dispatcher
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
                            continue

                        method = data.get("method", "")
                        params = data.get("params", {})

                        if method == "Network.requestWillBeSent":
                            req = params.get("request", {})
                            network_events.append({
                                "event": "requestWillBeSent",
                                "requestId": params.get("requestId"),
                                "url": req.get("url"),
                                "method": req.get("method"),
                                "headers": req.get("headers"),
                            })
                        elif method == "Network.responseReceived":
                            resp = params.get("response", {})
                            network_events.append({
                                "event": "responseReceived",
                                "requestId": params.get("requestId"),
                                "url": resp.get("url"),
                                "status": resp.get("status"),
                                "statusText": resp.get("statusText"),
                                "headers": resp.get("headers"),
                            })
                        elif method == "Network.loadingFailed":
                            network_events.append({
                                "event": "loadingFailed",
                                "requestId": params.get("requestId"),
                                "errorText": params.get("errorText"),
                                "canceled": params.get("canceled"),
                                "blockedReason": params.get("blockedReason"),
                                "corsErrorStatus": params.get("corsErrorStatus"),
                            })
                        elif method in ("Console.messageAdded", "Runtime.consoleAPICalled"):
                            console_events.append({
                                "event": method,
                                "params": params,
                            })
                        elif method == "Runtime.exceptionThrown":
                            console_events.append({
                                "event": "exceptionThrown",
                                "details": params.get("exceptionDetails"),
                            })
                except asyncio.CancelledError:
                    pass

            disp_task = asyncio.create_task(dispatcher())

            await send("Page.enable")
            await send("Runtime.enable")
            await send("DOM.enable")
            await send("Network.enable")
            await send("Console.enable")

            # Navigate to /login
            print("[1] Navigating to http://localhost:3000/login ...")
            await send("Page.navigate", {"url": f"{BASE_URL}/login"})
            await asyncio.sleep(2.0)

            # Fill inputs
            print("[2] Filling credentials (alice@example.com) ...")
            js_fill = """
            (() => {
                const emailEl = document.querySelector('input[type="email"]');
                const passEl = document.querySelector('input[type="password"]');
                
                const setVal = (el, val) => {
                    const desc = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');
                    if (desc && desc.set) {
                        desc.set.call(el, val);
                    } else {
                        el.value = val;
                    }
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                };
                
                setVal(emailEl, 'alice@example.com');
                setVal(passEl, 'DemoPassword2026!');
                return true;
            })()
            """
            await send("Runtime.evaluate", {"expression": js_fill, "returnByValue": True})
            await asyncio.sleep(0.5)

            # Click Submit
            print("[3] Clicking Sign In button ...")
            js_click = """
            (() => {
                const btn = document.querySelector('button[type="submit"]');
                if (btn) {
                    btn.click();
                    return true;
                }
                return false;
            })()
            """
            await send("Runtime.evaluate", {"expression": js_click, "returnByValue": True})
            
            # Wait for response and React re-render
            print("[4] Waiting 4.0 seconds for network and UI resolution ...")
            await asyncio.sleep(4.0)

            # Capture DOM text and current URL
            dom_res = await send("Runtime.evaluate", {
                "expression": "document.body ? document.body.innerText : ''",
                "returnByValue": True,
            })
            url_res = await send("Runtime.evaluate", {
                "expression": "window.location.href",
                "returnByValue": True,
            })

            disp_task.cancel()

            print("\n" + "=" * 70)
            print("REAL BROWSER DIAGNOSTIC REPORT")
            print("=" * 70)
            print(f"Final URL: {url_res.get('result', {}).get('value')}")
            print("\n--- DOM Text Snapshot ---")
            safe_dom = dom_res.get("result", {}).get("value", "")[:500].encode("ascii", errors="replace").decode("ascii")
            print(safe_dom)

            print("\n--- Network Events ---")
            for ev in network_events:
                ev_type = ev["event"]
                if ev_type == "requestWillBeSent":
                    if "api" in ev["url"] or "8000" in ev["url"]:
                        print(f"--> REQUEST: {ev['method']} {ev['url']}")
                        print(f"    Headers: {json.dumps(ev.get('headers', {}))}")
                elif ev_type == "responseReceived":
                    if "api" in ev["url"] or "8000" in ev["url"]:
                        headers = ev.get("headers", {})
                        cors_origin = headers.get("access-control-allow-origin") or headers.get("Access-Control-Allow-Origin")
                        cors_cred = headers.get("access-control-allow-credentials") or headers.get("Access-Control-Allow-Credentials")
                        print(f"<-- RESPONSE: {ev['status']} {ev['statusText']} for {ev['url']}")
                        print(f"    CORS Origin: {cors_origin} | Credentials: {cors_cred}")
                elif ev_type == "loadingFailed":
                    print(f"<-- FAILED: {ev['errorText']} | Canceled: {ev['canceled']} | Blocked: {ev['blockedReason']} | CORS: {ev['corsErrorStatus']}")

            print("\n--- Console Events & Exceptions ---")
            for ev in console_events:
                print(f"CONSOLE: {json.dumps(ev)}")
            print("=" * 70)

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    asyncio.run(diagnose_login())
