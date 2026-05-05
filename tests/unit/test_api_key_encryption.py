import pytest
from app.utils.encryption import encrypt_value, decrypt_value, mask_key


class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        plaintext = "sk-test-abc123secretkey456"
        encrypted = encrypt_value(plaintext)
        decrypted = decrypt_value(encrypted)
        assert decrypted == plaintext

    def test_encrypted_differs_from_plaintext(self):
        plaintext = "secret-key-123"
        encrypted = encrypt_value(plaintext)
        assert encrypted != plaintext
        assert plaintext not in encrypted

    def test_each_encryption_produces_different_ciphertext(self):
        plaintext = "same-plaintext"
        enc1 = encrypt_value(plaintext)
        enc2 = encrypt_value(plaintext)
        assert enc1 != enc2

    def test_decrypt_invalid_ciphertext_raises_error(self):
        with pytest.raises(Exception):
            decrypt_value("not-valid-base64!!!")

    def test_encrypt_empty_string(self):
        encrypted = encrypt_value("")
        decrypted = decrypt_value(encrypted)
        assert decrypted == ""


class TestMaskKey:
    def test_mask_long_key(self):
        key = "sk-proj-abc123def456ghi789"
        masked = mask_key(key)
        assert masked.endswith("i789")
        assert "*" in masked
        assert "abc123" not in masked

    def test_mask_short_key(self):
        key = "abc"
        masked = mask_key(key)
        assert masked == "abc"  # Short keys shown in full

    def test_mask_exactly_4_chars(self):
        key = "abcd"
        masked = mask_key(key)
        assert masked == "abcd"

    def test_mask_5_chars(self):
        key = "abcde"
        masked = mask_key(key)
        assert masked == "*bcde"
