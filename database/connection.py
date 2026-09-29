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


def _normalize_database_url(url: str) -> str:
    """
    Normalizes PostgreSQL URL schemes for SQLAlchemy compatibility.
    Strips accidental surrounding quotes, whitespace, and variable name prefixes.
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

    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


NORMALIZED_DATABASE_URL = _normalize_database_url(DATABASE_URL)

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
    logger.error("Failed to initialize database engine: %s", exc)
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


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
