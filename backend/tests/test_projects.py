import uuid
from fastapi.testclient import TestClient


def test_authenticated_users_can_create_and_list_their_own_projects(
    client: TestClient, auth_helper
):
    """7. Authenticated users can create and list their own projects."""
    user1, headers1 = auth_helper("owner1@example.com", "Password123!", "Owner One")
    user2, headers2 = auth_helper("owner2@example.com", "Password123!", "Owner Two")

    # User 1 creates two projects
    p1_res = client.post(
        "/api/projects",
        json={"name": "Project Alpha", "description": "First project"},
        headers=headers1,
    )
    assert p1_res.status_code == 201
    p1 = p1_res.json()
    assert p1["name"] == "Project Alpha"
    assert p1["role"] == "owner"

    p2_res = client.post(
        "/api/projects",
        json={"name": "Project Beta", "description": "Second project"},
        headers=headers1,
    )
    assert p2_res.status_code == 201
    p2 = p2_res.json()

    # User 2 creates one project
    p3_res = client.post(
        "/api/projects",
        json={"name": "Project Gamma", "description": "User 2 project"},
        headers=headers2,
    )
    assert p3_res.status_code == 201

    # User 1 lists projects: should only see Project Alpha and Beta
    list1 = client.get("/api/projects", headers=headers1)
    assert list1.status_code == 200
    items1 = list1.json()["items"]
    assert len(items1) == 2
    project_names1 = {item["name"] for item in items1}
    assert project_names1 == {"Project Alpha", "Project Beta"}
    for item in items1:
        assert item["role"] == "owner"

    # User 2 lists projects: should only see Project Gamma
    list2 = client.get("/api/projects", headers=headers2)
    assert list2.status_code == 200
    items2 = list2.json()["items"]
    assert len(items2) == 1
    assert items2[0]["name"] == "Project Gamma"


def test_project_owner_can_add_a_member(client: TestClient, auth_helper):
    """8. A project owner can add a member."""
    owner, owner_headers = auth_helper("project_boss@example.com", "Password123!", "Boss")
    editor_user, _ = auth_helper("editor_dev@example.com", "Password123!", "Editor")
    viewer_user, _ = auth_helper("viewer_auditor@example.com", "Password123!", "Viewer")

    # Create project
    proj_res = client.post(
        "/api/projects",
        json={"name": "Team Collab", "description": "Cross-role collaboration"},
        headers=owner_headers,
    )
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]

    # Owner adds editor
    add_editor_res = client.post(
        f"/api/projects/{proj_id}/members",
        json={"email": "editor_dev@example.com", "role": "editor"},
        headers=owner_headers,
    )
    assert add_editor_res.status_code == 201
    editor_member = add_editor_res.json()
    assert editor_member["role"] == "editor"
    assert editor_member["email"] == "editor_dev@example.com"

    # Owner adds viewer
    add_viewer_res = client.post(
        f"/api/projects/{proj_id}/members",
        json={"email": "viewer_auditor@example.com", "role": "viewer"},
        headers=owner_headers,
    )
    assert add_viewer_res.status_code == 201
    viewer_member = add_viewer_res.json()
    assert viewer_member["role"] == "viewer"

    # List members
    members_res = client.get(f"/api/projects/{proj_id}/members", headers=owner_headers)
    assert members_res.status_code == 200
    members = members_res.json()
    assert len(members) == 3
    roles = {m["email"]: m["role"] for m in members}
    assert roles["project_boss@example.com"] == "owner"
    assert roles["editor_dev@example.com"] == "editor"
    assert roles["viewer_auditor@example.com"] == "viewer"


