import pytest
from worker.tasks.heartbeat import heartbeat

pytestmark = pytest.mark.asyncio


async def test_heartbeat_returns_ok():
    result = await heartbeat(ctx={})
    assert result == "ok"
