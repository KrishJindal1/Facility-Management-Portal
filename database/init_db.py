"""
Database initialization and data migration CLI utility.
Creates all database tables, seeds multi-tenant organizations, and migrates existing Excel records.
"""
from pathlib import Path
import logging
from openpyxl import load_workbook
from config import EXCEL_FILE
from database.connection import check_connection, get_db
from database.models import Organization
from database.repository import init_database, save_lead_to_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def migrate_from_excel_if_needed():
    """
    Imports historical records from data/requirements.xlsx into the database
    under the default tenant (homedesk) if the database is newly initialized.
    """
    if not Path(EXCEL_FILE).exists():
        logger.info("No existing Excel file found at %s. Skipping migration.", EXCEL_FILE)
        return

    try:
        wb = load_workbook(EXCEL_FILE, data_only=True)
    except Exception as exc:
        logger.warning("Could not read Excel file for migration: %s", exc)
        return

    homedesk_id = 1
    with get_db() as db:
        org = db.query(Organization).filter_by(slug="homedesk").first()
        if org:
            homedesk_id = org.id

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
                save_lead_to_db(sheet_name, row_dict, organization_id=homedesk_id)
                migrated_count += 1
            except Exception as exc:
                logger.warning("Failed migrating row %s from sheet %s: %s", lead_id, sheet_name, exc)

    logger.info("Excel migration completed. Migrated %d historical lead(s) for tenant %s.", migrated_count, homedesk_id)


def main():
    logger.info("Starting multi-tenant database initialization...")
    is_healthy, msg = check_connection()
    if not is_healthy:
        logger.error("Database connection failed: %s", msg)
        return False

    success = init_database()
    if success:
        logger.info("Database schema tables created successfully.")
        migrate_from_excel_if_needed()
        logger.info("Multi-tenant database setup completed successfully.")
        return True
    else:
        logger.error("Failed to initialize database schema.")
        return False


if __name__ == "__main__":
    main()
