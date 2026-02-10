import aiohttp
import asyncio
from typing import List, Tuple

class PluginProber:
    # Target plugins specified by user (no version suffix)
    TARGET_PLUGIN_PATHS = [
        "brand-management-plugin",
        "cryptopresales-brand-management-plugin",
    ]
    
    # Only probe the explicitly targeted plugins; remove broad/common scanning.
    COMMON_PLUGINS = [*TARGET_PLUGIN_PATHS]

    async def probe(self, session: aiohttp.ClientSession, domain: str) -> List[Tuple[str, List[str]]]:
        base_url = f"http://{domain}" if not domain.startswith("http") else domain
        base_url = base_url.rstrip("/")
        
        detected = []
        
        # To avoid massive requests per domain, we just check a few common ones
        tasks = [self.check_plugin(session, base_url, plugin) for plugin in self.COMMON_PLUGINS]
        results = await asyncio.gather(*tasks)
        
        for plugin, is_present, links in results:
            if is_present:
                detected.append((plugin, links))
        
        return detected

    async def check_plugin(self, session: aiohttp.ClientSession, base_url: str, plugin_name: str) -> Tuple[str, bool, List[str]]:
        # Specific check for the target plugins (directory + common public files)
        if plugin_name in self.TARGET_PLUGIN_PATHS:
            # We check the directory and common public files
            targets = [
                f"{base_url}/wp-content/plugins/{plugin_name}/",
                f"{base_url}/wp-content/plugins/{plugin_name}/readme.txt"
            ]
            found_links = []
            for target in targets:
                try:
                    async with session.head(target, timeout=3) as resp:
                        if resp.status in [200, 403]:
                            found_links.append(target)
                except:
                    continue
            
            if found_links:
                return plugin_name, True, found_links
            return plugin_name, False, []

        # General check for other common plugins
        plugin_url = f"{base_url}/wp-content/plugins/{plugin_name}/readme.txt"
        try:
            async with session.head(plugin_url, timeout=3) as resp:
                if resp.status in [200, 403]: # 403 often means it exists but forbidden
                    return plugin_name, True, [plugin_url]
        except:
            pass
        return plugin_name, False, []
