from worker.asyncio_policy import configure_event_loop_policy

# Must run before pytest-asyncio creates its event loop — see
# worker/asyncio_policy.py and the identical fix in apps/api/tests/conftest.py.
configure_event_loop_policy()
