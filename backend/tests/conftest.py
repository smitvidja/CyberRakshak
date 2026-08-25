import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://cyberrakshak:cyberrakshak_local_only@localhost:5432/cyberrakshak",
)
os.environ.setdefault(
    "SECRET_KEY",
    "test-only-secret-key-that-is-long-enough-for-session-three",
)
