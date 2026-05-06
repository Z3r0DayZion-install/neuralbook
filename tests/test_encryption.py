"""Tests for NeuralBook encryption module."""

import pytest



def _key():
    from neuralbook.encryption import derive_key

    return derive_key("test-seed-abcdefghijklmnopqrstuvwxyz0123456789")


class TestDeriveKey:
    def test_deterministic(self):
        from neuralbook.encryption import derive_key

        assert derive_key("same-seed-abcdefghij1234567890abcdefghijkl") == derive_key(
            "same-seed-abcdefghij1234567890abcdefghijkl"
        )

    def test_32_bytes(self):
        from neuralbook.encryption import derive_key

        assert len(derive_key("any-seed-abcdefghijklmnopqrstuvwxyz12345")) == 32

    def test_str_and_bytes_equivalent(self):
        from neuralbook.encryption import derive_key

        seed = "seed-abcdefghijklmnopqrstuvwxyz123456"
        assert derive_key(seed) == derive_key(seed.encode())

    def test_different_seeds_different_keys(self):
        from neuralbook.encryption import derive_key

        k1 = derive_key("seed-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        k2 = derive_key("seed-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
        assert k1 != k2


class TestEncryptDecrypt:
    def test_round_trip(self):
        from neuralbook.encryption import decrypt_content, encrypt_content

        key = _key()
        pt = b"Hello NeuralBook"
        assert decrypt_content(encrypt_content(pt, key), key) == pt

    def test_unique_blobs_same_plaintext(self):
        from neuralbook.encryption import encrypt_content

        key = _key()
        pt = b"Same content"
        assert encrypt_content(pt, key) != encrypt_content(pt, key)

    def test_blob_format_size(self):
        from neuralbook.encryption import AUTH_TAG_LENGTH, IV_LENGTH, encrypt_content

        key = _key()
        pt = b"payload"
        blob = encrypt_content(pt, key)
        assert len(blob) == IV_LENGTH + AUTH_TAG_LENGTH + len(pt)

    def test_tamper_detection(self):
        from cryptography.exceptions import InvalidTag

        from neuralbook.encryption import decrypt_content, encrypt_content

        key = _key()
        blob = bytearray(encrypt_content(b"secret", key))
        blob[-1] ^= 0xFF  # corrupt last byte
        with pytest.raises((InvalidTag, Exception)):
            decrypt_content(bytes(blob), key)

    def test_short_blob_raises(self):
        from neuralbook.encryption import decrypt_content

        key = _key()
        with pytest.raises(ValueError, match="too short"):
            decrypt_content(b"tiny", key)

    def test_empty_plaintext(self):
        from neuralbook.encryption import decrypt_content, encrypt_content

        key = _key()
        assert decrypt_content(encrypt_content(b"", key), key) == b""

    def test_large_content(self):
        from neuralbook.encryption import decrypt_content, encrypt_content

        key = _key()
        pt = b"x" * 1_000_000
        assert decrypt_content(encrypt_content(pt, key), key) == pt


class TestEncryptFile:
    def test_file_round_trip(self, tmp_path):
        from neuralbook.encryption import decrypt_file, encrypt_file

        key = _key()
        src = tmp_path / "in.txt"
        enc = tmp_path / "in.txt.nd"
        dec = tmp_path / "out.txt"
        src.write_bytes(b"file content round trip")
        encrypt_file(src, enc, key)
        decrypt_file(enc, dec, key)
        assert dec.read_bytes() == src.read_bytes()

    def test_encrypted_size(self, tmp_path):
        from neuralbook.encryption import AUTH_TAG_LENGTH, IV_LENGTH, encrypt_file

        key = _key()
        src = tmp_path / "f.txt"
        enc = tmp_path / "f.nd"
        src.write_bytes(b"content")
        size = encrypt_file(src, enc, key)
        assert size == IV_LENGTH + AUTH_TAG_LENGTH + len(b"content")

    def test_creates_parent_dirs(self, tmp_path):
        from neuralbook.encryption import encrypt_file

        key = _key()
        src = tmp_path / "src.txt"
        enc = tmp_path / "deep" / "nested" / "out.nd"
        src.write_bytes(b"data")
        encrypt_file(src, enc, key)
        assert enc.exists()


class TestKeyDiscovery:
    def test_env_var(self, monkeypatch):
        from neuralbook.encryption import discover_key

        monkeypatch.setenv("NEURALBOOK_ENCRYPTION_SEED", "a" * 48)
        _, src = discover_key()
        assert src == "environment"

    def test_config_seed_demo(self, monkeypatch):
        from neuralbook.encryption import discover_key

        monkeypatch.delenv("NEURALBOOK_ENCRYPTION_SEED", raising=False)
        cfg = {"encryptionSeed": "b" * 48}
        _, src = discover_key(cfg, build_type="demo")
        assert src == "config"

    def test_config_seed_blocked_for_release(self, monkeypatch):
        from neuralbook.encryption import KeySourceError, discover_key

        monkeypatch.delenv("NEURALBOOK_ENCRYPTION_SEED", raising=False)
        cfg = {"encryptionSeed": "c" * 48}
        with pytest.raises(KeySourceError):
            discover_key(cfg, build_type="release")

    def test_no_seed_raises(self, monkeypatch):
        from neuralbook.encryption import KeySourceError, discover_key

        monkeypatch.delenv("NEURALBOOK_ENCRYPTION_SEED", raising=False)
        with pytest.raises(KeySourceError):
            discover_key({})

    def test_short_seed_raises(self, monkeypatch):
        from neuralbook.encryption import KeySourceError, discover_key

        monkeypatch.setenv("NEURALBOOK_ENCRYPTION_SEED", "tooshort")
        with pytest.raises(KeySourceError, match="too short"):
            discover_key()

    def test_weak_seed_raises(self, monkeypatch):
        from neuralbook.encryption import KeySourceError, discover_key

        monkeypatch.setenv("NEURALBOOK_ENCRYPTION_SEED", "password" + "x" * 40)
        with pytest.raises(KeySourceError, match="weak pattern"):
            discover_key()

    def test_seed_file(self, tmp_path, monkeypatch):
        from neuralbook.encryption import discover_key

        monkeypatch.delenv("NEURALBOOK_ENCRYPTION_SEED", raising=False)
        seed_file = tmp_path / "seed.txt"
        seed_file.write_text("z" * 64)
        cfg = {"encryptionSeedFile": "seed.txt"}
        _, src = discover_key(cfg, title_dir=tmp_path)
        assert src == "file:seed.txt"
