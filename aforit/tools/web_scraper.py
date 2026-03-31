"""Web scraping tool - fetch and parse web content."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlparse

from aforit.tools.base import BaseTool, ToolResult


class WebScraperTool(BaseTool):
    """Fetch and parse web pages."""

    name = "web_scraper"
    description = (
        "Fetch web pages and extract content. Can get raw HTML, extract text, "
        "find links, or parse specific elements using CSS selectors."
    )
    parameters = {
        "url": {
            "type": "string",
            "description": "URL to fetch",
        },
        "action": {
            "type": "string",
            "enum": ["fetch", "text", "links", "headers", "select"],
            "description": "What to extract from the page",
        },
        "selector": {
            "type": "string",
            "description": "CSS selector (for 'select' action)",
        },
        "timeout": {
            "type": "number",
            "description": "Request timeout in seconds",
        },
    }
    required_params = ["url"]
    timeout = 30.0

    async def execute(
        self,
        url: str,
        action: str = "text",
        selector: str = "",
        timeout: float = 15.0,
        **kwargs,
    ) -> ToolResult:
        """Fetch and process a web page."""
        try:
            import httpx
        except ImportError:
            return ToolResult(
                success=False, output="", error="httpx not installed"
            )

        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme:
            url = f"https://{url}"

        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; Aforit/1.0; +https://github.com/aforit)"
                },
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

            content = response.text
            content_type = response.headers.get("content-type", "")

            if action == "fetch":
                return ToolResult(
                    success=True,
                    output=content[:10000],
                    metadata={"status": response.status_code, "url": str(response.url)},
                )

            elif action == "text":
                text = self._html_to_text(content)
                return ToolResult(
                    success=True,
                    output=text[:8000],
                    metadata={"status": response.status_code, "chars": len(text)},
                )

            elif action == "links":
                links = self._extract_links(content, str(response.url))
                output = "\n".join(f"[{title}]({href})" for href, title in links[:50])
                return ToolResult(
                    success=True,
                    output=output,
                    metadata={"link_count": len(links)},
                )

            elif action == "headers":
                headers = dict(response.headers)
                output = "\n".join(f"{k}: {v}" for k, v in headers.items())
                return ToolResult(success=True, output=output)

            elif action == "select":
                if not selector:
                    return ToolResult(
                        success=False, output="", error="CSS selector required for 'select' action"
                    )
                selected = self._css_select(content, selector)
                return ToolResult(
                    success=True,
                    output="\n---\n".join(selected[:20]),
                    metadata={"matches": len(selected)},
                )

            else:
                return ToolResult(success=False, output="", error=f"Unknown action: {action}")

        except httpx.HTTPStatusError as e:
            return ToolResult(
                success=False, output="", error=f"HTTP {e.response.status_code}: {str(e)}"
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to readable text."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            # Remove script and style elements
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            # Clean up multiple newlines
            text = re.sub(r"\n{3,}", "\n\n", text)
            return text
        except ImportError:
            # Fallback: basic regex stripping
            text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text)
            return text.strip()

    def _extract_links(self, html: str, base_url: str) -> list[tuple[str, str]]:
        """Extract all links from HTML."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            links = []
            for a in soup.find_all("a", href=True):
                href = urljoin(base_url, a["href"])
                title = a.get_text(strip=True) or href
                links.append((href, title))
            return links
        except ImportError:
            # Fallback regex
            pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'
            matches = re.findall(pattern, html, re.DOTALL)
            return [
                (urljoin(base_url, href), re.sub(r"<[^>]+>", "", text).strip() or href)
                for href, text in matches
            ]

    def _css_select(self, html: str, selector: str) -> list[str]:
        """Select elements using CSS selectors."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            elements = soup.select(selector)
            return [el.get_text(strip=True) for el in elements]
        except ImportError:
            return ["beautifulsoup4 required for CSS selector support"]
