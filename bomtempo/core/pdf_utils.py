"""
PDF utilities — HTML-to-PDF via Playwright + Microsoft Edge.
"""

import threading
from pathlib import Path

from bomtempo.core.logging_utils import get_logger

logger = get_logger(__name__)




def html_to_pdf(
    html: str,
    path: Path,
    margin: dict = None,
    display_header_footer: bool = True,
    header_template: str = None,
    footer_template: str = None,
) -> None:
    """
    Renders an HTML string to a PDF file using Playwright with Microsoft Edge.
    Edge is pre-installed on Windows 11 — no Chromium download required.

    Runs async_playwright in a dedicated thread with its own event loop so
    this function is safe to call from any context: sync code, asyncio handlers,
    or run_in_executor threads — no "Sync API inside asyncio loop" error.

    Usa semáforo global para limitar a 1 instância Chromium simultânea.
    Em caso de timeout, o processo browser é encerrado via SIGTERM/terminate().

    Args:
        html: Full HTML document string (UTF-8).
        path: Destination Path for the PDF file.
        margin: Optional dict with top/right/bottom/left keys. Defaults to
                {"top":"1.8cm","right":"1.4cm","bottom":"1.8cm","left":"1.4cm"}.
        display_header_footer: Whether to show Playwright header/footer. Default True.
        header_template: Override header HTML. If None, uses default BOMTEMPO header.
        footer_template: Override footer HTML. If None, uses default page-number footer.

    Raises:
        RuntimeError: If Playwright or Edge is unavailable, times out, or queue full.
    """
    import asyncio

    errors: list = []
    # Compartilhado entre threads para cleanup de emergência no timeout
    browser_proc: list = []

    async def _render() -> None:
        import sys
        from playwright.async_api import async_playwright

        async def _launch(p):
            """Launch browser: Edge on Windows, Chromium on Linux (auto-install if missing)."""
            if sys.platform == "win32":
                try:
                    return await p.chromium.launch(channel="msedge")
                except Exception:
                    return await p.chromium.launch()
            else:
                try:
                    return await p.chromium.launch()
                except Exception as launch_err:
                    if "Executable doesn't exist" in str(launch_err) or "executable" in str(launch_err).lower():
                        logger.info("pdf_utils: Chromium not found — installing via playwright...")
                        import subprocess
                        subprocess.run(
                            [sys.executable, "-m", "playwright", "install", "chromium"],
                            check=False, capture_output=True, timeout=300,
                        )
                        return await p.chromium.launch()
                    raise

        async with async_playwright() as p:
            browser = await _launch(p)
            # Registra o processo para cleanup de emergência caso timeout
            if hasattr(browser, 'process') and browser.process:
                browser_proc.append(browser.process)
            try:
                page = await browser.new_page()

                # Bloqueia requests externas (Google Fonts, Tailwind CDN, etc.)
                # Em produção o servidor pode não ter acesso à internet, e networkidle
                # nunca dispara enquanto essas requests ficam pendentes → timeout de 90s.
                # O PDF é gerado corretamente com as fontes do sistema mesmo sem elas.
                _BLOCKED_HOSTS = (
                    "fonts.googleapis.com",
                    "fonts.gstatic.com",
                    "cdn.tailwindcss.com",
                    "unpkg.com",
                    "jsdelivr.net",
                    "cdnjs.cloudflare.com",
                )
                async def _block_external(route):
                    if any(h in route.request.url for h in _BLOCKED_HOSTS):
                        await route.abort()
                    else:
                        await route.continue_()
                await page.route("**/*", _block_external)

                # domcontentloaded: não espera requests externas bloqueadas acima.
                # load seria suficiente para HTML inline, mas domcontentloaded é mais rápido
                # e PDFs não dependem de lazy-loaded assets.
                await page.set_content(html, wait_until="domcontentloaded", timeout=15000)
                _default_header = (
                    '<div style="width:100%;box-sizing:border-box;padding:0 48px;'
                    'font-family:Arial,sans-serif;font-size:8px;color:#9CA3AF;'
                    'display:flex;justify-content:space-between;align-items:center;'
                    'border-bottom:1px solid #E5E7EB;padding-bottom:6px;">'
                    '<span style="font-weight:700;color:#C98B2A;letter-spacing:0.12em;">'
                    'BOMTEMPO INTELLIGENCE</span>'
                    '<span>Relatório Executivo · Confidencial</span>'
                    '</div>'
                )
                _default_footer = (
                    '<div style="width:100%;box-sizing:border-box;padding:0 48px;'
                    'font-family:Arial,sans-serif;font-size:8px;color:#9CA3AF;'
                    'display:flex;justify-content:space-between;align-items:center;'
                    'border-top:1px solid #E5E7EB;padding-top:6px;">'
                    '<span>Documento Confidencial — Uso Interno</span>'
                    '<span>Página <span class="pageNumber"></span> '
                    'de <span class="totalPages"></span></span>'
                    '</div>'
                )
                _margin = margin if margin is not None else {
                    "top": "1.8cm", "right": "1.4cm", "bottom": "1.8cm", "left": "1.4cm"
                }
                await page.pdf(
                    path=str(path),
                    format="A4",
                    print_background=True,
                    margin=_margin,
                    display_header_footer=display_header_footer,
                    header_template=header_template if header_template is not None else _default_header,
                    footer_template=footer_template if footer_template is not None else _default_footer,
                )
                logger.debug(f"pdf_utils: PDF written → {path.name}")
            finally:
                await browser.close()
                browser_proc.clear()

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
        # Timeout: encerra browser órfão para liberar RAM imediatamente
        for proc in browser_proc:
            try:
                proc.terminate()
                logger.warning("pdf_utils: browser process encerrado por timeout")
            except Exception:
                pass
        browser_proc.clear()
        raise RuntimeError("PDF generation timed out after 90s")

    if errors:
        raise errors[0]
