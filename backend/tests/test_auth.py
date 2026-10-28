from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import User
from app.security import create_access_token, verify_password


def test_registration_succeeds_with_valid_data(client: TestClient, db_session: Session):
    """1. Registration succeeds with valid data."""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "Alice.Smith@Example.COM",
            "password": "ValidPassword123!",
            "display_name": "Alice Smith",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    # Verify email is normalized
    assert data["email"] == "alice.smith@example.com"
    assert data["display_name"] == "Alice Smith"
    # Ensure sensitive hashes or passwords are not exposed
    assert "password" not in data
    assert "password_hash" not in data


def test_duplicate_registration_is_rejected(client: TestClient):
    """2. Duplicate registration is rejected."""
    payload = {
        "email": "duplicate@example.com",
        "password": "Password123!",
        "display_name": "Original User",
    }
    first_res = client.post("/api/auth/register", json=payload)
    assert first_res.status_code == 201

    # Attempt to register with the same email (varying case and whitespace)
    duplicate_payload = {
        "email": "  DUPLICATE@example.com  ",
        "password": "AnotherPassword456!",
        "display_name": "Imposter User",
    }
    second_res = client.post("/api/auth/register", json=duplicate_payload)
    assert second_res.status_code == 409
    assert "already exists" in second_res.json()["detail"]


def test_passwords_are_stored_as_hashes(client: TestClient, db_session: Session):
    """3. Passwords are stored as hashes."""
    plaintext = "SecretP@ssw0rd99"
    email = "security_test@example.com"

    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": plaintext,
            "display_name": "Security Tester",
        },
    )
    assert response.status_code == 201

    # Query the user row directly from the database
    stmt = select(User).where(User.email == email)
    user = db_session.execute(stmt).scalar_one()

    # Password hash must not equal plaintext
    assert user.password_hash != plaintext
    # Bcrypt hashes start with $2b$ or $2a$
    assert user.password_hash.startswith(("$2b$", "$2a$"))
    # Verify password succeeds with correct plaintext and fails with incorrect
    assert verify_password(plaintext, user.password_hash) is True
    assert verify_password("wrongpassword", user.password_hash) is False


def test_login_succeeds_with_correct_credentials(client: TestClient):
    """4. Login succeeds with correct credentials."""
    email = "bob@example.com"
    password = "CorrectHorseBatteryStaple!"

    reg_res = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": "Bob",
        },
    )
    assert reg_res.status_code == 201

    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["expires_in"] > 0


def test_login_fails_with_incorrect_credentials(client: TestClient):
    """5. Login fails with incorrect credentials."""
    email = "carol@example.com"
    correct_password = "GoodPassword123!"

    reg_res = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": correct_password,
            "display_name": "Carol",
        },
    )
    assert reg_res.status_code == 201

    # Wrong password
    wrong_pw_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": "WrongPassword999!"},
    )
    assert wrong_pw_res.status_code == 401
    assert wrong_pw_res.json()["detail"] == "Invalid email or password"

    # Non-existent user email (must return identical generic error)
    unknown_email_res = client.post(
        "/api/auth/login",
        json={"email": "nonexistent@example.com", "password": "AnyPassword123!"},
    )
    assert unknown_email_res.status_code == 401
    assert unknown_email_res.json()["detail"] == "Invalid email or password"


def test_expired_or_invalid_tokens_are_rejected(client: TestClient):
    """6. Expired or invalid tokens are rejected."""
    # 1. Expired token
    expired_token = create_access_token(
        subject="00000000-0000-0000-0000-000000000001",
        expires_delta=timedelta(seconds=-60),
    )
    res_expired = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res_expired.status_code == 401
    assert res_expired.json()["detail"] == "Token has expired"

    # 2. Tampered token
    tampered_token = expired_token[:-4] + "abcd"
    res_tampered = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert res_tampered.status_code == 401
    assert res_tampered.json()["detail"] == "Could not validate credentials"

    # 3. Completely bogus token
    res_bogus = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert res_bogus.status_code == 401
    assert res_bogus.json()["detail"] == "Could not validate credentials"

    # 4. Missing Authorization header
    res_missing = client.get("/api/auth/me")
    assert res_missing.status_code == 401 or res_missing.status_code == 403


def test_get_me_success(client: TestClient, auth_helper):
    """Authenticated user can retrieve their own profile."""
    user, headers = auth_helper("david@example.com", "DavidPass123!", "David")

    res = client.get("/api/auth/me", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == user["id"]
    assert data["email"] == "david@example.com"
    assert data["display_name"] == "David"


def test_registration_validation_errors(client: TestClient):
    """Input validation rejects invalid email, short password, or blank display name."""
    # Invalid email
    res1 = client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": "ValidPass123!", "display_name": "Dan"},
    )
    assert res1.status_code == 422

    # Password too short (< 8 chars)
    res2 = client.post(
        "/api/auth/register",
        json={"email": "short@example.com", "password": "short", "display_name": "Dan"},
    )
    assert res2.status_code == 422

    # Empty display name
    res3 = client.post(
        "/api/auth/register",
        json={"email": "blankname@example.com", "password": "ValidPass123!", "display_name": "   "},
    )
    assert res3.status_code == 422
