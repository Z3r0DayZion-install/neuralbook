"""Tests for neuralbook.api routing and helpers."""

import json

from neuralbook.api import Build, Project, Store, _json_body, new_id, now_iso, route_request


def test_now_iso_returns_iso_string():
    value = now_iso()
    assert "T" in value
    assert value


def test_new_id_includes_prefix():
    identifier = new_id("proj")
    assert identifier.startswith("proj_")
    assert len(identifier) > len("proj_")


def test_project_and_build_dataclasses_set_timestamps():
    project = Project(id="proj_1", title="Book", slug="book")
    build = Build(id="build_1", project_id="proj_1")

    assert project.created_at
    assert project.updated_at
    assert build.created_at
    assert build.status == "pending"


def test_store_load_defaults_when_missing(tmp_path):
    store = Store(tmp_path / "missing.json")
    data = store.load()
    assert data == {"projects": [], "builds": []}


def test_store_load_defaults_on_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{broken", encoding="utf-8")
    store = Store(path)
    data = store.load()
    assert data == {"projects": [], "builds": []}


def test_json_body_empty_and_invalid():
    assert _json_body(b"") == {}
    assert _json_body(b"{invalid}") == {}
    assert _json_body(b"\xff\xfe") == {}


def test_root_and_health_endpoints(tmp_path):
    store_path = tmp_path / "store.json"

    status, payload = route_request("GET", "/", b"", store_path)
    assert status == 200
    assert payload["message"] == "NeuralBook Platform API"

    status, payload = route_request("GET", "/health?full=1", b"", store_path)
    assert status == 200
    assert payload["status"] == "healthy"


def test_projects_get_post_and_duplicate_slug(tmp_path):
    store_path = tmp_path / "store.json"

    status, payload = route_request("GET", "/v1/projects", b"", store_path)
    assert status == 200
    assert payload == {"projects": []}

    body = json.dumps({"title": "My Book", "slug": "my-book"}).encode()
    status, created = route_request("POST", "/v1/projects", body, store_path)
    assert status == 201
    assert created["slug"] == "my-book"

    status, dup = route_request("POST", "/v1/projects", body, store_path)
    assert status == 409
    assert "slug already exists" in dup["error"]


def test_projects_validation_and_method_not_allowed(tmp_path):
    store_path = tmp_path / "store.json"
    status, payload = route_request("POST", "/v1/projects", b"{}", store_path)
    assert status == 400
    assert "title and slug are required" in payload["error"]

    status, payload = route_request("DELETE", "/v1/projects", b"", store_path)
    assert status == 405
    assert "method not allowed" in payload["error"]


def test_project_resource_and_build_flow(tmp_path):
    store_path = tmp_path / "store.json"
    body = json.dumps({"title": "My Book", "slug": "my-book"}).encode()
    _, created = route_request("POST", "/v1/projects", body, store_path)
    project_id = created["id"]

    status, fetched = route_request("GET", f"/v1/projects/{project_id}", b"", store_path)
    assert status == 200
    assert fetched["id"] == project_id

    status, missing = route_request("GET", "/v1/projects/does-not-exist", b"", store_path)
    assert status == 404
    assert "project not found" in missing["error"]

    status, build = route_request("POST", f"/v1/projects/{project_id}/builds", b"{}", store_path)
    assert status == 202
    assert build["project_id"] == project_id

    status, payload = route_request("POST", "/v1/projects/nope/builds", b"{}", store_path)
    assert status == 404
    assert "project not found" in payload["error"]


def test_builds_endpoint_get_and_not_found(tmp_path):
    store_path = tmp_path / "store.json"
    body = json.dumps({"title": "My Book", "slug": "my-book"}).encode()
    _, created = route_request("POST", "/v1/projects", body, store_path)
    _, build = route_request("POST", f"/v1/projects/{created['id']}/builds", b"{}", store_path)

    status, fetched = route_request("GET", f"/v1/builds/{build['id']}", b"", store_path)
    assert status == 200
    assert fetched["id"] == build["id"]

    status, payload = route_request("GET", "/v1/builds/missing", b"", store_path)
    assert status == 404
    assert "build not found" in payload["error"]

    status, payload = route_request("POST", f"/v1/builds/{build['id']}", b"", store_path)
    assert status == 404
    assert "not found" in payload["error"]


def test_email_capture_validation_and_method_handling(tmp_path):
    store_path = tmp_path / "store.json"

    bad = json.dumps({"email": "not-an-email"}).encode()
    status, payload = route_request("POST", "/v1/emails", bad, store_path)
    assert status == 422
    assert "invalid email address" in payload["error"]

    good = json.dumps({"email": "user@example.com"}).encode()
    status, payload = route_request("POST", "/v1/emails", good, store_path)
    assert status == 201
    assert payload["success"] is True
    assert payload["email"] == "user@example.com"

    status, payload = route_request("GET", "/v1/emails", b"", store_path)
    assert status == 405
    assert "method not allowed" in payload["error"]


def test_unknown_routes_return_404(tmp_path):
    store_path = tmp_path / "store.json"
    status, payload = route_request("GET", "/v1/unknown", b"", store_path)
    assert status == 404
    assert "not found" in payload["error"]