def test_non_owner_cannot_add_members_or_change_project_settings(
    client: TestClient, auth_helper
):
    """9. A non-owner cannot add members or change project settings."""
    _, owner_headers = auth_helper("lead@example.com", "Password123!", "Lead")
    _, editor_headers = auth_helper("editor1@example.com", "Password123!", "Editor")
    _, bystander_headers = auth_helper("bystander@example.com", "Password123!", "Bystander")

    # Create project
    proj_res = client.post(
        "/api/projects",
        json={"name": "Strict Project", "description": "Restricted"},
        headers=owner_headers,
    )
    proj_id = proj_res.json()["id"]

    # Owner adds editor
    client.post(
        f"/api/projects/{proj_id}/members",
        json={"email": "editor1@example.com", "role": "editor"},
        headers=owner_headers,
    )

    # Editor attempts to change project settings -> 403 Forbidden
    patch_res = client.patch(
        f"/api/projects/{proj_id}",
        json={"name": "Hacked Name"},
        headers=editor_headers,
    )
    assert patch_res.status_code == 403
    assert "owners" in patch_res.json()["detail"].lower()

    # Editor attempts to add a member -> 403 Forbidden
    add_res = client.post(
        f"/api/projects/{proj_id}/members",
        json={"email": "bystander@example.com", "role": "viewer"},
        headers=editor_headers,
    )
    assert add_res.status_code == 403
    assert "owners" in add_res.json()["detail"].lower()


def test_non_member_cannot_read_a_private_project(client: TestClient, auth_helper):
    """10. A non-member cannot read a private project."""
    _, owner_headers = auth_helper("private_owner@example.com", "Password123!", "Owner")
    _, stranger_headers = auth_helper("stranger@example.com", "Password123!", "Stranger")

    # Create project
    proj_res = client.post(
        "/api/projects",
        json={"name": "Secret Project", "description": "Top secret"},
        headers=owner_headers,
    )
    proj_id = proj_res.json()["id"]

    # Stranger attempts to read project -> 404 Not Found (policy to avoid leakage)
    read_res = client.get(f"/api/projects/{proj_id}", headers=stranger_headers)
    assert read_res.status_code == 404
    assert read_res.json()["detail"] == "Project not found"

    # Stranger attempts to list project members -> 404 Not Found
    members_res = client.get(
        f"/api/projects/{proj_id}/members", headers=stranger_headers
    )
    assert members_res.status_code == 404
    assert members_res.json()["detail"] == "Project not found"

    # Stranger attempts to patch project -> 404 Not Found
    patch_res = client.patch(
        f"/api/projects/{proj_id}",
        json={"name": "Renamed by stranger"},
        headers=stranger_headers,
    )
    assert patch_res.status_code == 404

    # Stranger attempts to add member -> 404 Not Found
    add_res = client.post(
        f"/api/projects/{proj_id}/members",
        json={"email": "stranger@example.com", "role": "viewer"},
        headers=stranger_headers,
    )
    assert add_res.status_code == 404


def test_viewers_cannot_perform_editing_operations(client: TestClient, auth_helper):
    """11. Viewers cannot perform editing operations."""
    _, owner_headers = auth_helper("viewer_test_owner@example.com", "Password123!", "Owner")
    _, viewer_headers = auth_helper("viewer_user@example.com", "Password123!", "Viewer")
    _, target_headers = auth_helper("target_invitee@example.com", "Password123!", "Invitee")

    proj_res = client.post(
        "/api/projects",
        json={"name": "Read Only Project"},
        headers=owner_headers,
    )
    proj_id = proj_res.json()["id"]

    # Add viewer
    client.post(
        f"/api/projects/{proj_id}/members",
        json={"email": "viewer_user@example.com", "role": "viewer"},
        headers=owner_headers,
    )

    # Viewer CAN read project
    read_res = client.get(f"/api/projects/{proj_id}", headers=viewer_headers)
    assert read_res.status_code == 200
    assert read_res.json()["role"] == "viewer"

    # Viewer CAN list members
    members_res = client.get(f"/api/projects/{proj_id}/members", headers=viewer_headers)
    assert members_res.status_code == 200

    # Viewer CANNOT update project settings -> 403 Forbidden
    patch_res = client.patch(
        f"/api/projects/{proj_id}",
        json={"description": "Viewer edit attempt"},
        headers=viewer_headers,
    )
    assert patch_res.status_code == 403

    # Viewer CANNOT add members -> 403 Forbidden
    add_res = client.post(
        f"/api/projects/{proj_id}/members",
        json={"email": "target_invitee@example.com", "role": "viewer"},
        headers=viewer_headers,
    )
    assert add_res.status_code == 403


