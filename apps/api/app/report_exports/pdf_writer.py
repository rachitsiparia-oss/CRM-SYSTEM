"""PDF generation — TOOLS.md section 11.3: "Playwright with Chromium is
the final, locked approach for controlled backend HTML-to-PDF rendering."
Only ever renders `app.report_exports.templates`-built HTML (a controlled
template, never arbitrary user HTML) — TOOLS.md's "sanitize user content,
use controlled templates" requirement.
"""

from playwright.async_api import async_playwright


async def generate_pdf(*, html: str) -> bytes:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        try:
            page = await browser.new_page()
            await page.set_content(html, wait_until="networkidle")
            pdf_bytes = await page.pdf(format="A4", print_background=True)
        finally:
            await browser.close()
    return pdf_bytes
