import os

os.environ.setdefault("DATABASE_HOST", "localhost")
os.environ.setdefault("DATABASE_PORT", "5432")
os.environ.setdefault("DATABASE_NAME", "claimguard")
os.environ.setdefault("DATABASE_USER", "claimguard")
os.environ.setdefault("DATABASE_PASSWORD", "change-me")
os.environ.setdefault("POLICY_BASE_URL", "http://policy.test")
os.environ.setdefault("POLICY_HTTP_TIMEOUT_SECONDS", "3")
