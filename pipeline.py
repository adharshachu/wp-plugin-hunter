import asyncio
import logging
from typing import List, Set
from pydantic import BaseModel
import aiohttp
from detector import WPDetector
from prober import PluginProber
from intel_passive import PassiveIntel
from utils import save_results, load_domains, is_already_scanned, GoogleSheetHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ScanResult(BaseModel):
    domain: str
    is_wp: bool = False
    plugins: List[str] = []
    links: List[str] = []
    error: str = None

class Pipeline:
    def __init__(self, concurrency: int = 100, sheet_handler: GoogleSheetHandler = None):
        self.semaphore = asyncio.Semaphore(concurrency)
        self.results: List[ScanResult] = []
        self.detector = WPDetector()
        self.prober = PluginProber()
        self.intel = PassiveIntel()
        self.sheet_handler = sheet_handler
        self.output_buffer = []
        self.buffer_lock = asyncio.Lock()
        self.batch_size = 250
        self.status_lock = asyncio.Lock()
        self.processed_count = 0
        self.total_count = 0
        self.total_searched = 0
        self.progress_callback = None

    def set_progress_callback(self, callback):
        self.progress_callback = callback

    async def process_domain(self, session: aiohttp.ClientSession, domain: str):
        if is_already_scanned(domain):
            logger.info(f"Skipping {domain} (already scanned)")
            return

        async with self.semaphore:
            result = ScanResult(domain=domain)
            try:
                # 1. WP Detection (Cheap Filter)
                is_wp, detector_links = await self.detector.detect(session, domain)
                result.is_wp = is_wp
                result.links.extend(detector_links)

                if is_wp:
                    # 2. Plugin Probing (Direct Path Check)
                    plugin_info = await self.prober.probe(session, domain)
                    for plugin, links in plugin_info:
                        result.plugins.append(plugin)
                        result.links.extend(links)
                    
                    # 3. Passive Intelligence
                    passive_plugins = await self.intel.get_passive_plugins(session, domain)
                    
                    # 4. Normalize + Deduplicate
                    result.plugins = list(set(result.plugins + passive_plugins))
                    result.links = list(set(result.links))
                
                self.results.append(result)
                logger.info(f"Processed {domain}: WP={result.is_wp}, Plugins={len(result.plugins)}")
                
                # Update total counter and check for periodic flush (every 1000 domains)
                if self.sheet_handler:
                    async with self.status_lock:
                        self.total_searched += 1
                        if self.total_searched % 1000 == 0:
                            async with self.buffer_lock:
                                if self.output_buffer:
                                    logger.info(f"Periodic flush: Pushing {len(self.output_buffer)} hits to Google Sheets at domain {self.total_searched}...")
                                    loop = asyncio.get_event_loop()
                                    await loop.run_in_executor(None, self.sheet_handler.append_rows, self.output_buffer.copy())
                                    self.output_buffer.clear()

                # Buffer for Google Sheet live update - ONLY IF PLUGIN IS DETECTED
                if self.sheet_handler and result.plugins:
                    async with self.buffer_lock:
                        data = [
                            result.domain,
                            str(result.is_wp),
                            ",".join(result.plugins),
                            ",".join(result.links),
                            result.error or ""
                        ]
                        self.output_buffer.append(data)
                        
                        if len(self.output_buffer) >= self.batch_size:
                            logger.info(f"Buffer full: Pushing {len(self.output_buffer)} hits to Google Sheets...")
                            # Run synchronous gspread call in a thread to avoid blocking event loop
                            loop = asyncio.get_event_loop()
                            await loop.run_in_executor(None, self.sheet_handler.append_rows, self.output_buffer.copy())
                            self.output_buffer.clear()
            except Exception as e:
                result.error = str(e)
                self.results.append(result)
                logger.error(f"Error processing {domain}: {e}")
            finally:
                async with self.status_lock:
                    self.processed_count += 1
                    if self.progress_callback:
                        await self.progress_callback(self.processed_count, self.total_count)

    async def run(self, domains: List[str]):
        self.total_count = len(domains)
        self.processed_count = 0
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            tasks = [self.process_domain(session, domain) for domain in domains]
            await asyncio.gather(*tasks)
        
        await save_results(self.results, "results.csv")
        
        # Final flush for Google Sheet buffer
        if self.sheet_handler and self.output_buffer:
            logger.info(f"Flushing final {len(self.output_buffer)} results to Google Sheets...")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.sheet_handler.append_rows, self.output_buffer.copy())
            self.output_buffer.clear()

        logger.info(f"Final results saved. Total: {len(self.results)}")

if __name__ == "__main__":
    import sys
    import os
    from dotenv import load_dotenv
    load_dotenv()

    domains_to_scan = load_domains("domains.txt") if len(sys.argv) < 2 else sys.argv[1:]
    if not domains_to_scan:
        logger.warning("No domains to scan. Please provide domains in domains.txt or as arguments.")
        sys.exit(0)
    
    # Google Sheets Setup
    sheet_handler = None
    json_keyfile = os.getenv("GOOGLE_SHEETS_JSON")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    
    if json_keyfile and sheet_id:
        try:
            sheet_handler = GoogleSheetHandler(json_keyfile, sheet_id)
            logger.info("Google Sheets handler initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets: {e}")
    
    pipeline = Pipeline(concurrency=50, sheet_handler=sheet_handler)
    if sheet_handler:
        sheet_handler.create_tab("Scan Results")
    asyncio.run(pipeline.run(domains_to_scan))
