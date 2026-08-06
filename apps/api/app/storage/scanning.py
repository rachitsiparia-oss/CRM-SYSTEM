"""Malware-scan hook for uploaded file attachments —
SECURITY_PERFORMANCE_AND_QUALITY.md section 9.3 ("quarantine/scan/clean
flow"). Every `*_attachment`/`staff_document` model already carries a
`scan_status` column (`pending`/`clean`/`infected`/`skipped`) waiting for
this; before this module existed, every upload path left it at its DB
default of `"pending"` forever rather than ever setting it, which silently
implied "scanning is in progress" indefinitely instead of being honest
about the fact that no scan ever ran.

No scanning provider is approved anywhere in `docs/TOOLS.md` — the only
registered scanner is `NoOpScanner`, which reports `"skipped"` rather than
fabricating a `"clean"` result (CLAUDE.md section 16, "do not claim...
integration is available without verified API"). Registering a real
provider later means adding a `MalwareScanner` implementation and swapping
`_scanner` — every call site already calls `scan_upload()` and persists
whatever `ScanResult` comes back, so no caller needs to change, and an
`"infected"` result already blocks the upload before it reaches storage.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ScanResult:
    status: str  # "clean" | "infected" | "skipped" — the *_attachment models' SCAN_STATUSES
    detail: str | None = None


class MalwareScanner(ABC):
    @abstractmethod
    async def scan(self, data: bytes) -> ScanResult: ...


class NoOpScanner(MalwareScanner):
    """The only registered scanner today. Honestly reports "skipped" —
    never "clean", which would claim a scan happened when it did not."""

    async def scan(self, data: bytes) -> ScanResult:
        del data
        return ScanResult(status="skipped", detail="No malware-scanning provider is configured.")


_scanner: MalwareScanner = NoOpScanner()


async def scan_upload(data: bytes) -> ScanResult:
    return await _scanner.scan(data)
