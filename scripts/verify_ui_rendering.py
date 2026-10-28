#!/usr/bin/env python3
"""
MemoryHub — Browser UI Rendering and Route Guard Verification
Uses headless Chrome to load and verify frontend Next.js pages:
  1. Public Auth Pages (/login, /register): verifies form elements and branding.
  2. Protected App Pages (/dashboard, /projects, /handoffs, /sources, /integrations):
     verifies that client-side ProtectedRoute correctly guards against unauthenticated access.
"""

import subprocess
import sys

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://localhost:3000"

PUBLIC_PAGES = [
    ("/login", "Sign In Page", ["MemoryHub", "Sign in", "Email Address", "Password"]),
    ("/register", "Registration Page", ["MemoryHub", "Create your MemoryHub account", "Full name", "Email address", "Password"]),
]

PROTECTED_PAGES = [
    ("/dashboard", "Dashboard Route"),
    ("/projects", "Projects Directory Route"),
    ("/handoffs", "Operational Handoffs Route"),
    ("/sources", "Knowledge Sources Route"),
    ("/integrations", "Integrations Hub Route"),
]


def check_public_page(path: str, label: str, expected_texts: list) -> bool:
    url = f"{BASE_URL}{path}"
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--dump-dom",
        url,
    ]
    try:
        raw = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=12)
        html = raw.decode("utf-8", errors="ignore")
        dom_size = len(html)
        if dom_size < 1000:
            print(f"  [X] {path:16} -> Empty or invalid DOM (size: {dom_size} bytes)")
            return False

        found = [t for t in expected_texts if t.lower() in html.lower()]
        missing = [t for t in expected_texts if t.lower() not in html.lower()]

        if missing:
            print(f"  [!] {path:16} -> Rendered {dom_size} bytes, missing keywords: {missing}")
            return False

        print(f"  [+] {path:16} -> Rendered {dom_size:5} bytes | Verified elements: {found}")
        return True
    except Exception as e:
        print(f"  [X] {path:16} -> Error: {e}")
        return False


def check_protected_page(path: str, label: str) -> bool:
    url = f"{BASE_URL}{path}"
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--dump-dom",
        url,
    ]
    try:
        raw = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=12)
        html = raw.decode("utf-8", errors="ignore")
        dom_size = len(html)

        # ProtectedRoute should render session verification or redirect to /login
        has_auth_guard = (
            "Verifying authentication session" in html
            or "/login" in html
            or "Sign in" in html
        )

        if not has_auth_guard or dom_size < 1000:
            print(f"  [X] {path:16} -> Protected route guard missing or failed (size: {dom_size})")
            return False

        print(f"  [+] {path:16} -> Rendered {dom_size:5} bytes | Enforced ProtectedRoute guard (Session check/Redirect)")
        return True
    except Exception as e:
        print(f"  [X] {path:16} -> Error: {e}")
        return False


def main():
    print("==================================================================")
    print("  MEMORYHUB BROWSER UI VERIFICATION (Headless Chrome)")
    print(f"  Target: {BASE_URL}")
    print("==================================================================")

    all_passed = True
    print("\n[PART 1: PUBLIC AUTHENTICATION ROUTES]")
    for path, label, keywords in PUBLIC_PAGES:
        if not check_public_page(path, label, keywords):
            all_passed = False

    print("\n[PART 2: PROTECTED ROUTES & CLIENT-SIDE AUTH GUARDS]")
    for path, label in PROTECTED_PAGES:
        if not check_protected_page(path, label):
            all_passed = False

    print("\n==================================================================")
    if all_passed:
        print("  ALL 7 FRONTEND ROUTES SUCCESSFULLY HYDRATED & VERIFIED IN CHROME")
        print("==================================================================")
        sys.exit(0)
    else:
        print("  SOME PAGES FAILED BROWSER VERIFICATION")
        print("==================================================================")
        sys.exit(1)


if __name__ == "__main__":
    main()
