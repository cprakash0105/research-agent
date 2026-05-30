import os
import pytest
from app.security import generate_key, encrypt_secrets, load_secrets, KEY_FILE, SECRETS_FILE


@pytest.fixture(autouse=True)
def clean_secret_files():
    """Remove secret files before and after each test."""
    for f in [KEY_FILE, SECRETS_FILE]:
        if os.path.exists(f):
            os.remove(f)
    yield
    for f in [KEY_FILE, SECRETS_FILE]:
        if os.path.exists(f):
            os.remove(f)


class TestSecretEncryption:
    """Test secret encryption and decryption."""

    def test_generate_key_creates_file(self):
        key = generate_key()
        assert os.path.exists(KEY_FILE)
        assert len(key) > 0

    def test_encrypt_and_decrypt(self):
        secrets = {"GOOGLE_API_KEY": "test-key-123", "TAVILY_API_KEY": "tavily-456"}
        encrypt_secrets(secrets)
        assert os.path.exists(SECRETS_FILE)

        loaded = load_secrets()
        assert loaded["GOOGLE_API_KEY"] == "test-key-123"
        assert loaded["TAVILY_API_KEY"] == "tavily-456"

    def test_load_secrets_fallback_to_env(self):
        # No encrypted files exist, should fall back to env
        os.environ["GOOGLE_API_KEY"] = "env-key"
        os.environ["TAVILY_API_KEY"] = "env-tavily"
        loaded = load_secrets()
        assert loaded["GOOGLE_API_KEY"] == "env-key"
        assert loaded["TAVILY_API_KEY"] == "env-tavily"

    def test_encrypt_overwrites_existing(self):
        encrypt_secrets({"GOOGLE_API_KEY": "first"})
        encrypt_secrets({"GOOGLE_API_KEY": "second"})
        loaded = load_secrets()
        assert loaded["GOOGLE_API_KEY"] == "second"
