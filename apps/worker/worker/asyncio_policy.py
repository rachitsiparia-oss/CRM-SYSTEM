import asyncio
import sys


def configure_event_loop_policy() -> None:
    """psycopg 3's async mode refuses to run under Windows' default
    ProactorEventLoop — it requires a selector-based loop. Must be called
    before ARQ creates its event loop, so this runs first thing on import
    — mirrors apps/api/app/core/asyncio_policy.py."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
