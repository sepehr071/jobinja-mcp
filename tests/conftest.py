import json
from pathlib import Path

import httpx
import pytest
from mcp import Client

from jobinja_mcp import http
from jobinja_mcp.server import mcp

FIXTURES = Path(__file__).parent / "fixtures"


def page(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def fresh_http_client(monkeypatch):
    """The shared httpx client is bound to one event loop; each test gets a new loop."""
    monkeypatch.setattr(http, "RETRY_DELAY", 0)
    monkeypatch.setattr(http, "JITTER", (0, 0))
    http.set_transport(None)
    yield
    http.set_transport(None)


@pytest.fixture
def site():
    """Route table for a fake jobinja.ir: site["/path"] = fixture file name, or a callable(request) -> Response.

    Keys match the URL path only. Unknown paths return 404. Every request is appended to site.calls.
    """

    class Routes(dict):
        calls: list[httpx.Request]

    routes = Routes()
    routes.calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        routes.calls.append(request)
        target = routes.get(request.url.path)
        if target is None:
            return httpx.Response(404, text="not found")
        if callable(target):
            return target(request)
        return httpx.Response(200, text=page(target))

    http.set_transport(httpx.MockTransport(handler))
    return routes


@pytest.fixture
async def client():
    async with Client(mcp, raise_exceptions=True) as c:
        call_tool = c.call_tool

        async def parsed(*args, **kwargs):
            result = await call_tool(*args, **kwargs)
            if not result.is_error:
                result.structured_content = json.loads(result.content[0].text)
            return result

        c.call_tool = parsed
        yield c
