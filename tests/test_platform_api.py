"""Tests for NeuralBook Platform API."""

import pytest
from fastapi.testclient import TestClient

from neuralbook.platform_api import app


@pytest.fixture
def client(tmp_path):
    """Test client with isolated data directory."""
    import neuralbook.platform_api as api_mod

    original = api_mod.DATA_DIR
    api_mod.DATA_DIR = tmp_path
    client = TestClient(app)
    yield client
    api_mod.DATA_DIR = original


@pytest.fixture
def auth_headers():
    """Headers with valid API key when auth is enabled."""
    import neuralbook.platform_api as api_mod

    original = api_mod.VALID_API_KEYS
    api_mod.VALID_API_KEYS = {"test-key-123"}
    yield {"X-API-Key": "test-key-123"}
    api_mod.VALID_API_KEYS = original


class TestRootAndHealth:
    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert data["message"] == "NeuralBook Platform API"
        assert "version" in data

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"


class TestCreatorEndpoints:
    def test_create_project(self, client):
        r = client.post("/v1/projects", json={"title": "My Book", "slug": "my-book"})
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == "My Book"
        assert data["slug"] == "my-book"
        assert data["status"] == "draft"
        assert "id" in data

    def test_create_project_duplicate_slug(self, client):
        client.post("/v1/projects", json={"title": "Book 1", "slug": "same-slug"})
        r = client.post("/v1/projects", json={"title": "Book 2", "slug": "same-slug"})
        assert r.status_code == 409

    def test_create_project_invalid_slug(self, client):
        r = client.post("/v1/projects", json={"title": "Book", "slug": "INVALID SLUG!"})
        assert r.status_code == 422

    def test_list_projects(self, client):
        client.post("/v1/projects", json={"title": "Book A", "slug": "book-a"})
        client.post("/v1/projects", json={"title": "Book B", "slug": "book-b"})
        r = client.get("/v1/projects")
        assert r.status_code == 200
        assert r.json()["count"] == 2

    def test_get_project(self, client):
        create = client.post("/v1/projects", json={"title": "Found", "slug": "found"}).json()
        r = client.get(f"/v1/projects/{create['id']}")
        assert r.status_code == 200
        assert r.json()["title"] == "Found"

    def test_get_project_not_found(self, client):
        r = client.get("/v1/projects/nonexistent")
        assert r.status_code == 404

    def test_update_project(self, client):
        create = client.post("/v1/projects", json={"title": "Old", "slug": "old"}).json()
        r = client.put(f"/v1/projects/{create['id']}", json={"title": "New", "status": "published"})
        assert r.status_code == 200
        assert r.json()["title"] == "New"
        assert r.json()["status"] == "published"

    def test_update_project_invalid_status(self, client):
        create = client.post("/v1/projects", json={"title": "T", "slug": "t"}).json()
        r = client.put(f"/v1/projects/{create['id']}", json={"status": "invalid"})
        assert r.status_code == 422

    def test_trigger_build(self, client):
        create = client.post("/v1/projects", json={"title": "B", "slug": "b"}).json()
        r = client.post(f"/v1/projects/{create['id']}/builds")
        assert r.status_code == 202
        assert r.json()["status"] == "pending"

    def test_trigger_build_invalid_source(self, client):
        create = client.post("/v1/projects", json={"title": "B", "slug": "b2"}).json()
        r = client.post(f"/v1/projects/{create['id']}/builds?trigger_source=hack")
        assert r.status_code == 422

    def test_get_build(self, client):
        create = client.post("/v1/projects", json={"title": "B", "slug": "b3"}).json()
        build = client.post(f"/v1/projects/{create['id']}/builds").json()
        r = client.get(f"/v1/builds/{build['id']}")
        assert r.status_code == 200
        assert r.json()["build"]["id"] == build["id"]

    def test_get_build_not_found(self, client):
        r = client.get("/v1/builds/nonexistent")
        assert r.status_code == 404

    def test_capture_email(self, client):
        r = client.post("/v1/emails", json={"email": "user@example.com", "source": "landing"})
        assert r.status_code == 201
        assert r.json()["success"] is True

    def test_capture_email_duplicate(self, client):
        client.post("/v1/emails", json={"email": "dup@example.com"})
        r = client.post("/v1/emails", json={"email": "dup@example.com"})
        assert r.status_code == 201
        assert r.json()["already_exists"] is True

    def test_capture_email_invalid(self, client):
        r = client.post("/v1/emails", json={"email": "not-an-email"})
        assert r.status_code == 422


