import os
import json
import logging
from pathlib import Path
from cryptography.fernet import Fernet

logger = logging.getLogger("research-agent.security")

SECRETS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "secrets.enc")
KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "secrets.key")


def generate_key():
    """Generate a new encryption key and save to file."""
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    logger.info(f"Encryption key generated: {KEY_FILE}")
    return key


def encrypt_secrets(secrets: dict):
    """Encrypt a dict of secrets and save to file."""
    if not os.path.exists(KEY_FILE):
        key = generate_key()
    else:
        with open(KEY_FILE, "rb") as f:
            key = f.read()

    fernet = Fernet(key)
    encrypted = fernet.encrypt(json.dumps(secrets).encode())

    with open(SECRETS_FILE, "wb") as f:
        f.write(encrypted)
    logger.info("Secrets encrypted and saved")


def load_secrets() -> dict:
    """Load and decrypt secrets. Falls back to .env if no encrypted file exists."""
    if not os.path.exists(SECRETS_FILE) or not os.path.exists(KEY_FILE):
        logger.info("No encrypted secrets found, using .env variables")
        return {
            "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY", ""),
            "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", ""),
        }

    try:
        with open(KEY_FILE, "rb") as f:
            key = f.read()
        with open(SECRETS_FILE, "rb") as f:
            encrypted = f.read()

        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted)
        secrets = json.loads(decrypted.decode())
        logger.info("Secrets loaded from encrypted store")
        return secrets
    except Exception as e:
        logger.error(f"Failed to load encrypted secrets: {e}", exc_info=True)
        logger.info("Falling back to .env variables")
        return {
            "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY", ""),
            "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", ""),
        }


def init_secrets():
    """Initialize secrets into environment from encrypted store or .env."""
    secrets = load_secrets()
    for key, value in secrets.items():
        if value and not os.getenv(key):
            os.environ[key] = value
    logger.info("Secrets initialized into environment")
