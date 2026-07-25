"""Local development entrypoint.

Running `uvicorn app.main:app` directly lets uvicorn's CLI create its event
loop (Windows default: ProactorEventLoop) before our app module is ever
imported, which is too late to switch policies — psycopg 3's async mode
requires a selector-based loop on Windows. This script sets the policy
first, then hands off to uvicorn. On Linux/macOS (Railway, CI) this call is
a no-op, so the same script works everywhere.
"""

from app.core.asyncio_policy import configure_event_loop_policy

configure_event_loop_policy()

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