class TestReaderEndpoints:
    def test_register_book(self, client):
        r = client.post(
            "/books", json={"title": "Mind Unset", "slug": "mind-unset", "author": "Author"}
        )
        assert r.status_code == 201
        assert r.json()["status"] == "registered"

    def test_register_book_duplicate(self, client):
        client.post("/books", json={"title": "B", "slug": "dup-book"})
        r = client.post("/books", json={"title": "B2", "slug": "dup-book"})
        assert r.status_code == 409

    def test_list_books(self, client):
        client.post("/books", json={"title": "B1", "slug": "b1"})
        client.post("/books", json={"title": "B2", "slug": "b2"})
        r = client.get("/books")
        assert r.json()["count"] == 2

    def test_get_book(self, client):
        client.post("/books", json={"title": "Found Book", "slug": "found-book"})
        r = client.get("/books/found-book")
        assert r.status_code == 200
        assert r.json()["title"] == "Found Book"

    def test_get_book_not_found(self, client):
        r = client.get("/books/nope")
        assert r.status_code == 404

    def test_list_patches_empty(self, client):
        client.post("/books", json={"title": "B", "slug": "patch-b"})
        r = client.get("/books/patch-b/patches")
        assert r.json()["count"] == 0

    def test_latest_patch_none(self, client):
        client.post("/books", json={"title": "B", "slug": "latest-b"})
        r = client.get("/books/latest-b/latest")
        assert r.json()["latest"] is None

    def test_verify_no_reference(self, client):
        client.post("/books", json={"title": "B", "slug": "verify-b"})
        r = client.post("/books/verify-b/verify", json={"root_hash": "a" * 64})
        assert r.json()["status"] == "no_reference"

    def test_verify_mismatch(self, client):
        client.post("/books", json={"title": "B", "slug": "verify-m", "root_hash": "b" * 64})
        r = client.post("/books/verify-m/verify", json={"root_hash": "a" * 64})
        assert r.json()["status"] == "mismatch"

    def test_verify_match(self, client):
        client.post("/books", json={"title": "B", "slug": "verify-ok", "root_hash": "a" * 64})
        r = client.post("/books/verify-ok/verify", json={"root_hash": "a" * 64})
        assert r.json()["status"] == "match"

    def test_verify_invalid_hash_length(self, client):
        client.post("/books", json={"title": "B", "slug": "verify-bad"})
        r = client.post("/books/verify-bad/verify", json={"root_hash": "tooshort"})
        assert r.status_code == 422


class TestAuth:
    def test_write_blocked_without_key(self, client, auth_headers):
        """When auth is enabled, write ops require key."""
        r = client.post("/v1/projects", json={"title": "Blocked", "slug": "blocked"})
        assert r.status_code == 401

    def test_write_allowed_with_key(self, client, auth_headers):
        r = client.post(
            "/v1/projects", json={"title": "Allowed", "slug": "allowed"}, headers=auth_headers
        )
        assert r.status_code == 201

    def test_read_allowed_without_key(self, client, auth_headers):
        """Read endpoints remain public even with auth enabled."""
        r = client.get("/books")
        assert r.status_code == 200

        r = client.get("/health")
        assert r.status_code == 200


