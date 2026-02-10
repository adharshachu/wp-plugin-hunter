import os
import aiofiles
import json
import csv
from aiocsv import AsyncDictWriter
from typing import List
import logging
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound

logger = logging.getLogger(__name__)

async def save_results(results: List, filename: str, sheet_handler=None):
    fieldnames = ["domain", "is_wp", "plugins", "links", "error"]
    file_exists = os.path.isfile(filename)
    
    # Save to CSV as backup
    async with aiofiles.open(filename, mode="a", encoding="utf-8", newline="") as afp:
        writer = AsyncDictWriter(afp, fieldnames=fieldnames)
        if not file_exists:
            await writer.writeheader()
        
        for res in results:
            data = {
                "domain": res.domain,
                "is_wp": res.is_wp,
                "plugins": ",".join(res.plugins),
                "links": ",".join(res.links),
                "error": res.error or ""
            }
            await writer.writerow(data)
            
            # Live update Google Sheet if available
            if sheet_handler:
                sheet_handler.append_row(list(data.values()))

class GoogleSheetHandler:
    def __init__(self, json_keyfile: str, sheet_id: str):
        self.scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        self.creds = Credentials.from_service_account_file(json_keyfile, scopes=self.scope)
        self.client = gspread.authorize(self.creds)
        self.sheet_id = sheet_id
        self.sheet = None

    def create_tab(self, tab_name: str):
        try:
            # Check if tab exists, if not create it
            try:
                self.sheet = self.client.open_by_key(self.sheet_id).worksheet(tab_name)
                logger.info(f"Tab '{tab_name}' already exists. Using it.")
            except WorksheetNotFound:
                self.sheet = self.client.open_by_key(self.sheet_id).add_worksheet(title=tab_name, rows="1000", cols="20")
                logger.info(f"Created new tab: {tab_name}")
            
            # Add headers if empty
            if not self.sheet.get_all_values():
                headers = ["Domain", "Is WordPress", "Plugins", "Links", "Error"]
                self.sheet.append_row(headers)
        except Exception as e:
            logger.error(f"Failed to create/set tab {tab_name}: {e}")

    def append_row(self, row: List):
        try:
            self.sheet.append_row(row)
        except Exception as e:
            logger.error(f"Failed to update Google Sheet: {e}")

    def append_rows(self, rows: List[List]):
        if not rows:
            return
        try:
            self.sheet.append_rows(rows)
        except Exception as e:
            logger.error(f"Failed to batch update Google Sheet: {e}")

def load_domains(filename: str) -> List[str]:
    if not os.path.exists(filename):
        return []
    with open(filename, "r") as f:
        return [line.strip() for line in f if line.strip()]

_scanned_cache = set()

def is_already_scanned(domain: str) -> bool:
    global _scanned_cache
    if not _scanned_cache and os.path.exists("results.csv"):
        # Load from results file to populate cache once
        import csv
        try:
            with open("results.csv", "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    _scanned_cache.add(row["domain"])
        except:
            pass
    return domain in _scanned_cache
