import asyncio
import sys


def configure_event_loop_policy() -> None:
    """psycopg 3's async mode refuses to run under Windows' default
    ProactorEventLoop — it requires a selector-based loop. Must be called
    before any asyncio event loop is created (uvicorn, pytest-asyncio, or
    ARQ), so every async entrypoint calls this first thing on import."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