class TestTierAndSubscriberEndpoints:
    def test_tier_crud_pricing_and_subscribers_flow(self, client):
        client.post(
            "/books",
            json={"title": "Tiered Book", "slug": "tiered-book", "author": "Author"},
        )

        create_tier = client.post(
            "/v1/books/tiered-book/tiers",
            json={
                "id": "pro",
                "name": "Pro",
                "price": 29,
                "currency": "USD",
                "features": ["read", "download"],
                "description": "Pro tier",
            },
        )
        assert create_tier.status_code == 201
        assert create_tier.json()["tier"]["id"] == "pro"

        list_tiers = client.get("/v1/books/tiered-book/tiers")
        assert list_tiers.status_code == 200
        assert list_tiers.json()["count"] == 1

        get_tier = client.get("/v1/books/tiered-book/tiers/pro")
        assert get_tier.status_code == 200
        assert get_tier.json()["name"] == "Pro"

        sub = client.post(
            "/v1/books/tiered-book/subscribers",
            json={"email": "reader@example.com", "tier_id": "pro", "book_slug": "tiered-book"},
        )
        assert sub.status_code == 201
        assert sub.json()["status"] == "subscribed"

        list_subs = client.get("/v1/books/tiered-book/subscribers")
        assert list_subs.status_code == 200
        assert list_subs.json()["count"] == 1

        filtered_subs = client.get("/v1/books/tiered-book/subscribers?tier_id=pro")
        assert filtered_subs.status_code == 200
        assert filtered_subs.json()["count"] == 1

        get_sub = client.get("/v1/books/tiered-book/subscribers/reader@example.com")
        assert get_sub.status_code == 200
        assert get_sub.json()["has_access"] is True
        assert "download" in get_sub.json()["features"]

        analytics = client.get("/v1/books/tiered-book/analytics")
        assert analytics.status_code == 200
        assert analytics.json()["total_subscribers"] == 1
        assert analytics.json()["by_tier"]["pro"]["revenue"] == 29

        pricing = client.get("/v1/books/tiered-book/pricing")
        assert pricing.status_code == 200
        assert pricing.json()["count"] == 1

        deactivate = client.put("/v1/books/tiered-book/tiers/pro", json={"active": False})
        assert deactivate.status_code == 200

        pricing_after = client.get("/v1/books/tiered-book/pricing")
        assert pricing_after.status_code == 200
        assert pricing_after.json()["count"] == 0

    def test_subscriber_update_existing_and_not_found_paths(self, client):
        client.post("/books", json={"title": "Book", "slug": "book-sub"})
        client.post(
            "/v1/books/book-sub/tiers",
            json={"id": "basic", "name": "Basic", "price": 9, "features": ["read"]},
        )

        first = client.post(
            "/v1/books/book-sub/subscribers",
            json={"email": "same@example.com", "tier_id": "basic", "book_slug": "book-sub"},
        )
        assert first.status_code == 201
        assert first.json()["status"] == "subscribed"

        second = client.post(
            "/v1/books/book-sub/subscribers",
            json={"email": "same@example.com", "tier_id": "basic", "book_slug": "book-sub"},
        )
        assert second.status_code == 201
        assert second.json()["status"] == "updated"

        missing_tier = client.post(
            "/v1/books/book-sub/subscribers",
            json={"email": "x@example.com", "tier_id": "nope", "book_slug": "book-sub"},
        )
        assert missing_tier.status_code == 404

        missing_sub = client.get("/v1/books/book-sub/subscribers/missing@example.com")
        assert missing_sub.status_code == 404


class TestReaderAccessHelper:
    def test_check_reader_access_feature_and_expiration_paths(self, client):
        import neuralbook.platform_api as api_mod

        client.post("/books", json={"title": "Secured", "slug": "secured"})
        client.post(
            "/v1/books/secured/tiers",
            json={"id": "pro", "name": "Pro", "price": 19, "features": ["read", "download"]},
        )
        client.post(
            "/v1/books/secured/subscribers",
            json={"email": "ok@example.com", "tier_id": "pro", "book_slug": "secured"},
        )

        has_feature = api_mod._check_reader_access("ok@example.com", "secured", "download")
        assert has_feature["has_access"] is True

        missing_feature = api_mod._check_reader_access("ok@example.com", "secured", "audio")
        assert missing_feature["has_access"] is False
        assert "available_features" in missing_feature

        no_sub = api_mod._check_reader_access("none@example.com", "secured")
        assert no_sub["has_access"] is False
        assert no_sub["tier_id"] is None


