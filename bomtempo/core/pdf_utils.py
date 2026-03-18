"""
PDF utilities — HTML-to-PDF via Playwright + Microsoft Edge.
"""

from pathlib import Path

from bomtempo.core.logging_utils import get_logger

logger = get_logger(__name__)


def html_to_pdf(html: str, path: Path) -> None:
    """
    Renders an HTML string to a PDF file using Playwright with Microsoft Edge.
    Edge is pre-installed on Windows 11 — no Chromium download required.

    Runs async_playwright in a dedicated thread with its own event loop so
    this function is safe to call from any context: sync code, asyncio handlers,
    or run_in_executor threads — no "Sync API inside asyncio loop" error.

    Args:
        html: Full HTML document string (UTF-8).
        path: Destination Path for the PDF file.

    Raises:
        RuntimeError: If Playwright or Edge is unavailable, or times out.
    """
    import asyncio
    import threading

    errors: list = []

    async def _render() -> None:
        import sys
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            # Windows: use pre-installed Edge; Linux/production: fall back to Chromium
            if sys.platform == "win32":
                try:
                    browser = await p.chromium.launch(channel="msedge")
                except Exception:
                    browser = await p.chromium.launch()
            else:
                browser = await p.chromium.launch()
            try:
                page = await browser.new_page()
                # wait_until="networkidle" ensures Google Fonts load before rendering
                await page.set_content(html, wait_until="networkidle")
                _header = (
                    '<div style="width:100%;box-sizing:border-box;padding:0 48px;'
                    'font-family:Arial,sans-serif;font-size:8px;color:#9CA3AF;'
                    'display:flex;justify-content:space-between;align-items:center;'
                    'border-bottom:1px solid #E5E7EB;padding-bottom:6px;">'
                    '<span style="font-weight:700;color:#C98B2A;letter-spacing:0.12em;">'
                    'BOMTEMPO INTELLIGENCE</span>'
                    '<span>Relatório Executivo · Confidencial</span>'
                    '</div>'
                )
                _footer = (
                    '<div style="width:100%;box-sizing:border-box;padding:0 48px;'
                    'font-family:Arial,sans-serif;font-size:8px;color:#9CA3AF;'
                    'display:flex;justify-content:space-between;align-items:center;'
                    'border-top:1px solid #E5E7EB;padding-top:6px;">'
                    '<span>Documento Confidencial — Uso Interno</span>'
                    '<span>Página <span class="pageNumber"></span> '
                    'de <span class="totalPages"></span></span>'
                    '</div>'
                )
                await page.pdf(
                    path=str(path),
                    format="A4",
                    print_background=True,
                    margin={"top": "1.8cm", "right": "1.4cm", "bottom": "1.8cm", "left": "1.4cm"},
                    display_header_footer=True,
                    header_template=_header,
                    footer_template=_footer,
                )
                logger.debug(f"pdf_utils: PDF written → {path.name}")
            finally:
                await browser.close()

    def _thread_main() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_render())
        except Exception as exc:
            errors.append(exc)
        finally:
            loop.close()

    t = threading.Thread(target=_thread_main, daemon=True)
    t.start()
    t.join(timeout=90)

    if t.is_alive():
        raise RuntimeError("PDF generation timed out after 90s")
    if errors:
        raise errors[0]
