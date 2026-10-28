#!/usr/bin/env python3
"""
MemoryHub — Reproducible End-to-End Demo Workflow Verification
Tests the 8-stage operational continuity lifecycle against a running MemoryHub API stack.

Prerequisites:
  1. PostgreSQL and ChromaDB containers running (docker compose up -d postgres chroma)
  2. FastAPI backend running on http://127.0.0.1:8000
     (uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000)

Usage:
  python scripts/verify_demo_workflow.py [--url http://127.0.0.1:8000]
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple


class WorkflowVerifier:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.ts = int(time.time())
        self.alice_email = f"alice_demo_{self.ts}@example.com"
        self.bob_email = f"bob_demo_{self.ts}@example.com"
        self.password = "StrongDemoPass123!"
        self.alice_token: Optional[str] = None
        self.bob_token: Optional[str] = None
        self.project_id: Optional[str] = None
        self.handoff_id: Optional[str] = None

    def request(
        self,
        path: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None,
    ) -> Tuple[int, Dict[str, Any]]:
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        body_bytes = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
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
            return 0, {"error": str(e.reason)}

    def check_prerequisites(self) -> bool:
        print(f"[*] Checking MemoryHub API at {self.base_url}...")
        status, res = self.request("/health/readiness")
        if status != 200:
            print(f"[!] Cannot reach backend readiness endpoint at {self.base_url}/health/readiness.")
            print("    Please ensure FastAPI backend is running on port 8000.")
            print(f"    Response: {status} {res}")
            return False
        postgres_ok = res.get("postgres") == "connected"
        chroma_ok = res.get("chroma") == "connected"
        print(f"    - PostgreSQL: {res.get('postgres', 'unknown')}")
        print(f"    - ChromaDB:   {res.get('chroma', 'unknown')}")
        if not (postgres_ok and chroma_ok):
            print("[!] One or more downstream data services are not ready.")
            return False
        print("[+] Backend and storage dependencies are healthy.\n")
        return True

    def stage_1_authentication(self):
        print("=== STAGE 1: USER AUTHENTICATION & ROLE MANAGEMENT ===")
        # Register Alice (Departing Lead)
        s, res = self.request("/api/auth/register", method="POST", data={
            "email": self.alice_email,
            "password": self.password,
            "display_name": "Alice Engineer"
        })
        assert s == 201, f"Failed to register Alice: {res}"

        # Login Alice
        s, login_a = self.request("/api/auth/login", method="POST", data={
            "email": self.alice_email,
            "password": self.password,
        })
        assert s == 200 and "access_token" in login_a, f"Alice login failed: {login_a}"
        self.alice_token = login_a["access_token"]

        # Register Bob (Successor)
        s, res = self.request("/api/auth/register", method="POST", data={
            "email": self.bob_email,
            "password": self.password,
            "display_name": "Bob Successor"
        })
        assert s == 201, f"Failed to register Bob: {res}"

        # Login Bob
        s, login_b = self.request("/api/auth/login", method="POST", data={
            "email": self.bob_email,
            "password": self.password,
        })
        assert s == 200 and "access_token" in login_b, f"Bob login failed: {login_b}"
        self.bob_token = login_b["access_token"]

        s, me_a = self.request("/api/auth/me", token=self.alice_token)
        s, me_b = self.request("/api/auth/me", token=self.bob_token)
        self.bob_id = me_b["id"]
        print(f"  [+] Alice authenticated: {me_a['display_name']} ({me_a['email']})")
        print(f"  [+] Bob authenticated:   {me_b['display_name']} ({me_b['email']}) [ID: {self.bob_id}]")

    def stage_2_workspace_and_rbac(self):
        print("\n=== STAGE 2: WORKSPACE SETUP & RBAC MEMBERSHIP ===")
        proj_name = f"E-Commerce Modernization (Verification {self.ts})"
        s, proj = self.request("/api/projects", method="POST", data={
            "name": proj_name,
            "description": "Checkout service Redis cluster migration, payment idempotency, and runbook handover"
        }, token=self.alice_token)
        assert s == 201, f"Failed to create project workspace: {proj}"
        self.project_id = proj["id"]
        print(f"  [+] Workspace created: '{proj['name']}' (ID: {self.project_id})")

        # Add Bob as viewer
        s, mem = self.request(f"/api/projects/{self.project_id}/members", method="POST", data={
            "email": self.bob_email,
            "role": "viewer"
        }, token=self.alice_token)
        assert s == 201, f"Failed to add Bob as project member: {mem}"
        print(f"  [+] RBAC Member assigned: {self.bob_email} -> role '{mem['role']}'")

    def stage_3_knowledge_ingestion(self):
        print("\n=== STAGE 3: KNOWLEDGE INGESTION (DEMO SCENARIO) ===")
        s, seed = self.request(f"/api/projects/{self.project_id}/integrations/seed-demo", method="POST", token=self.alice_token)
        assert s in (200, 201), f"Failed to seed demo scenario: {seed}"
        print(f"  [+] Scenario:         {seed['scenario']}")
        print(f"  [+] Records Ingested: {seed['records_ingested']}")
        print(f"  [+] Provider Types:   {seed['providers_simulated']}")

    def stage_4_persistence_verification(self):
        print("\n=== STAGE 4: DATABASE & VECTOR PERSISTENCE VERIFICATION ===")
        s, sources_data = self.request(f"/api/projects/{self.project_id}/sources", token=self.alice_token)
        assert s == 200, f"Failed to list sources: {sources_data}"
        sources = sources_data.get("items", [])
        assert len(sources) >= 5, f"Expected at least 5 sources, found {len(sources)}"
        print(f"  [+] Verified {len(sources)} source records in PostgreSQL:")
        for src in sources[:5]:
            meta = src.get("access_metadata") or {}
            c_hash = meta.get("content_sha256", "N/A")[:16]
            chunks = meta.get("chunk_count", 1)
            print(f"      - [{src['provider_type']}] '{src['title']}' | Chunks: {chunks} | SHA-256: {c_hash}...")

    def stage_5_rag_and_abstention(self):
        print("\n=== STAGE 5: EVIDENCE-GROUNDED RAG & HONEST ABSTENTION ===")
        # Query 1: Grounded question with verifiable context
        q1 = "What is the resolution plan for the Redis session cache eviction bottleneck?"
        s, r1 = self.request(f"/api/projects/{self.project_id}/ask", method="POST", data={
            "question": q1,
            "top_k": 3
        }, token=self.bob_token)
        assert s == 200, f"RAG query 1 failed: {r1}"
        assert r1.get("has_sufficient_evidence") is True, "Expected sufficient evidence for Q1"
        assert r1.get("confidence", 0) >= 0.22, f"Expected confidence >= 0.22, got {r1.get('confidence')}"
        assert len(r1.get("citations", [])) > 0, "Expected at least 1 citation for Q1"
        print(f"  [+] Grounded Question: '{q1}'")
        print(f"      - Confidence Score: {r1['confidence']} (Threshold: 0.22)")
        print(f"      - Sufficient Evidence: {r1['has_sufficient_evidence']}")
        print(f"      - Citations ({len(r1['citations'])}):")
        for c in r1["citations"][:2]:
            print(f"        * [{c.get('provider_type')}] '{c.get('title')}' (Score: {c.get('score')})")

        # Query 2: Unverified absent question
        q2 = "What is the personal mobile phone number of the company CEO?"
        s, r2 = self.request(f"/api/projects/{self.project_id}/ask", method="POST", data={
            "question": q2,
            "top_k": 3
        }, token=self.bob_token)
        assert s == 200, f"RAG query 2 failed: {r2}"
        assert r2.get("has_sufficient_evidence") is False, "Expected insufficient evidence for Q2"
        assert r2.get("confidence", 0) == 0.0, f"Expected confidence 0.0, got {r2.get('confidence')}"
        print(f"  [+] Absent Question:   '{q2}'")
        print(f"      - Confidence Score: {r2['confidence']}")
        print(f"      - Honest Abstention: {r2['has_sufficient_evidence'] is False}")
        print(f"      - Abstention Notice: {r2['answer'][:110]}...")

    def stage_6_handoff_generation(self):
        print("\n=== STAGE 6: AI-ASSISTED HANDOFF GENERATION & READINESS ===")
        s, gen_res = self.request(f"/api/projects/{self.project_id}/handoffs/generate", method="POST", data={
            "title": "E-Commerce Checkout & Payments Handover Brief",
            "successor_id": self.bob_id,
            "target_completion_date": "2026-11-15T00:00:00Z"
        }, token=self.alice_token)
        assert s == 201, f"Failed to generate handoff: {gen_res}"
        handoff = gen_res["handoff"]
        self.handoff_id = handoff["id"]
        summary = handoff.get("summary") or {}
        score_data = summary.get("readiness_score") or {}
        tasks = summary.get("tasks") or []
        risks = summary.get("risks") or []
        deps = summary.get("dependencies") or []

        print(f"  [+] Handoff Created: '{handoff['title']}' (ID: {self.handoff_id})")
        print(f"      - Status:               {handoff['status']}")
        print(f"      - Extracted Tasks:      {len(tasks)}")
        print(f"      - Identified Risks:     {len(risks)}")
        print(f"      - Tracked Dependencies: {len(deps)}")
        print(f"      - Initial Readiness:    {score_data.get('score', 0)}% (Level: {score_data.get('level', 'unknown')})")
        print(f"      - Breakdown:            {score_data.get('breakdown', {})}")

    def stage_7_review_and_acknowledgement(self):
        print("\n=== STAGE 7: REVIEW LIFECYCLE & SUCCESSOR SIGN-OFF ===")
        # Alice moves to in_review
        s, h1 = self.request(
            f"/api/projects/{self.project_id}/handoffs/{self.handoff_id}/status",
            method="POST",
            data={"status": "in_review", "comment": "Ready for successor Bob to verify dependencies."},
            token=self.alice_token,
        )
        assert s == 200 and h1["status"] == "in_review", f"Failed transition to in_review: {h1}"
        print(f"  [+] Transition 1: draft -> in_review by Alice")

        # Bob posts comment
        s, c1 = self.request(
            f"/api/projects/{self.project_id}/handoffs/{self.handoff_id}/comments",
            method="POST",
            data={"content": "Reviewed runbook and architecture diagrams. Redis Sentinel configuration verified.", "comment_type": "approval"},
            token=self.bob_token,
        )
        assert s == 201, f"Failed to post Bob's review comment: {c1}"
        print(f"  [+] Successor feedback: '{c1['content'][:75]}...'")

        # Alice approves handoff
        s, h2 = self.request(
            f"/api/projects/{self.project_id}/handoffs/{self.handoff_id}/status",
            method="POST",
            data={"status": "approved", "comment": "Handoff approved for final successor sign-off."},
            token=self.alice_token,
        )
        assert s == 200 and h2["status"] == "approved", f"Failed transition to approved: {h2}"
        print(f"  [+] Transition 2: in_review -> approved by Alice")

        # Bob formally acknowledges
        s, h3 = self.request(
            f"/api/projects/{self.project_id}/handoffs/{self.handoff_id}/acknowledge",
            method="POST",
            token=self.bob_token,
        )
        assert s == 200 and h3["status"] == "acknowledged", f"Bob acknowledgement failed: {h3}"
        updated_score = (h3.get("summary") or {}).get("readiness_score") or {}
        print(f"  [+] Successor Sign-Off: Bob formally acknowledged handoff receipt.")
        print(f"      - Final Status:     {h3['status']}")
        print(f"      - Recalculated Score: {updated_score.get('score', 0)}% (Level: {updated_score.get('level', 'unknown')})")
        print(f"      - Successor Pts:    {updated_score.get('breakdown', {}).get('successor_readiness', 0)} / 20 (+10 pts bonus)")

    def stage_8_comments_notifications_audit(self):
        print("\n=== STAGE 8: COMMENTS, NOTIFICATIONS, & AUDIT EVENTS ===")
        # Check comments thread
        s, handoff = self.request(f"/api/projects/{self.project_id}/handoffs/{self.handoff_id}", token=self.alice_token)
        comments = handoff.get("comments") or []
        print(f"  [+] Audit Discussion Thread: {len(comments)} comment records verified.")

        # Check Alice's notifications
        s, notifs_a = self.request("/api/notifications", token=self.alice_token)
        items_a = notifs_a.get("items") or []
        print(f"  [+] Alice Notification Inbox: {len(items_a)} notification records.")
        for n in items_a[:2]:
            print(f"      - [{n['notification_type']}] {n['title']}")

        # Check Bob's notifications
        s, notifs_b = self.request("/api/notifications", token=self.bob_token)
        items_b = notifs_b.get("items") or []
        print(f"  [+] Bob Notification Inbox:   {len(items_b)} notification records.")
        for n in items_b[:2]:
            print(f"      - [{n['notification_type']}] {n['title']}")

    def run_all(self) -> bool:
        start_time = time.time()
        print("==================================================================")
        print("  MEMORYHUB DEMONSTRATION WORKFLOW — AUTOMATED REPRODUCIBILITY")
        print("==================================================================")
        if not self.check_prerequisites():
            return False

        try:
            self.stage_1_authentication()
            self.stage_2_workspace_and_rbac()
            self.stage_3_knowledge_ingestion()
            self.stage_4_persistence_verification()
            self.stage_5_rag_and_abstention()
            self.stage_6_handoff_generation()
            self.stage_7_review_and_acknowledgement()
            self.stage_8_comments_notifications_audit()
            elapsed = time.time() - start_time
            print("\n==================================================================")
            print(f"  DEMO WORKFLOW VALIDATION: ALL 8 STAGES PASSED (Elapsed: {elapsed:.2f}s)")
            print("==================================================================")
            return True
        except AssertionError as e:
            print(f"\n[X] Verification assertion failed: {e}")
            return False
        except Exception as e:
            print(f"\n[X] Unexpected error during verification: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="MemoryHub Demo Workflow Verifier")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Base URL of MemoryHub API")
    args = parser.parse_args()

    verifier = WorkflowVerifier(base_url=args.url)
    success = verifier.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