class TestPatchAndExportEndpoints:
    def test_upload_patch_invalid_json_and_not_found(self, client):
        bad_file = {"file": ("bad.nbook-patch.json", b"{not-json", "application/json")}

        missing_book = client.post("/books/missing/patches", files=bad_file)
        assert missing_book.status_code == 404

        client.post("/books", json={"title": "Patch Book", "slug": "patch-book"})
        invalid_json = client.post("/books/patch-book/patches", files=bad_file)
        assert invalid_json.status_code == 400

    def test_upload_get_latest_patch_flow(self, client):
        import json

        client.post(
            "/books",
            json={"title": "Patch Flow", "slug": "patch-flow", "root_hash": "a" * 64},
        )

        payload = {
            "neuralbook_patch": {"patch_id": "p001"},
            "verification": {"new_root_hash": "b" * 64},
        }
        patch_file = {"file": ("p001.nbook-patch.json", json.dumps(payload), "application/json")}
        up = client.post("/books/patch-flow/patches", files=patch_file)
        assert up.status_code == 200
        assert up.json()["patch_id"] == "p001"

        fetched = client.get("/books/patch-flow/patches/p001")
        assert fetched.status_code == 200
        assert fetched.json()["verification"]["new_root_hash"] == "b" * 64

        latest = client.get("/books/patch-flow/latest")
        assert latest.status_code == 200
        assert latest.json()["patch_count"] == 1
        assert latest.json()["latest"]["neuralbook_patch"]["patch_id"] == "p001"

        missing = client.get("/books/patch-flow/patches/nope")
        assert missing.status_code == 404

    def test_export_book_not_found_and_missing_nbook(self, client):
        not_found = client.get("/books/no-book/export?format=html")
        assert not_found.status_code == 404

        client.post("/books", json={"title": "No Nbook", "slug": "no-nbook"})
        missing_nbook = client.get("/books/no-nbook/export?format=html")
        assert missing_nbook.status_code == 404

    def test_export_book_html_and_epub_success(self, client):
        import neuralbook.platform_api as api_mod
        from neuralbook.format import NeuralBookDocument

        client.post(
            "/books",
            json={"title": "Exported", "slug": "exported", "style": "cyberpunk"},
        )

        # Put .nbook in books/ to exercise parent-file fallback path.
        doc = NeuralBookDocument(meta={"title": "Exported", "author": "Tester"})
        doc.add_section("section", "I", "Start", "Body content")
        nbook_path = api_mod.DATA_DIR / "books" / "exported.nbook"
        doc.write_file(nbook_path)

        html = client.get("/books/exported/export?format=html")
        assert html.status_code == 200
        assert "text/html" in html.headers["content-type"]

        epub = client.get("/books/exported/export?format=epub")
        assert epub.status_code == 200
        assert "application/epub+zip" in epub.headers["content-type"]


class TestYamlFallbackHelpers:
    def test_tiers_and_subscribers_json_fallback_when_yaml_missing(self, client, monkeypatch):
        import builtins
        import json

        import neuralbook.platform_api as api_mod

        client.post("/books", json={"title": "Fallback", "slug": "fallback"})
        book_dir = api_mod.DATA_DIR / "books" / "fallback"
        (book_dir / "tiers.yaml").write_text("ignored", encoding="utf-8")
        (book_dir / "subscribers.yaml").write_text("ignored", encoding="utf-8")
        (book_dir / "tiers.json").write_text(
            json.dumps([{"id": "t1", "name": "Tier 1", "price": 1}]), encoding="utf-8"
        )
        (book_dir / "subscribers.json").write_text(
            json.dumps([{"email": "a@b.com", "tier_id": "t1"}]), encoding="utf-8"
        )

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError("yaml intentionally unavailable for test")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        tiers = api_mod._load_tiers("fallback")
        subscribers = api_mod._load_subscribers("fallback")
        assert tiers[0]["id"] == "t1"
        assert subscribers[0]["email"] == "a@b.com"

        api_mod._save_tiers("fallback", [{"id": "t2", "name": "Tier 2", "price": 2}])
        api_mod._save_subscribers("fallback", [{"email": "c@d.com", "tier_id": "t2"}])
        assert (book_dir / "tiers.json").exists()
        assert (book_dir / "subscribers.json").exists()
