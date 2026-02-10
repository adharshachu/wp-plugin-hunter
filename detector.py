import aiohttp
import logging
import re
from typing import Tuple, List

logger = logging.getLogger(__name__)

class WPDetector:
    async def detect(self, session: aiohttp.ClientSession, domain: str) -> Tuple[bool, List[str]]:
        url = f"http://{domain}" if not domain.startswith("http") else domain
        links = []
        try:
            # Check for common WP indicators in headers and response body
            async with session.get(url, allow_redirects=True, timeout=5) as response:
                if response.status != 200:
                    return False, []
                
                # Check Headers
                headers = response.headers
                if "X-Powered-By" in headers and "PHP" in headers["X-Powered-By"]:
                    pass # Strong hint but not definitive
                
                text = await response.text()
                
                # Specifically look for and extract ALL links for target plugin paths
                target_plugins = [
                    "brand-management-plugin",
                    "cryptopresales-brand-management-plugin",
                ]
                pattern = rf'["\']([^"\']*?/wp-content/plugins/(?:{"|".join(map(re.escape, target_plugins))})/[^"\']*?)["\']'
                matches = re.findall(pattern, text)
                
                if matches:
                    logger.info(
                        f"Found {len(matches)} direct URL matches for target plugins in {domain}"
                    )
                    for match in matches:
                        if not match.startswith("http"):
                            # Handle relative paths
                            full_url = f"{url.rstrip('/')}/{match.lstrip('/')}"
                            links.append(full_url)
                        else:
                            links.append(match)
                    return True, links

                indicators = [
                    "/wp-content/",
                    "/wp-includes/",
                    "wp-emoji-release.min.js",
                    "wp-embed.min.js"
                ]
                
                found_indicators = [ind for ind in indicators if ind in text]
                if found_indicators:
                    # It is WordPress, but we don't have the specific plugin links yet
                    # We return True for is_wp but keep links empty unless the regex found something
                    return True, links
                
                # Secondary check: /wp-login.php (Head request)
                async with session.head(f"{url}/wp-login.php", timeout=3) as wp_check:
                    if wp_check.status == 200:
                        return True, links
                        
            return False, []
        except Exception as e:
            logger.debug(f"WP detection failed for {domain}: {e}")
            return False, []
