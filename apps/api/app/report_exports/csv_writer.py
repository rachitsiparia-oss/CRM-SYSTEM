"""CSV generation with formula-injection protection — TOOLS.md section
11.1's "REQUIRED" CSV export rule. A cell beginning with `=`, `+`, `-`,
`@`, tab, or CR is a formula trigger in Excel/Sheets/LibreOffice
(CSV-injection, OWASP); prefixing it with a leading apostrophe forces it
to be read as literal text in every one of those tools, without altering
the visible value for anything else.
"""

import csv
import io

_FORMULA_TRIGGER_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _sanitize_cell(value: object) -> str:
    text = "" if value is None else str(value)
    if text and text[0] in _FORMULA_TRIGGER_PREFIXES:
        return "'" + text
    return text


def generate_csv(*, columns: list[str], rows: list[dict[str, object]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([_sanitize_cell(row.get(column)) for column in columns])
    # UTF-8 BOM so Excel (the primary consumer) detects encoding correctly
    # instead of mis-rendering non-ASCII characters.
    return buffer.getvalue().encode("utf-8-sig")
