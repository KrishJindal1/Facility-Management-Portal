"""
Database connection and session management module.
Provides connection pooling, dialect normalization, and safe session lifecycle helpers.
"""
from contextlib import contextmanager
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL

logger = logging.getLogger(__name__)


from urllib.parse import quote_plus, unquote


def _normalize_database_url(url: str) -> str:
    """
    Normalizes PostgreSQL URL schemes for SQLAlchemy compatibility.
    Strips accidental surrounding quotes, whitespace, and variable name prefixes.
    Automatically encodes special characters in passwords if unencoded.
    Replaces deprecated 'postgres://' or bare 'postgresql://' with psycopg2 driver scheme.
    """
    if not url:
        return ""
    url = url.strip()
    # Strip any accidental wrapping quotes: "..." or '...'
    if (url.startswith('"') and url.endswith('"')) or (url.startswith("'") and url.endswith("'")):
        url = url[1:-1].strip()
    # Strip accidental "DATABASE_URL=" or "DATABASE_URL = " prefix
    if url.startswith("DATABASE_URL"):
        url = url.split("=", 1)[-1].strip()
        if (url.startswith('"') and url.endswith('"')) or (url.startswith("'") and url.endswith("'")):
            url = url[1:-1].strip()

    if not url:
        return ""

    # Auto-encode special characters in password if raw special chars are present
    if "://" in url and "@" in url:
        scheme, rest = url.split("://", 1)
        creds, host_and_path = rest.rsplit("@", 1)
        if ":" in creds:
            username, password = creds.split(":", 1)
            # unquote first in case partially encoded, then quote_plus
            clean_pwd = quote_plus(unquote(password))
            url = f"{scheme}://{username}:{clean_pwd}@{host_and_path}"

    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


NORMALIZED_DATABASE_URL = _normalize_database_url(DATABASE_URL)

# Fallback to local SQLite if DATABASE_URL is empty or missing
if not NORMALIZED_DATABASE_URL:
    from config import BASE_DIR
    NORMALIZED_DATABASE_URL = f"sqlite:///{(BASE_DIR / 'data' / 'facility_management.db').resolve()}"
    logger.warning("DATABASE_URL is empty or invalid. Falling back to local database: %s", NORMALIZED_DATABASE_URL)

# Configure engine arguments based on database backend
engine_kwargs = {"pool_pre_ping": True}

if NORMALIZED_DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_recycle"] = 1800

try:
    engine = create_engine(NORMALIZED_DATABASE_URL, **engine_kwargs)
except Exception as exc:
    logger.error("Failed to initialize database engine for URL: %s", exc)
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

_DEFAULT_ENGINE = engine
_DEFAULT_SESSIONLOCAL = SessionLocal
_DEFAULT_URL = NORMALIZED_DATABASE_URL


def configure_test_database(test_url: str = None):
    """
    Switches connection engine to an isolated test database (e.g. temporary SQLite file)
    to guarantee production database is never modified by automated test runs.
    """
    global engine, SessionLocal, NORMALIZED_DATABASE_URL
    from config import BASE_DIR
    if not test_url:
        test_url = f"sqlite:///{(BASE_DIR / 'data' / 'test_isolated.db').resolve()}"
    NORMALIZED_DATABASE_URL = test_url
    engine = create_engine(NORMALIZED_DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return engine


def reset_database_to_default():
    """Restores database engine and sessionmaker to original production/default settings."""
    global engine, SessionLocal, NORMALIZED_DATABASE_URL
    engine = _DEFAULT_ENGINE
    SessionLocal = _DEFAULT_SESSIONLOCAL
    NORMALIZED_DATABASE_URL = _DEFAULT_URL


@contextmanager
def get_db():
    """
    Context manager for database sessions.
    Automatically commits on success, rolls back on exception, and closes session.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Database transaction rolled back due to error: %s", exc)
        raise
    finally:
        db.close()


def check_connection() -> tuple[bool, str]:
    """
    Checks if the database is reachable by executing a simple query.
    Returns:
        (True, "OK") if healthy,
        (False, error_message) if connection failed.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Database connection is healthy."
    except Exception as exc:
        msg = f"Database connection failed: {str(exc)}"
        logger.warning(msg)
        return False, msg
