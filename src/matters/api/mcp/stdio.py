"""Dependency-free stdio transport for the in-process Matters MCP adapter."""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from matters import runtime
from matters._version import VERSION
from matters.api.mcp.server import MattersMCP


SUPPORTED_PROTOCOL_VERSIONS = (
    "2025-06-18",
    "2025-11-25",
)


def _error(
    request_id: object,
    code: int,
    message: str,
    *,
    data: object | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }
    if data is not None:
        payload["error"]["data"] = data
    return payload


def _result(request_id: object, result: object) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


class MattersMCPStdioServer:
    """Minimal MCP lifecycle/tools transport with no stdout logging."""

    def __init__(self, adapter: MattersMCP) -> None:
        self.adapter = adapter
        self.initialized = False

    def handle(self, request: object) -> dict[str, Any] | None:
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
            return _error(
                request.get("id") if isinstance(request, dict) else None,
                -32600,
                "Invalid Request",
            )
        method = request.get("method")
        request_id = request.get("id")
        params = request.get("params", {})
        if not isinstance(method, str) or (
            params is not None and not isinstance(params, dict)
        ):
            return _error(request_id, -32600, "Invalid Request")

        if method == "initialize":
            requested = str((params or {}).get("protocolVersion", ""))
            protocol = (
                requested
                if requested in SUPPORTED_PROTOCOL_VERSIONS
                else SUPPORTED_PROTOCOL_VERSIONS[-1]
            )
            return _result(
                request_id,
                {
                    "protocolVersion": protocol,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "matters", "version": VERSION},
                    "instructions": (
                        "Use the bounded Matters model map and situation context. "
                        "Preserve modality and visible gaps; never infer canonical "
                        "writes from advisory feedback."
                    ),
                },
            )
        if method == "notifications/initialized":
            self.initialized = True
            return None
        if method.startswith("notifications/"):
            return None
        if method == "ping":
            return _result(request_id, {})
        if not self.initialized:
            return _error(request_id, -32002, "Server not initialized")
        if method == "tools/list":
            return _result(
                request_id,
                {"tools": list(self.adapter.list_tools())},
            )
        if method == "tools/call":
            name = (params or {}).get("name")
            arguments = (params or {}).get("arguments", {})
            if not isinstance(name, str) or not isinstance(arguments, dict):
                return _error(request_id, -32602, "Invalid params")
            response = self.adapter.call_tool(name, arguments)
            serialized = json.dumps(
                response,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            return _result(
                request_id,
                {
                    "content": [{"type": "text", "text": serialized}],
                    "structuredContent": response,
                    "isError": not bool(response.get("ok", False)),
                },
            )
        return _error(request_id, -32601, "Method not found")

    def serve(self, reader: TextIO, writer: TextIO) -> None:
        for line in reader:
            if not line.strip():
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                response = _error(None, -32700, "Parse error")
            else:
                response = self.handle(request)
            if response is None:
                continue
            writer.write(
                json.dumps(
                    response,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
                + "\n"
            )
            writer.flush()


def create_stdio_server() -> MattersMCPStdioServer:
    """Compose the MCP adapter through the one installed-runtime authority."""

    return MattersMCPStdioServer(MattersMCP(runtime.create_service()))


def main() -> int:
    server = create_stdio_server()
    server.serve(sys.stdin, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "MattersMCPStdioServer",
    "SUPPORTED_PROTOCOL_VERSIONS",
    "create_stdio_server",
    "main",
]
