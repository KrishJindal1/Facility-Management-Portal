"""
Production Health & Readiness Check Utility.
Verifies runtime environment, database connectivity, table schema,
and AI provider configuration.

Usage:
    python healthcheck.py
    python healthcheck.py --json
"""
import sys
import json
import logging
from pathlib import Path

# Configure minimal stdout logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("healthcheck")


def run_health_check() -> dict:
    """
    Executes core diagnostic checks and returns status results.
    """
    report = {
        "status": "healthy",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "checks": {},
    }

    # 1. Python Version Check (must be >= 3.11)
    if sys.version_info < (3, 11):
        report["checks"]["python"] = {
            "status": "warning",
            "message": f"Python version is {report['python_version']}, expected >= 3.11",
        }
    else:
        report["checks"]["python"] = {
            "status": "ok",
            "message": f"Python {report['python_version']} is compatible",
        }

    # 2. Database Connection Check
    try:
        from database.connection import check_connection, get_db
        from database.models import Organization
        from database.repository import init_database

        is_connected, msg = check_connection()
        if not is_connected:
            report["status"] = "unhealthy"
            report["checks"]["database_connection"] = {
                "status": "failed",
                "message": msg,
            }
        else:
            report["checks"]["database_connection"] = {
                "status": "ok",
                "message": "Database connection verified",
            }

            # Check schema readiness
            try:
                with get_db() as db:
                    org_count = db.query(Organization).count()
                    report["checks"]["database_schema"] = {
                        "status": "ok",
                        "message": f"Schema initialized with {org_count} organization(s)",
                    }
            except Exception as schema_err:
                # Attempt to initialize schema
                logger.warning("Tables missing. Attempting self-initialization: %s", schema_err)
                if init_database():
                    report["checks"]["database_schema"] = {
                        "status": "ok",
                        "message": "Schema initialized successfully on check",
                    }
                else:
                    report["status"] = "degraded"
                    report["checks"]["database_schema"] = {
                        "status": "failed",
                        "message": f"Failed to initialize schema: {schema_err}",
                    }
    except Exception as exc:
        report["status"] = "unhealthy"
        report["checks"]["database"] = {
            "status": "failed",
            "message": f"Database initialization failed: {exc}",
        }

    # 3. AI Provider Configuration Check
    try:
        from config import AI_PROVIDER
        from ai.providers.factory import get_ai_provider

        provider = get_ai_provider(AI_PROVIDER)
        is_configured, ai_msg = provider.is_configured()
        report["checks"]["ai_provider"] = {
            "provider": AI_PROVIDER,
            "status": "ok" if is_configured else "warning",
            "message": ai_msg,
        }
    except Exception as ai_err:
        report["checks"]["ai_provider"] = {
            "status": "warning",
            "message": f"AI provider check failed: {ai_err}",
        }

    # 4. Storage & Export Directory Check
    try:
        from config import EXCEL_FILE
        excel_path = Path(EXCEL_FILE)
        parent_dir = excel_path.parent
        parent_dir.mkdir(parents=True, exist_ok=True)
        report["checks"]["storage"] = {
            "status": "ok",
            "directory": str(parent_dir),
            "writable": parent_dir.is_dir(),
        }
    except Exception as stor_err:
        report["checks"]["storage"] = {
            "status": "warning",
            "message": f"Storage directory check failed: {stor_err}",
        }

    return report


def main():
    report = run_health_check()
    as_json = "--json" in sys.argv

    if as_json:
        print(json.dumps(report, indent=2))
    else:
        print("=" * 60)
        print(f" HomeDesk System Health Check: {report['status'].upper()} ")
        print("=" * 60)
        print(f"Python:   {report['checks'].get('python', {}).get('message', 'N/A')}")
        print(f"Database: {report['checks'].get('database_connection', {}).get('message', 'N/A')}")
        print(f"Schema:   {report['checks'].get('database_schema', {}).get('message', 'N/A')}")
        ai_info = report["checks"].get("ai_provider", {})
        print(f"AI ({ai_info.get('provider', 'N/A')}): {ai_info.get('message', 'N/A')}")
        print(f"Storage:  {report['checks'].get('storage', {}).get('status', 'N/A')}")
        print("=" * 60)

    if report["status"] == "unhealthy":
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
