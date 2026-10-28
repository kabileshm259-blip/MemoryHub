#!/usr/bin/env python3
"""
MemoryHub — Synthetic Demo Profile & Workspace Seeder (Milestone 5.1)
Idempotently establishes the 3 official demonstration profiles within the
'E-Commerce Platform' workspace for academic and operational continuity reviews.

Profiles Created / Verified:
  1. Alice Lead Engineer  (alice@example.com)   -> Project Owner
  2. Charlie Core Dev     (charlie@example.com) -> Project Editor
  3. Bob Successor        (bob@example.com)     -> Project Viewer / Successor

Usage:
  python scripts/seed_demo_accounts.py [--url http://127.0.0.1:8000] [--password <demo_pass>]
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple


def request(
    base_url: str,
    path: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    token: Optional[str] = None,
) -> Tuple[int, Dict[str, Any]]:
    url = f"{base_url.rstrip('/')}{path}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body_bytes = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"detail": raw}
        return e.code, parsed
    except urllib.error.URLError as e:
        return 0, {"detail": f"Network error connecting to {url}: {e}"}


def main():
    parser = argparse.ArgumentParser(description="MemoryHub Demo Profiles Seeder")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="FastAPI Base URL")
    parser.add_argument("--password", default="DemoPassword2026!", help="Default demo password for synthetic profiles")
    args = parser.parse_args()

    base_url = args.url
    password = args.password

    print("=" * 70)
    print("MemoryHub Milestone 5.1 — Synthetic Demo Workspace & Profiles Seeder")
    print(f"Target API Endpoint: {base_url}")
    print("=" * 70)

    # 1. Verify API Health
    status_code, health = request(base_url, "/health/readiness")
    if status_code != 200:
        print(f"[!] Warning: Readiness endpoint returned {status_code}: {health}")
        print("[!] Ensuring liveness endpoint...")
        s_live, live = request(base_url, "/health")
        if s_live != 200:
            print(f"[ERROR] MemoryHub backend is unreachable at {base_url}. Aborting.")
            sys.exit(1)
    print(f"[+] Backend Service Active: {health.get('service', 'memoryhub-api')} (status: {health.get('status', 'ok')})")

    profiles = [
        {"name": "Alice Lead Engineer", "email": "alice@example.com", "role": "owner"},
        {"name": "Charlie Core Dev", "email": "charlie@example.com", "role": "editor"},
        {"name": "Bob Successor", "email": "bob@example.com", "role": "viewer"},
    ]

    tokens = {}
    user_ids = {}

    print("\n--- 1. Establishing Synthetic Demo User Profiles ---")
    for p in profiles:
        email = p["email"]
        name = p["name"]

        # Try registering user
        s_reg, res_reg = request(base_url, "/api/auth/register", method="POST", data={
            "email": email,
            "display_name": name,
            "password": password,
        })

        if s_reg == 201:
            print(f"  [+] Created account: {name} ({email})")
            user_ids[email] = res_reg["id"]
        elif s_reg == 409:
            print(f"  [*] Account already exists (idempotent reuse): {name} ({email})")
        else:
            print(f"  [!] Registration notice ({s_reg}): {res_reg.get('detail')}")

        # Authenticate user to obtain token
        s_login, res_login = request(base_url, "/api/auth/login", method="POST", data={
            "email": email,
            "password": password,
        })
        if s_login != 200 or "access_token" not in res_login:
            print(f"[ERROR] Failed to authenticate {email}: {res_login}")
            sys.exit(1)

        token = res_login["access_token"]
        tokens[email] = token

        # Verify profile via /me
        s_me, me = request(base_url, "/api/auth/me", token=token)
        if s_me == 200:
            user_ids[email] = me["id"]
            print(f"      Verified Login -> Token Active | UUID: {me['id']}")
        else:
            print(f"[ERROR] Failed to fetch /me for {email}: {me}")
            sys.exit(1)

    alice_token = tokens["alice@example.com"]
    bob_id = user_ids["bob@example.com"]

    print("\n--- 2. Establishing 'E-Commerce Platform' Workspace ---")
    # List Alice's projects to see if project exists
    s_projs, projs_data = request(base_url, "/api/projects", token=alice_token)
    items = projs_data.get("items", []) if s_projs == 200 else []

    target_name = "E-Commerce Platform"
    project = next((proj for proj in items if proj.get("name") == target_name or "E-Commerce" in proj.get("name", "")), None)

    if project:
        project_id = project["id"]
        print(f"  [*] Existing workspace reused: '{project['name']}' [ID: {project_id}]")
    else:
        s_p, new_proj = request(base_url, "/api/projects", method="POST", data={
            "name": target_name,
            "description": "High-throughput checkout platform, Redis session cache, payment idempotency, and disaster runbook handover.",
        }, token=alice_token)
        if s_p != 201:
            print(f"[ERROR] Failed to create project: {new_proj}")
            sys.exit(1)
        project_id = new_proj["id"]
        print(f"  [+] Created new workspace: '{new_proj['name']}' [ID: {project_id}]")

    print("\n--- 3. Configuring RBAC Memberships ---")
    s_mems, mems_data = request(base_url, f"/api/projects/{project_id}/members", token=alice_token)
    existing_members = {m.get("email"): m for m in mems_data} if s_mems == 200 else {}

    # Invite Charlie as editor
    if "charlie@example.com" not in existing_members:
        s_mc, res_mc = request(base_url, f"/api/projects/{project_id}/members", method="POST", data={
            "email": "charlie@example.com",
            "role": "editor",
        }, token=alice_token)
        if s_mc == 201:
            print(f"  [+] Member assigned: Charlie Core Dev -> role 'editor'")
        else:
            print(f"  [*] Charlie member assignment: {res_mc.get('detail')}")
    else:
        print(f"  [*] Member already present: Charlie Core Dev (role: {existing_members['charlie@example.com'].get('role')})")

    # Invite Bob as viewer (successor)
    if "bob@example.com" not in existing_members:
        s_mb, res_mb = request(base_url, f"/api/projects/{project_id}/members", method="POST", data={
            "email": "bob@example.com",
            "role": "viewer",
        }, token=alice_token)
        if s_mb == 201:
            print(f"  [+] Member assigned: Bob Successor -> role 'viewer'")
        else:
            print(f"  [*] Bob member assignment: {res_mb.get('detail')}")
    else:
        print(f"  [*] Member already present: Bob Successor (role: {existing_members['bob@example.com'].get('role')})")

    print("\n--- 4. Seeding Knowledge Sources (Idempotent) ---")
    s_seed, seed_res = request(base_url, f"/api/projects/{project_id}/integrations/seed-demo", method="POST", token=alice_token)
    if s_seed in (200, 201):
        print(f"  [+] Ingested synthetic records: {seed_res.get('records_ingested', 5)}")
        print(f"  [+] Simulated Provider Sources: {seed_res.get('providers_simulated', ['jira', 'slack', 'file_upload'])}")
    else:
        print(f"  [*] Seed notice ({s_seed}): {seed_res.get('detail')}")

    print("\n--- 5. Preparing Baseline Operational Handoff ---")
    s_hlist, hlist = request(base_url, f"/api/projects/{project_id}/handoffs", token=alice_token)
    handoffs = hlist.get("items", []) if s_hlist == 200 else []

    handoff = None
    if handoffs:
        handoff = handoffs[0]
        print(f"  [*] Reusing existing handoff: '{handoff['title']}' (Status: {handoff['status']})")
    else:
        # Generate initial draft via RAG service
        s_gen, gen_res = request(base_url, f"/api/projects/{project_id}/handoffs/generate", method="POST", data={
            "title": "Checkout Service Modernization & Payment Gateway Handover",
            "successor_id": bob_id,
            "target_completion_date": "2026-11-15",
            "focus_areas": ["Payment Gateway", "Redis Cluster", "PostgreSQL Deadlocks"],
        }, token=alice_token)
        if s_gen in (200, 201):
            handoff = gen_res["handoff"]
            print(f"  [+] Generated initial structured handoff: '{handoff['title']}'")
            print(f"      Readiness Score: {handoff['summary']['readiness_score']['score']}%")
            print(f"      Tasks Extracted: {len(handoff['summary']['tasks'])}")
            print(f"      Risks Extracted: {len(handoff['summary']['risks'])}")
        else:
            print(f"[!] Handoff generation notice ({s_gen}): {gen_res}")

    print("\n--- 6. Verifying Cross-Role Demonstration Capabilities ---")
    # Verify Bob (Successor/Viewer) can execute RAG Q&A
    bob_token = tokens["bob@example.com"]
    s_ask, ask_res = request(base_url, f"/api/projects/{project_id}/ask", method="POST", data={
        "question": "What is the max client connections setting for PostgreSQL under checkout flash sales?",
        "top_k": 3,
    }, token=bob_token)
    if s_ask == 200:
        print(f"  [+] Bob (Viewer/Successor) Vector RAG Query Successful:")
        print(f"      Provider Mode: {ask_res.get('provider_mode', 'heuristic')}")
        print(f"      Answer: {ask_res['answer'][:110]}...")
        print(f"      Verified Citations: {len(ask_res['citations'])} source citations")
    else:
        print(f"  [!] RAG Query notice ({s_ask}): {ask_res}")

    # Verify Charlie (Editor) can post a comment
    charlie_token = tokens["charlie@example.com"]
    if handoff:
        s_comm, comm_res = request(base_url, f"/api/projects/{project_id}/handoffs/{handoff['id']}/comments", method="POST", data={
            "content": "Verified the Redis session eviction patch in staging. Ready for production cutover.",
            "comment_type": "comment",
        }, token=charlie_token)
        if s_comm in (200, 201):
            print(f"  [+] Charlie (Editor) Review Comment Posted: '{comm_res['content'][:60]}...'")

    print("\n" + "=" * 70)
    print("SUCCESS: DEMO PROFILES AND WORKSPACE READY FOR DEMONSTRATION")
    print("=" * 70)
    print(f"{'Role':<12} | {'Display Name':<22} | {'Email':<22} | {'Password'}")
    print("-" * 70)
    print(f"{'Owner':<12} | {'Alice Lead Engineer':<22} | {'alice@example.com':<22} | {password}")
    print(f"{'Editor':<12} | {'Charlie Core Dev':<22} | {'charlie@example.com':<22} | {password}")
    print(f"{'Viewer':<12} | {'Bob Successor':<22} | {'bob@example.com':<22} | {password}")
    print("=" * 70)
    print("Workspace Name: E-Commerce Platform")
    print(f"Workspace UUID: {project_id}")
    print("=" * 70)


if __name__ == "__main__":
    main()