def test_duplicate_memberships_are_handled_safely(client: TestClient, auth_helper):
    """12. Duplicate memberships are handled safely."""
    _, owner_headers = auth_helper("dup_owner@example.com", "Password123!", "Owner")
    _, member_headers = auth_helper("dup_member@example.com", "Password123!", "Member")

    proj_res = client.post(
        "/api/projects",
        json={"name": "Duplicate Test Project"},
        headers=owner_headers,
    )
    proj_id = proj_res.json()["id"]

    # First add: succeeds
    first_add = client.post(
        f"/api/projects/{proj_id}/members",
        json={"email": "dup_member@example.com", "role": "editor"},
        headers=owner_headers,
    )
    assert first_add.status_code == 201

    # Second add of the same member: rejected with 409 Conflict
    second_add = client.post(
        f"/api/projects/{proj_id}/members",
        json={"email": "dup_member@example.com", "role": "editor"},
        headers=owner_headers,
    )
    assert second_add.status_code == 409
    assert "already a member" in second_add.json()["detail"].lower()


def test_owner_can_update_project_settings(client: TestClient, auth_helper):
    """Owner can successfully update project name, description, and status."""
    _, owner_headers = auth_helper("updater@example.com", "Password123!", "Owner")

    proj_res = client.post(
        "/api/projects",
        json={"name": "Initial Name", "description": "Initial desc"},
        headers=owner_headers,
    )
    proj_id = proj_res.json()["id"]

    patch_res = client.patch(
        f"/api/projects/{proj_id}",
        json={
            "name": "Updated Name",
            "description": "Updated desc",
            "status": "archived",
        },
        headers=owner_headers,
    )
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "Updated desc"
    assert data["status"] == "archived"


def test_invalid_uuid_path_parameter_rejected(client: TestClient, auth_helper):
    """FastAPI rejects invalid UUID path parameters with 422."""
    _, headers = auth_helper("uuid_tester@example.com", "Password123!", "Tester")

    res = client.get("/api/projects/not-a-valid-uuid", headers=headers)
    assert res.status_code == 422


def test_add_nonexistent_user_rejected(client: TestClient, auth_helper):
    """Adding a member with an unregistered email returns 404."""
    _, owner_headers = auth_helper("owner_lookup@example.com", "Password123!", "Owner")

    proj_res = client.post(
        "/api/projects",
        json={"name": "Lookup Test"},
        headers=owner_headers,
    )
    proj_id = proj_res.json()["id"]

    res = client.post(
        f"/api/projects/{proj_id}/members",
        json={"email": "nobody_exists@example.com", "role": "viewer"},
        headers=owner_headers,
    )
    assert res.status_code == 404
    assert "does not exist" in res.json()["detail"].lower()


def test_pagination_and_sorting(client: TestClient, auth_helper):
    """Project list pagination (limit, offset) works as expected."""
    _, headers = auth_helper("paginator@example.com", "Password123!", "Paginator")

    for i in range(5):
        client.post(
            "/api/projects",
            json={"name": f"Page Project {i}"},
            headers=headers,
        )

    # Fetch page 1 (limit 2, offset 0)
    page1 = client.get("/api/projects?limit=2&offset=0", headers=headers)
    assert page1.status_code == 200
    p1_data = page1.json()
    assert p1_data["total"] == 5
    assert len(p1_data["items"]) == 2
    assert p1_data["limit"] == 2
    assert p1_data["offset"] == 0

    # Fetch page 2 (limit 2, offset 2)
    page2 = client.get("/api/projects?limit=2&offset=2", headers=headers)
    assert page2.status_code == 200
    p2_data = page2.json()
    assert len(p2_data["items"]) == 2
    assert p2_data["offset"] == 2
