"""Web search tool - search the internet for information."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote_plus

from aforit.tools.base import BaseTool, ToolResult


class SearchTool(BaseTool):
    """Search the web for information."""

    name = "web_search"
    description = (
        "Search the web for information. Returns relevant results with titles, "
        "URLs, and snippets. Supports multiple search engines."
    )
    parameters = {
        "query": {
            "type": "string",
            "description": "Search query",
        },
        "num_results": {
            "type": "integer",
            "description": "Number of results to return (default: 5)",
        },
        "engine": {
            "type": "string",
            "enum": ["duckduckgo", "google", "bing"],
            "description": "Search engine to use",
        },
    }
    required_params = ["query"]
    timeout = 20.0

    async def execute(
        self,
        query: str,
        num_results: int = 5,
        engine: str = "duckduckgo",
        **kwargs,
    ) -> ToolResult:
        """Execute a web search."""
        try:
            if engine == "duckduckgo":
                return await self._search_duckduckgo(query, num_results)
            elif engine == "google":
                return await self._search_google(query, num_results)
            else:
                return await self._search_duckduckgo(query, num_results)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Search failed: {str(e)}")

    async def _search_duckduckgo(self, query: str, num_results: int) -> ToolResult:
        """Search using DuckDuckGo's HTML endpoint."""
        try:
            import httpx
        except ImportError:
            return ToolResult(success=False, output="", error="httpx not installed")

        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

        async with httpx.AsyncClient(
            timeout=15.0,
            headers={"User-Agent": "Mozilla/5.0 (compatible; Aforit/1.0)"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        results = self._parse_ddg_html(response.text, num_results)

        if not results:
            return ToolResult(
                success=True,
                output="No results found.",
                metadata={"query": query, "engine": "duckduckgo"},
            )

        output_lines = []
        for i, result in enumerate(results, 1):
            output_lines.append(
                f"{i}. {result['title']}\n"
                f"   URL: {result['url']}\n"
                f"   {result['snippet']}\n"
            )

        return ToolResult(
            success=True,
            output="\n".join(output_lines),
            metadata={"query": query, "engine": "duckduckgo", "count": len(results)},
        )

    async def _search_google(self, query: str, num_results: int) -> ToolResult:
        """Search using Google Custom Search API (requires API key)."""
        import os

        api_key = os.getenv("GOOGLE_API_KEY")
        cx = os.getenv("GOOGLE_SEARCH_CX")

        if not api_key or not cx:
            # Fall back to DuckDuckGo
            return await self._search_duckduckgo(query, num_results)

        try:
            import httpx
        except ImportError:
            return ToolResult(success=False, output="", error="httpx not installed")

        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": api_key,
            "cx": cx,
            "q": query,
            "num": min(num_results, 10),
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("items", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            })

        output_lines = []
        for i, result in enumerate(results, 1):
            output_lines.append(
                f"{i}. {result['title']}\n"
                f"   URL: {result['url']}\n"
                f"   {result['snippet']}\n"
            )

        return ToolResult(
            success=True,
            output="\n".join(output_lines),
            metadata={"query": query, "engine": "google", "count": len(results)},
        )

    def _parse_ddg_html(self, html: str, max_results: int) -> list[dict[str, str]]:
        """Parse DuckDuckGo HTML search results."""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            results = []

            for result_div in soup.select(".result"):
                title_el = result_div.select_one(".result__title a")
                snippet_el = result_div.select_one(".result__snippet")

                if title_el:
                    title = title_el.get_text(strip=True)
                    url = title_el.get("href", "")
                    snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                    results.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                    })

                    if len(results) >= max_results:
                        break

            return results

        except ImportError:
            import re
            results = []
            # Basic regex fallback
            pattern = r'class="result__title"[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>'
            matches = re.findall(pattern, html, re.DOTALL)
            for url, title in matches[:max_results]:
                results.append({
                    "title": re.sub(r"<[^>]+>", "", title).strip(),
                    "url": url,
                    "snippet": "",
                })
            return results
