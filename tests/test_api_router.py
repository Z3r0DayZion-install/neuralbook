"""
Tests for the API router module.
"""

import json
import tempfile
from pathlib import Path

import pytest

from neuralbook.api_router import route_request


@pytest.fixture
def temp_store():
    """Create a temporary store file for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "test_store.json"
        yield store_path


class TestHealthCheck:
    """Tests for health check endpoints."""

    def test_health_endpoint(self, temp_store):
        """Test /health endpoint."""
        status, response = route_request("GET", "/health", b"", temp_store)
        assert status == 200
        assert response["status"] == "healthy"
        assert response["service"] == "creator-platform-api"

    def test_healthz_endpoint(self, temp_store):
        """Test /healthz endpoint (alternate health check)."""
        status, response = route_request("GET", "/healthz", b"", temp_store)
        assert status == 200
        assert response["status"] == "healthy"


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_get(self, temp_store):
        """Test GET / returns API info."""
        status, response = route_request("GET", "/", b"", temp_store)
        assert status == 200
        assert "message" in response
        assert "version" in response


class TestProjectsCollection:
    """Tests for /v1/projects collection endpoint."""

    def test_list_projects_empty(self, temp_store):
        """Test listing projects when none exist."""
        status, response = route_request("GET", "/v1/projects", b"", temp_store)
        assert status == 200
        assert response == []

    def test_create_project_success(self, temp_store):
        """Test creating a project with valid data."""
        payload = json.dumps({"title": "Test Book", "slug": "test-book"}).encode()
        status, response = route_request("POST", "/v1/projects", payload, temp_store)

        assert status == 201
        assert response["title"] == "Test Book"
        assert response["slug"] == "test-book"
        assert "id" in response
        assert response["status"] == "draft"

    def test_create_project_with_theme(self, temp_store):
        """Test creating a project with custom theme."""
        payload = json.dumps(
            {"title": "Themed Book", "slug": "themed-book", "theme": "minimal"}
        ).encode()
        status, response = route_request("POST", "/v1/projects", payload, temp_store)

        assert status == 201
        assert response["theme"] == "minimal"

    def test_create_project_missing_title(self, temp_store):
        """Test creating a project without title."""
        payload = json.dumps({"slug": "no-title"}).encode()
        status, response = route_request("POST", "/v1/projects", payload, temp_store)

        assert status == 400
        assert "title and slug are required" in response["error"]

    def test_create_project_missing_slug(self, temp_store):
        """Test creating a project without slug."""
        payload = json.dumps({"title": "No Slug"}).encode()
        status, response = route_request("POST", "/v1/projects", payload, temp_store)

        assert status == 400
        assert "title and slug are required" in response["error"]

    def test_create_project_empty_title(self, temp_store):
        """Test creating a project with empty title."""
        payload = json.dumps({"title": "   ", "slug": "test"}).encode()
        status, response = route_request("POST", "/v1/projects", payload, temp_store)

        assert status == 400
        assert "title and slug are required" in response["error"]

    def test_create_project_duplicate_slug(self, temp_store):
        """Test creating projects with duplicate slug."""
        payload1 = json.dumps({"title": "First Book", "slug": "duplicate"}).encode()
        route_request("POST", "/v1/projects", payload1, temp_store)

        payload2 = json.dumps({"title": "Second Book", "slug": "duplicate"}).encode()
        status, response = route_request("POST", "/v1/projects", payload2, temp_store)

        assert status == 409
        assert "error" in response

    def test_list_projects_after_create(self, temp_store):
        """Test listing projects after creation."""
        payload = json.dumps({"title": "Test Book", "slug": "test-book"}).encode()
        route_request("POST", "/v1/projects", payload, temp_store)

        status, response = route_request("GET", "/v1/projects", b"", temp_store)
        assert status == 200
        assert len(response) == 1
        assert response[0]["title"] == "Test Book"

    def test_projects_invalid_method(self, temp_store):
        """Test invalid HTTP method on /v1/projects."""
        status, response = route_request("DELETE", "/v1/projects", b"", temp_store)
        assert status == 405
        assert "method not allowed" in response["error"]


class TestProjectsResource:
    """Tests for /v1/projects/:id endpoint."""

    def test_get_project_success(self, temp_store):
        """Test retrieving an existing project."""
        # Create a project
        payload = json.dumps({"title": "Test Book", "slug": "test-book"}).encode()
        _, created = route_request("POST", "/v1/projects", payload, temp_store)
        project_id = created["id"]

        # Retrieve it
        status, response = route_request("GET", f"/v1/projects/{project_id}", b"", temp_store)
        assert status == 200
        assert response["id"] == project_id
        assert response["title"] == "Test Book"

    def test_get_project_not_found(self, temp_store):
        """Test retrieving a non-existent project."""
        status, response = route_request("GET", "/v1/projects/nonexistent", b"", temp_store)
        assert status == 404
        assert "project not found" in response["error"]

    def test_update_project_success(self, temp_store):
        """Test updating a project."""
        # Create a project
        payload = json.dumps({"title": "Original", "slug": "original"}).encode()
        _, created = route_request("POST", "/v1/projects", payload, temp_store)
        project_id = created["id"]

        # Update it
        update_payload = json.dumps({"title": "Updated"}).encode()
        status, response = route_request(
            "PUT", f"/v1/projects/{project_id}", update_payload, temp_store
        )

        assert status == 200
        assert response["title"] == "Updated"
        assert response["id"] == project_id

    def test_update_project_status(self, temp_store):
        """Test updating project status."""
        payload = json.dumps({"title": "Book", "slug": "book"}).encode()
        _, created = route_request("POST", "/v1/projects", payload, temp_store)
        project_id = created["id"]

        update_payload = json.dumps({"status": "published"}).encode()
        status, response = route_request(
            "PUT", f"/v1/projects/{project_id}", update_payload, temp_store
        )

        assert status == 200
        assert response["status"] == "published"

    def test_update_nonexistent_project(self, temp_store):
        """Test updating a non-existent project."""
        update_payload = json.dumps({"title": "Updated"}).encode()
        status, response = route_request(
            "PUT", "/v1/projects/nonexistent", update_payload, temp_store
        )

        assert status == 404
        assert "project not found" in response["error"]

    def test_project_invalid_method(self, temp_store):
        """Test invalid HTTP method on project resource."""
        status, response = route_request("DELETE", "/v1/projects/some-id", b"", temp_store)
        assert status == 405


class TestBuilds:
    """Tests for /v1/projects/:id/build endpoint."""

    def test_create_build_success(self, temp_store):
        """Test triggering a build for a project."""
        # Create a project
        payload = json.dumps({"title": "Test Book", "slug": "test-book"}).encode()
        _, created = route_request("POST", "/v1/projects", payload, temp_store)
        project_id = created["id"]

        # Trigger a build
        build_payload = json.dumps({"trigger_source": "manual"}).encode()
        status, response = route_request(
            "POST", f"/v1/projects/{project_id}/build", build_payload, temp_store
        )

        assert status == 202
        assert response["project_id"] == project_id
        assert response["status"] == "queued"
        assert "id" in response

    def test_create_build_nonexistent_project(self, temp_store):
        """Test creating a build for non-existent project."""
        build_payload = json.dumps({"trigger_source": "manual"}).encode()
        status, response = route_request(
            "POST", "/v1/projects/nonexistent/build", build_payload, temp_store
        )

        assert status == 404
        assert "error" in response

    def test_create_build_default_trigger_source(self, temp_store):
        """Test creating a build with default trigger source."""
        # Create a project
        payload = json.dumps({"title": "Test Book", "slug": "test-book"}).encode()
        _, created = route_request("POST", "/v1/projects", payload, temp_store)
        project_id = created["id"]

        # Trigger a build without trigger_source
        build_payload = json.dumps({}).encode()
        status, response = route_request(
            "POST", f"/v1/projects/{project_id}/build", build_payload, temp_store
        )

        assert status == 202
        assert response["trigger_source"] == "manual"


class TestInvalidRoutes:
    """Tests for invalid routes."""

    def test_nonexistent_route(self, temp_store):
        """Test accessing a nonexistent route."""
        status, response = route_request("GET", "/v1/nonexistent", b"", temp_store)
        assert status == 404
        assert "not found" in response["error"]

    def test_malformed_path(self, temp_store):
        """Test accessing malformed path."""
        status, response = route_request("GET", "/v1/projects/id/extra/segments", b"", temp_store)
        assert status == 404


class TestEmailCapture:
    """Tests for email capture endpoint."""

    @pytest.mark.skip(reason="capture_email function not implemented")
    def test_capture_email_success(self, temp_store):
        """Test capturing a valid email."""
        payload = json.dumps({"email": "test@example.com", "source": "landing_page"}).encode()
        status, response = route_request("POST", "/v1/emails", payload, temp_store)

        assert status == 201
        assert response["success"] is True
        assert response["email"] == "test@example.com"

    def test_capture_email_invalid(self, temp_store):
        """Test capturing an invalid email."""
        payload = json.dumps({"email": "not-an-email", "source": "landing_page"}).encode()
        status, response = route_request("POST", "/v1/emails", payload, temp_store)

        assert status == 422
        assert "invalid email address" in response["error"]

    def test_capture_email_missing(self, temp_store):
        """Test capturing without email."""
        payload = json.dumps({"source": "landing_page"}).encode()
        status, response = route_request("POST", "/v1/emails", payload, temp_store)

        assert status == 422
        assert "invalid email address" in response["error"]

    def test_email_invalid_method(self, temp_store):
        """Test invalid method on email endpoint."""
        status, response = route_request("GET", "/v1/emails", b"", temp_store)
        assert status == 405


class TestQueryStringHandling:
    """Tests for query string handling."""

    def test_ignore_query_string_on_get(self, temp_store):
        """Test that query strings are ignored during routing."""
        status, response = route_request("GET", "/health?foo=bar&baz=qux", b"", temp_store)
        assert status == 200
        assert response["status"] == "healthy"

    def test_ignore_query_string_on_list(self, temp_store):
        """Test that query strings don't affect list operation."""
        status, response = route_request("GET", "/v1/projects?sort=date", b"", temp_store)
        assert status == 200
        assert response == []


class TestMalformedJSON:
    """Tests for handling malformed JSON."""

    def test_malformed_json_treated_as_empty(self, temp_store):
        """Test that malformed JSON is treated as empty body."""
        bad_json = b"{ not valid json }"
        status, response = route_request("POST", "/v1/projects", bad_json, temp_store)

        # Should fail due to missing required fields, not JSON parse error
        assert status == 400
        assert "title and slug are required" in response["error"]
