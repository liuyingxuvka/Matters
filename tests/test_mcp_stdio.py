from __future__ import annotations

from io import StringIO
import json

from matters.api.mcp.server import MattersMCP
from matters.api.mcp.stdio import MattersMCPStdioServer, create_stdio_server


class FakeService:
    def capabilities(self):
        return {"ai_gateway": "available"}


def test_mcp_stdio_initializes_lists_and_calls_without_extra_stdout():
    requests = (
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            },
        },
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        },
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        },
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "capabilities", "arguments": {}},
        },
    )
    reader = StringIO(
        "".join(
            json.dumps(request, separators=(",", ":")) + "\n"
            for request in requests
        )
    )
    writer = StringIO()

    MattersMCPStdioServer(MattersMCP(FakeService())).serve(reader, writer)

    responses = tuple(
        json.loads(line) for line in writer.getvalue().splitlines()
    )
    assert len(responses) == 3
    assert responses[0]["result"]["protocolVersion"] == "2025-11-25"
    assert responses[0]["result"]["capabilities"] == {
        "tools": {"listChanged": False}
    }
    assert {
        tool["name"] for tool in responses[1]["result"]["tools"]
    } >= {
        "list_model_contracts",
        "get_situation_context",
        "record_user_observation",
    }
    assert responses[2]["result"]["structuredContent"] == {
        "ok": True,
        "result": {"ai_gateway": "available"},
    }
    assert responses[2]["result"]["isError"] is False


def test_mcp_stdio_rejects_calls_before_initialization():
    server = MattersMCPStdioServer(MattersMCP(FakeService()))

    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }
    )

    assert response == {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {"code": -32002, "message": "Server not initialized"},
    }


def test_mcp_stdio_composes_through_runtime_authority(monkeypatch):
    service = FakeService()
    calls = []

    def create_service():
        calls.append("runtime")
        return service

    monkeypatch.setattr(
        "matters.api.mcp.stdio.runtime.create_service",
        create_service,
    )

    server = create_stdio_server()

    assert calls == ["runtime"]
    assert server.adapter._service is service
