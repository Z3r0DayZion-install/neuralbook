"""
Tests for the core module.
"""

import tempfile
from pathlib import Path

import pytest

from neuralbook.core import (
    Store,
    create_build,
    create_project,
    get_build,
    get_project,
    list_projects,
    update_project,
)


@pytest.fixture
def temp_store():
    """Create a temporary store file for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "test_store.json"
        yield store_path


class TestStore:
    """Tests for Store class."""

    def test_store_initialization(self, temp_store):
        """Test store initialization creates necessary files."""
        store = Store(temp_store)
        assert store.path == temp_store

    def test_store_persistence(self, temp_store):
        """Test that store persists data."""
        store1 = Store(temp_store)
        project1 = create_project(store1, title="Book 1", slug="book-1")

        # Load with new store instance
        store2 = Store(temp_store)
        projects = list_projects(store2)
        assert len(projects) == 1
        assert projects[0]["title"] == "Book 1"


class TestCreateProject:
    """Tests for creating projects."""

    def test_create_project_basic(self, temp_store):
        """Test basic project creation."""
        store = Store(temp_store)
        project = create_project(store, title="My Book", slug="my-book")

        assert project["title"] == "My Book"
        assert project["slug"] == "my-book"
        assert project["status"] == "draft"
        assert "id" in project
        assert project["id"].startswith("p_")

    def test_create_project_with_theme(self, temp_store):
        """Test project creation with custom theme."""
        store = Store(temp_store)
        project = create_project(store, title="Book", slug="book", theme="minimal")

        assert project["theme"] == "minimal"

    def test_create_project_default_theme(self, temp_store):
        """Test project uses default theme."""
        store = Store(temp_store)
        project = create_project(store, title="Book", slug="book")

        assert project["theme"] == "cyberpunk"

    def test_create_project_duplicate_slug_raises(self, temp_store):
        """Test that duplicate slug raises ValueError."""
        store = Store(temp_store)
        create_project(store, title="Book 1", slug="duplicate")

        with pytest.raises(ValueError, match="already exists"):
            create_project(store, title="Book 2", slug="duplicate")

    def test_create_project_has_metadata(self, temp_store):
        """Test that created project has metadata."""
        store = Store(temp_store)
        project = create_project(store, title="Book", slug="book")

        assert "content" in project
        assert "metadata" in project["content"]
        assert project["content"]["metadata"]["title"] == "Book"

    def test_create_project_has_pricing(self, temp_store):
        """Test that created project has pricing tiers."""
        store = Store(temp_store)
        project = create_project(store, title="Book", slug="book")

        assert "pricing" in project
        assert "tiers" in project["pricing"]
        assert len(project["pricing"]["tiers"]) > 0


class TestGetProject:
    """Tests for retrieving projects."""

    def test_get_project_success(self, temp_store):
        """Test retrieving an existing project."""
        store = Store(temp_store)
        created = create_project(store, title="Book", slug="book")

        retrieved = get_project(store, created["id"])
        assert retrieved["id"] == created["id"]
        assert retrieved["title"] == "Book"

    def test_get_project_not_found(self, temp_store):
        """Test retrieving non-existent project returns None."""
        store = Store(temp_store)
        result = get_project(store, "nonexistent_id")
        assert result is None


class TestListProjects:
    """Tests for listing projects."""

    def test_list_projects_empty(self, temp_store):
        """Test listing when no projects exist."""
        store = Store(temp_store)
        projects = list_projects(store)
        assert projects == []

    def test_list_projects_multiple(self, temp_store):
        """Test listing multiple projects."""
        store = Store(temp_store)
        create_project(store, title="Book 1", slug="book-1")
        create_project(store, title="Book 2", slug="book-2")

        projects = list_projects(store)
        assert len(projects) == 2
        assert projects[0]["title"] == "Book 1"
        assert projects[1]["title"] == "Book 2"


class TestUpdateProject:
    """Tests for updating projects."""

    def test_update_project_title(self, temp_store):
        """Test updating project title."""
        store = Store(temp_store)
        project = create_project(store, title="Original", slug="original")

        updated = update_project(store, project["id"], title="Updated")
        assert updated["title"] == "Updated"
        assert updated["slug"] == "original"  # Slug unchanged

    def test_update_project_status(self, temp_store):
        """Test updating project status."""
        store = Store(temp_store)
        project = create_project(store, title="Book", slug="book")

        updated = update_project(store, project["id"], status="published")
        assert updated["status"] == "published"

    def test_update_project_theme(self, temp_store):
        """Test updating project theme."""
        store = Store(temp_store)
        project = create_project(store, title="Book", slug="book", theme="cyberpunk")

        updated = update_project(store, project["id"], theme="minimal")
        assert updated["theme"] == "minimal"

    def test_update_project_multiple_fields(self, temp_store):
        """Test updating multiple fields at once."""
        store = Store(temp_store)
        project = create_project(store, title="Book", slug="book")

        updated = update_project(
            store, project["id"], title="New Title", status="published", theme="minimal"
        )
        assert updated["title"] == "New Title"
        assert updated["status"] == "published"
        assert updated["theme"] == "minimal"

    def test_update_project_preserves_unchanged_fields(self, temp_store):
        """Test that update preserves unmodified fields."""
        store = Store(temp_store)
        project = create_project(store, title="Original", slug="original", theme="cyberpunk")
        original_id = project["id"]

        updated = update_project(store, original_id, title="Updated")
        assert updated["id"] == original_id
        assert updated["slug"] == "original"
        assert updated["theme"] == "cyberpunk"


class TestCreateBuild:
    """Tests for creating builds."""

    def test_create_build_success(self, temp_store):
        """Test creating a build for a project."""
        store = Store(temp_store)
        project = create_project(store, title="Book", slug="book")

        build = create_build(store, project["id"], trigger_source="manual")

        assert build["project_id"] == project["id"]
        assert build["status"] == "queued"
        assert build["trigger_source"] == "manual"
        assert "id" in build
        assert build["id"].startswith("b_")

    def test_create_build_nonexistent_project(self, temp_store):
        """Test creating build for non-existent project raises error."""
        store = Store(temp_store)

        with pytest.raises(ValueError, match="not found"):
            create_build(store, "nonexistent", trigger_source="manual")

    def test_create_build_default_trigger(self, temp_store):
        """Test creating build with default trigger source."""
        store = Store(temp_store)
        project = create_project(store, title="Book", slug="book")

        build = create_build(store, project["id"])
        assert build["trigger_source"] == "manual"


class TestGetBuild:
    """Tests for retrieving builds."""

    def test_get_build_success(self, temp_store):
        """Test retrieving an existing build."""
        store = Store(temp_store)
        project = create_project(store, title="Book", slug="book")
        created_build = create_build(store, project["id"])

        retrieved = get_build(store, created_build["id"])
        assert retrieved["id"] == created_build["id"]
        assert retrieved["project_id"] == project["id"]

    def test_get_build_not_found(self, temp_store):
        """Test retrieving non-existent build returns None."""
        store = Store(temp_store)
        result = get_build(store, "nonexistent_id")
        assert result is None


class TestProjectIdGeneration:
    """Tests for project ID generation."""

    def test_project_ids_are_unique(self, temp_store):
        """Test that each project gets a unique ID."""
        store = Store(temp_store)
        p1 = create_project(store, title="Book 1", slug="book-1")
        p2 = create_project(store, title="Book 2", slug="book-2")

        assert p1["id"] != p2["id"]

    def test_project_ids_start_with_p_prefix(self, temp_store):
        """Test that project IDs have correct prefix."""
        store = Store(temp_store)
        project = create_project(store, title="Book", slug="book")

        assert project["id"].startswith("p_")


class TestTimestamps:
    """Tests for timestamp handling."""

    def test_created_at_exists(self, temp_store):
        """Test that created_at is set on project creation."""
        store = Store(temp_store)
        project = create_project(store, title="Book", slug="book")

        assert "created_at" in project
        assert project["created_at"]

    def test_updated_at_exists(self, temp_store):
        """Test that updated_at is set on project creation."""
        store = Store(temp_store)
        project = create_project(store, title="Book", slug="book")

        assert "updated_at" in project
        assert project["updated_at"]

    def test_updated_at_changes_on_update(self, temp_store):
        """Test that updated_at changes when project is updated."""
        store = Store(temp_store)
        project = create_project(store, title="Book", slug="book")
        original_updated = project["updated_at"]

        # Add a small delay to ensure timestamps differ
        import time

        time.sleep(0.01)

        updated = update_project(store, project["id"], title="New Title")
        assert updated["updated_at"] > original_updated
