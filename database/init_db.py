"""
Database initialization and data migration CLI utility.
Creates all database tables, seeds categories, organizations, and migrates existing Excel records.
"""
from pathlib import Path
import sys
import logging

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from openpyxl import load_workbook
from config import EXCEL_FILE
from database.connection import check_connection, get_db
from database.models import Requirement, Category
from database.repository import init_database, save_requirement_to_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def migrate_from_excel_if_needed():
    """
    Imports historical records from data/requirements.xlsx into PostgreSQL
    under their respective categories if the database is newly initialized.
    """
    if not Path(EXCEL_FILE).exists():
        logger.info("No existing Excel file found at %s. Skipping migration.", EXCEL_FILE)
        return

    try:
        wb = load_workbook(EXCEL_FILE, data_only=True)
    except Exception as exc:
        logger.warning("Could not read Excel file for migration: %s", exc)
        return

    migrated_count = 0

    for sheet_name in ("Cook", "Driver", "Security Guard"):
        if sheet_name not in wb.sheetnames:
            continue

        ws = wb[sheet_name]
        headers = [cell.value for cell in ws[1]] if ws.max_row >= 1 else []
        if not headers or "Lead ID" not in headers:
            continue

        for row_idx in range(2, ws.max_row + 1):
            row_vals = [cell.value for cell in ws[row_idx]]
            if not any(row_vals):
                continue

            row_dict = {str(headers[i]): row_vals[i] for i in range(min(len(headers), len(row_vals)))}
            lead_id = row_dict.get("Lead ID")
            if not lead_id:
                continue

            try:
                # Check if already migrated
                with get_db() as db:
                    existing = db.query(Requirement).filter_by(lead_id=str(lead_id).strip()).first()
                    if existing:
                        continue

                save_requirement_to_db(sheet_name, row_dict)
                migrated_count += 1
            except Exception as exc:
                logger.warning("Failed migrating row %s from sheet %s: %s", lead_id, sheet_name, exc)

    logger.info("Excel migration completed. Migrated %d historical requirement(s) to PostgreSQL.", migrated_count)


def main():
    logger.info("Starting PostgreSQL database initialization...")
    is_healthy, msg = check_connection()
    if not is_healthy:
        logger.error("Database connection failed: %s", msg)
        return False

    success = init_database()
    if success:
        logger.info("Database schema tables created successfully.")
        migrate_from_excel_if_needed()
        logger.info("Database setup completed successfully.")
        return True
    else:
        logger.error("Failed to initialize database schema.")
        return False


if __name__ == "__main__":
    if not main():
        sys.exit(1)

