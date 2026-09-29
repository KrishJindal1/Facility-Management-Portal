"""
Storage configuration re-exporting from root config.
Maintains backward compatibility with existing storage modules.
"""
from config import EXCEL_FILE

__all__ = ["EXCEL_FILE"]