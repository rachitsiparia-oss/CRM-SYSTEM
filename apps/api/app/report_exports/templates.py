"""The single controlled HTML template PDF exports render — TOOLS.md
section 11.3's "use controlled templates." Every dynamic value is escaped
via `html.escape`; nothing here ever interpolates raw user-authored HTML.
"""

from html import escape


def build_report_html(
    *,
    title: str,
    domain: str,
    window_code: str,
    window_start: str,
    window_end: str,
    timezone: str,
    generated_at: str,
    metrics: list[dict[str, object]],
) -> str:
    rows_html = "".join(
        f"<tr>"
        f"<td>{escape(str(m.get('display_name', '')))}</td>"
        f"<td>{escape(str(m.get('value', '')))}</td>"
        f"<td>{escape(str(m.get('comparison_value', '') or ''))}</td>"
        f"<td>{escape(str(m.get('change_pct', '') or ''))}</td>"
        f"<td>{escape(str(m.get('unit', '') or ''))}</td>"
        f"</tr>"
        for m in metrics
    )
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>{escape(title)}</title>
<style>
  body {{ font-family: Arial, sans-serif; color: #1a1a1a; padding: 24px; }}
  h1 {{ font-size: 20px; margin-bottom: 4px; }}
  .meta {{ color: #555; font-size: 12px; margin-bottom: 16px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  th, td {{ border: 1px solid #ccc; padding: 6px 8px; text-align: left; }}
  th {{ background: #f2f2f2; }}
  .footer {{ margin-top: 16px; font-size: 10px; color: #888; }}
</style>
</head>
<body>
  <h1>{escape(title)}</h1>
  <div class="meta">
    Domain: {escape(domain)} &middot; Window: {escape(window_code)}
    ({escape(window_start)} &ndash; {escape(window_end)}, {escape(timezone)})
  </div>
  <table>
    <thead>
      <tr><th>Metric</th><th>Value</th><th>Comparison</th><th>Change %</th><th>Unit</th></tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
  <div class="footer">Generated {escape(generated_at)} &middot; RKPR Restaurant CRM</div>
</body>
</html>"""
