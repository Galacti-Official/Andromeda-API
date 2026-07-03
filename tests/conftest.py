"""Provides dummy values for all required settings before any Andromeda module
is imported, so the test suite runs without a .env file (e.g. in CI). Real env
vars still win via setdefault."""
import os
import tempfile

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_PRIVATE_KEY", "test-private-key")
os.environ.setdefault("JWT_PUBLIC_KEY", "test-public-key")
os.environ.setdefault("USER_JWT_ISS", "https://api.test.invalid")
os.environ.setdefault("USER_JWT_AUD", "https://test.invalid")
os.environ.setdefault("PRODUCTION", "false")
os.environ.setdefault("BUILD", "test")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("AVATAR_DIR", os.path.join(tempfile.gettempdir(), "andromeda-test-avatars"))
