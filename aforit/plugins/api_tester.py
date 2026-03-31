"""API Tester plugin - test HTTP endpoints."""

from __future__ import annotations

import json
import time
from typing import Any
from urllib.parse import urljoin

from aforit.core.registry import ToolRegistry
from aforit.plugins.loader import PluginBase
from aforit.tools.base import BaseTool, ToolResult


class ApiTesterTool(BaseTool):
    """HTTP API testing tool."""

    name = "api_test"
    description = (
        "Test HTTP API endpoints. Send GET, POST, PUT, PATCH, DELETE requests "
        "with custom headers, body, and authentication. Shows response status, "
        "headers, body, and timing."
    )
    parameters = {
        "method": {
            "type": "string",
            "enum": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
            "description": "HTTP method",
        },
        "url": {
            "type": "string",
            "description": "Request URL",
        },
        "headers": {
            "type": "object",
            "description": "Request headers as key-value pairs",
        },
        "body": {
            "type": "string",
            "description": "Request body (JSON string)",
        },
        "auth_type": {
            "type": "string",
            "enum": ["none", "bearer", "basic"],
            "description": "Authentication type",
        },
        "auth_token": {
            "type": "string",
            "description": "Authentication token or credentials",
        },
        "timeout": {
            "type": "number",
            "description": "Request timeout in seconds",
        },
    }
    required_params = ["method", "url"]
    timeout = 30.0

    async def execute(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: str = "",
        auth_type: str = "none",
        auth_token: str = "",
        timeout: float = 15.0,
        **kwargs,
    ) -> ToolResult:
        """Send an HTTP request and return the response."""
        try:
            import httpx
        except ImportError:
            return ToolResult(success=False, output="", error="httpx not installed")

        # Build headers
        request_headers = headers or {}
        if auth_type == "bearer" and auth_token:
            request_headers["Authorization"] = f"Bearer {auth_token}"
        elif auth_type == "basic" and auth_token:
            import base64
            encoded = base64.b64encode(auth_token.encode()).decode()
            request_headers["Authorization"] = f"Basic {encoded}"

        # Parse body
        request_body = None
        if body:
            try:
                request_body = json.loads(body)
                if "Content-Type" not in request_headers:
                    request_headers["Content-Type"] = "application/json"
            except json.JSONDecodeError:
                request_body = body

        try:
            start_time = time.time()

            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    headers=request_headers,
                    json=request_body if isinstance(request_body, (dict, list)) else None,
                    content=request_body if isinstance(request_body, str) else None,
                )

            elapsed = time.time() - start_time

            # Format output
            output_parts = [
                f"Status: {response.status_code} {response.reason_phrase}",
                f"Time: {elapsed:.3f}s",
                f"Size: {len(response.content)} bytes",
                "",
                "Response Headers:",
            ]

            for key, value in response.headers.items():
                output_parts.append(f"  {key}: {value}")

            output_parts.append("")
            output_parts.append("Response Body:")

            # Try to format JSON response
            try:
                response_json = response.json()
                output_parts.append(json.dumps(response_json, indent=2)[:5000])
            except (json.JSONDecodeError, ValueError):
                output_parts.append(response.text[:5000])

            return ToolResult(
                success=200 <= response.status_code < 400,
                output="\n".join(output_parts),
                metadata={
                    "status_code": response.status_code,
                    "elapsed": elapsed,
                    "content_type": response.headers.get("content-type", ""),
                },
            )

        except httpx.TimeoutException:
            return ToolResult(
                success=False, output="", error=f"Request timed out after {timeout}s"
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class ApiTesterPlugin(PluginBase):
    """Plugin that adds API testing tools."""

    name = "api_tester"
    version = "1.0.0"
    description = "HTTP API testing and endpoint exploration"

    def on_load(self, registry: ToolRegistry):
        registry.register(ApiTesterTool())
