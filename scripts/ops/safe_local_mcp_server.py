"""Small local MCP Streamable HTTP server for WNID validation.

This server intentionally exposes only one harmless tool (`ping`), one
read-only resource (`pa://safe-mcp/health`), and one static prompt
(`pa-safe-summary`). It performs no file, shell, network, credential, or
environment access.
"""

from __future__ import annotations

import argparse
import json
from typing import Any
from uuid import uuid4

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.responses import Response
from starlette.routing import Route
import uvicorn


PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "pa-safe-local-mcp", "version": "1.0.0"}
RESOURCE_URI = "pa://safe-mcp/health"
PROMPT_NAME = "pa-safe-summary"


async def mcp_endpoint(request: Request) -> Response:
    if request.method == "GET":
        return JSONResponse({"status": "ok", "server": SERVER_INFO})
    payload = await request.json()
    if isinstance(payload, list):
        results = [_handle_rpc(item) for item in payload if isinstance(item, dict)]
        return _json_rpc_response([item for item in results if item is not None])
    if not isinstance(payload, dict):
        return _json_rpc_response(_error_response(None, -32600, "Invalid Request"))
    result = _handle_rpc(payload)
    if result is None:
        return Response(status_code=202)
    return _json_rpc_response(result)


def _json_rpc_response(payload: Any) -> JSONResponse:
    return JSONResponse(
        payload,
        headers={
            "Mcp-Session-Id": "pa-safe-local-mcp",
            "MCP-Session-ID": "pa-safe-local-mcp",
        },
    )


def _handle_rpc(request: dict[str, Any]) -> dict[str, Any] | None:
    method = str(request.get("method") or "")
    request_id = request.get("id")
    if request_id is None:
        return None
    if method == "initialize":
        return _success_response(
            request_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                    "prompts": {"listChanged": False},
                },
                "serverInfo": SERVER_INFO,
            },
        )
    if method == "tools/list":
        return _success_response(
            request_id,
            {
                "tools": [
                    {
                        "name": "ping",
                        "description": "Returns a fixed health response for PA WNID MCP validation.",
                        "inputSchema": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "message": {
                                    "type": "string",
                                    "description": "Optional short message to echo in metadata.",
                                    "maxLength": 80,
                                }
                            },
                        },
                    }
                ]
            },
        )
    if method == "prompts/list":
        return _success_response(
            request_id,
            {
                "prompts": [
                    {
                        "name": PROMPT_NAME,
                        "description": "Static prompt for PA WNID MCP prompt parity validation.",
                    }
                ]
            },
        )
    if method == "prompts/get":
        params = request.get("params") if isinstance(request.get("params"), dict) else {}
        name = str(params.get("name") or "")
        if name != PROMPT_NAME:
            return _error_response(request_id, -32602, "Unknown prompt")
        return _success_response(
            request_id,
            {
                "description": "Static prompt for PA WNID MCP prompt parity validation.",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": "Summarize the safe local MCP validation status without using external data.",
                        },
                    }
                ],
            },
        )
    if method == "resources/list":
        return _success_response(
            request_id,
            {
                "resources": [
                    {
                        "uri": RESOURCE_URI,
                        "name": "PA safe MCP health",
                        "description": "Read-only local health resource for WNID MCP validation.",
                        "mimeType": "application/json",
                    }
                ]
            },
        )
    if method == "resources/read":
        return _success_response(
            request_id,
            {
                "contents": [
                    {
                        "uri": RESOURCE_URI,
                        "mimeType": "application/json",
                        "text": json.dumps(
                            {
                                "status": "ok",
                                "server": SERVER_INFO["name"],
                                "request_id": uuid4().hex[:8],
                            },
                            sort_keys=True,
                        ),
                    }
                ]
            },
        )
    if method == "tools/call":
        params = request.get("params") if isinstance(request.get("params"), dict) else {}
        name = str(params.get("name") or "")
        if name != "ping":
            return _error_response(request_id, -32602, "Unknown tool")
        return _success_response(
            request_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": "pa-safe-local-mcp pong",
                    }
                ],
                "isError": False,
            },
        )
    return _error_response(request_id, -32601, f"Method not found: {method}")


def _success_response(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error_response(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def create_app() -> Starlette:
    return Starlette(
        routes=[
            Route("/mcp", mcp_endpoint, methods=["GET", "POST"]),
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the PA safe local MCP server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    uvicorn.run(create_app(), host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
