"""Tests for NeuralBook format SDK."""

import pytest

from neuralbook.format import (
    FORMAT_VERSION,
    NeuralBookDocument,
    ValidationResult,
    _increment_patch,
    import_txt,
    root_hash,
    section_hash,
    validate_format,
    validate_full,
    validate_integrity,
    validate_structure,
)

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def sample_txt(tmp_path):
    p = tmp_path / "sample.txt"
    p.write_text(
        "===== SECTION I: First Section =====\n"
        "Body of first section.\n"
        "===== SECTION II: Second Section =====\n"
        "Body of second section.\n"
        "===== PART I: First Part =====\n"
        "Body of first part.\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def empty_doc():
    return NeuralBookDocument(
        meta={
            "title": "Test",
            "author": "Author",
            "slug": "test",
            "edition": "1.0.0",
            "language": "en",
            "license": "MIT",
            "tags": [],
            "word_count": 0,
            "section_count": 0,
        }
    )


@pytest.fixture
def populated_doc(empty_doc):
    empty_doc.add_section("section", "I", "First", "Hello world")
    empty_doc.add_section("section", "II", "Second", "More text here")
    empty_doc.add_section("part", "I", "Part One", "Part body content")
    return empty_doc


# ── NeuralBookDocument ────────────────────────────────────────────────────


class TestNeuralBookDocument:
    def test_init_defaults(self):
        doc = NeuralBookDocument()
        assert doc.neuralbook["format"] == FORMAT_VERSION
        assert doc.neuralbook["sealed"] is False
        assert doc.meta["section_count"] == 0

    def test_add_section(self, empty_doc):
        s = empty_doc.add_section("section", "I", "Test", "Body text")
        assert s["id"] == "sec-I"
        assert s["hash"]
        assert empty_doc.meta["section_count"] == 1
        assert empty_doc.meta["word_count"] > 0

    def test_add_section_with_weight_class(self, empty_doc):
        s = empty_doc.add_section("section", "I", "Test", "Body", weight_class="WEAPONIZED")
        assert s["weight_class"] == "WEAPONIZED"

    def test_add_section_with_protocols(self, empty_doc):
        proto = [{"id": "p1", "name": "Audit", "type": "audit", "steps": ["Step 1"]}]
        s = empty_doc.add_section("section", "I", "Test", "Body", protocols=proto)
        assert s["protocols"] == proto

    def test_get_section(self, populated_doc):
        s = populated_doc.get_section("sec-I")
        assert s is not None
        assert s["title"] == "First"

    def test_get_section_missing(self, populated_doc):
        assert populated_doc.get_section("sec-999") is None

    def test_update_section(self, populated_doc):
        s = populated_doc.update_section("sec-I", title="Updated First")
        assert s["title"] == "Updated First"
        assert s["version"] == "1.0.1"

    def test_update_section_missing(self, populated_doc):
        assert populated_doc.update_section("sec-999", title="Nope") is None

    def test_remove_section(self, populated_doc):
        before = populated_doc.meta["section_count"]
        assert populated_doc.remove_section("sec-I") is True
        assert populated_doc.meta["section_count"] == before - 1

    def test_remove_section_missing(self, populated_doc):
        assert populated_doc.remove_section("sec-999") is False

    def test_seal_document(self, populated_doc):
        seal = populated_doc.seal_document()
        assert seal["root_hash"]
        assert seal["sealed_at"]
        assert populated_doc.neuralbook["sealed"] is True
        assert len(seal["section_hashes"]) == 3

    def test_verify_integrity_valid(self, populated_doc):
        populated_doc.seal_document()
        ok, errors = populated_doc.verify_integrity()
        assert ok is True
        assert errors == []

    def test_verify_integrity_tampered(self, populated_doc):
        populated_doc.seal_document()
        populated_doc.content[0]["body"] = "TAMPERED"
        ok, errors = populated_doc.verify_integrity()
        assert ok is False
        assert any("Hash mismatch" in e for e in errors)

    def test_apply_patch_replace(self, populated_doc):
        populated_doc.seal_document()
        old_hash = populated_doc.seal["root_hash"]
        patch = {
            "neuralbook_patch": {
                "version": "1.0",
                "target_edition": "1.0.0",
                "patch_id": "p001",
                "created": "2026-01-01",
                "description": "test",
            },
            "operations": [{"op": "replace", "path": "/content/0/body", "value": "Patched body"}],
            "verification": {
                "previous_root_hash": old_hash,
                "new_root_hash": "",
                "sections_affected": ["sec-I"],
            },
        }
        ok, errors = populated_doc.apply_patch(patch)
        assert ok is True
        assert populated_doc.content[0]["body"] == "Patched body"

    def test_apply_patch_wrong_edition(self, populated_doc):
        patch = {
            "neuralbook_patch": {
                "version": "1.0",
                "target_edition": "9.9.9",
                "patch_id": "p002",
                "created": "2026-01-01",
                "description": "test",
            },
            "operations": [],
            "verification": {
                "previous_root_hash": "",
                "new_root_hash": "",
                "sections_affected": [],
            },
        }
        ok, errors = populated_doc.apply_patch(patch)
        assert ok is False

    def test_apply_patch_wrong_root_hash(self, populated_doc):
        patch = {
            "neuralbook_patch": {
                "version": "1.0",
                "target_edition": "",
                "patch_id": "p003",
                "created": "2026-01-01",
                "description": "test",
            },
            "operations": [],
            "verification": {
                "previous_root_hash": "badhash",
                "new_root_hash": "",
                "sections_affected": [],
            },
        }
        ok, errors = populated_doc.apply_patch(patch)
        assert ok is False

    def test_apply_patch_add_section(self, populated_doc):
        patch = {
            "neuralbook_patch": {
                "version": "1.0",
                "target_edition": "",
                "patch_id": "p004",
                "created": "2026-01-01",
                "description": "test",
            },
            "operations": [
                {
                    "op": "add",
                    "path": "/content/-",
                    "value": {
                        "id": "sec-III",
                        "type": "section",
                        "number": "III",
                        "title": "New",
                        "version": "1.0.0",
                        "body": "New section",
                    },
                }
            ],
            "verification": {
                "previous_root_hash": "",
                "new_root_hash": "",
                "sections_affected": ["sec-III"],
            },
        }
        ok, _ = populated_doc.apply_patch(patch)
        assert ok is True
        assert populated_doc.get_section("sec-III") is not None

    def test_apply_patch_remove_section(self, populated_doc):
        patch = {
            "neuralbook_patch": {
                "version": "1.0",
                "target_edition": "",
                "patch_id": "p005",
                "created": "2026-01-01",
                "description": "test",
            },
            "operations": [{"op": "remove", "path": "/content/0"}],
            "verification": {
                "previous_root_hash": "",
                "new_root_hash": "",
                "sections_affected": [],
            },
        }
        before = len(populated_doc.content)
        ok, _ = populated_doc.apply_patch(patch)
        assert ok is True
        assert len(populated_doc.content) == before - 1


# ── Serialization ────────────────────────────────────────────────────────


class TestSerialization:
    def test_to_dict_roundtrip(self, populated_doc):
        d = populated_doc.to_dict()
        doc2 = NeuralBookDocument.from_dict(d)
        assert doc2.meta["title"] == populated_doc.meta["title"]
        assert len(doc2.content) == len(populated_doc.content)

    def test_json_roundtrip(self, populated_doc):
        j = populated_doc.to_json()
        doc2 = NeuralBookDocument.from_json(j)
        assert doc2.meta["slug"] == populated_doc.meta["slug"]

    def test_file_roundtrip(self, populated_doc, tmp_path):
        fp = tmp_path / "test.nbook"
        populated_doc.write_file(fp)
        doc2 = NeuralBookDocument.from_file(fp)
        assert doc2.meta["section_count"] == populated_doc.meta["section_count"]


# ── TXT Import ────────────────────────────────────────────────────────────


class TestImportTxt:
    def test_import_structured(self, sample_txt):
        doc = import_txt(sample_txt, title="Sample", author="Test")
        assert doc.meta["title"] == "Sample"
        assert doc.meta["section_count"] == 3
        assert doc.get_section("sec-I")["title"] == "First Section"
        assert doc.get_section("part-I")["title"] == "First Part"

    def test_import_unstructured(self, tmp_path):
        p = tmp_path / "plain.txt"
        p.write_text("Just some text without headers", encoding="utf-8")
        doc = import_txt(p, title="Plain")
        assert doc.meta["section_count"] == 1

    def test_import_slug_derived(self, sample_txt):
        doc = import_txt(sample_txt, title="My Cool Book")
        assert doc.meta["slug"] == "my-cool-book"


# ── Validation ────────────────────────────────────────────────────────────


class TestValidation:
    def test_validate_structure_valid(self, populated_doc):
        result = validate_structure(populated_doc)
        assert result.ok

    def test_validate_structure_empty(self):
        doc = NeuralBookDocument()
        result = validate_structure(doc)
        assert not result.ok
        assert any("no content" in e for e in result.errors)

    def test_validate_structure_no_title(self):
        doc = NeuralBookDocument()
        doc.add_section("section", "I", "S", "Body")
        result = validate_structure(doc)
        assert any("title is empty" in w for w in result.warnings)

    def test_validate_integrity_valid(self, populated_doc):
        populated_doc.seal_document()
        result = validate_integrity(populated_doc)
        assert result.ok

    def test_validate_integrity_tampered(self, populated_doc):
        populated_doc.seal_document()
        populated_doc.content[0]["body"] = "TAMPERED"
        result = validate_integrity(populated_doc)
        assert not result.ok

    def test_validate_format_valid(self, populated_doc):
        result = validate_format(populated_doc)
        assert result.ok

    def test_validate_full(self, populated_doc):
        populated_doc.seal_document()
        result = validate_full(populated_doc)
        assert result.ok


# ── Helpers ───────────────────────────────────────────────────────────────


class TestHelpers:
    def test_section_hash_deterministic(self):
        s = {
            "id": "sec-I",
            "type": "section",
            "number": "I",
            "title": "T",
            "body": "B",
            "version": "1.0.0",
        }
        h1 = section_hash(s)
        h2 = section_hash(s)
        assert h1 == h2
        assert len(h1) == 64

    def test_section_hash_excludes_hash_field(self):
        s1 = {"id": "sec-I", "body": "B"}
        s2 = {"id": "sec-I", "body": "B", "hash": "shouldnotmatter"}
        assert section_hash(s1) == section_hash(s2)

    def test_root_hash_deterministic(self, populated_doc):
        h1 = root_hash(populated_doc.content)
        h2 = root_hash(populated_doc.content)
        assert h1 == h2

    def test_increment_patch(self):
        assert _increment_patch("1.0.0") == "1.0.1"
        assert _increment_patch("2.3.9") == "2.3.10"
        assert _increment_patch("bad") == "bad"

    def test_validation_result_equality(self):
        r1 = ValidationResult()
        r2 = ValidationResult()
        assert r1 == r2
        r1.error("fail")
        assert r1 != r2
