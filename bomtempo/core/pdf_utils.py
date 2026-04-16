"""
PDF utilities — HTML-to-PDF via xhtml2pdf in an isolated subprocess.

ARCHITECTURE NOTE — WHY subprocess isolation matters:
  The previous Playwright/Chromium implementation used 300–500 MB RAM per call.
  On the Fly.io 1 GB container, one PDF generation was enough to push the process
  past the OOM limit → the kernel killed the entire Python process → ALL WebSocket
  connections dropped → every user saw "Reconectando" simultaneously.

  The new implementation spawns a SEPARATE PROCESS for each PDF job via
  multiprocessing.Process(context="spawn"). If that worker crashes or OOMs,
  ONLY the subprocess dies. The main Reflex server process and every active
  user connection remain alive. The calling code gets a RuntimeError and can
  show the user an error message instead of bringing down the platform.

  xhtml2pdf peak RAM: ~20–40 MB vs Playwright/Chromium ~300–500 MB.
  xhtml2pdf has zero binary dependencies — no Chromium download required.
"""
from __future__ import annotations

import multiprocessing
import sys
import time
from pathlib import Path

from bomtempo.core.logging_utils import get_logger

logger = get_logger(__name__)

# Minimum free RAM required before spawning the PDF subprocess.
# xhtml2pdf peak: ~40 MB. We require 150 MB to leave headroom for the rest
# of the server (Redis, async handlers, ongoing requests).
# If available RAM is below this, we fail fast with a clear error instead of
# spawning and causing an OOM kill that would disconnect all users.
_MIN_FREE_MB = 150


# ─── Public API ───────────────────────────────────────────────────────────────

def html_to_pdf(
    html: str,
    path: Path,
    margin: dict | None = None,
    display_header_footer: bool = True,
    header_template: str | None = None,
    footer_template: str | None = None,
) -> None:
    """
    Render an HTML string to a PDF file using xhtml2pdf.

    Runs in an isolated subprocess — a crash or OOM in the worker cannot
    affect the main server process or other users' connections.

    Args:
        html: Full HTML document string (UTF-8).
        path: Destination Path for the PDF file.
        margin: Optional dict with top/right/bottom/left keys.
                Defaults to {"top":"1.8cm","right":"1.4cm","bottom":"1.8cm","left":"1.4cm"}.
        display_header_footer: Whether to inject the BOMTEMPO header/footer on each page.
        header_template: Override header HTML (raw HTML fragment). Ignored when
                         display_header_footer=False.
        footer_template: Override footer HTML (raw HTML fragment). Ignored when
                         display_header_footer=False.

    Raises:
        RuntimeError: On timeout, worker crash, or xhtml2pdf errors.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # ── Pre-flight: memory pressure check ────────────────────────────────────
    # Check available RAM BEFORE spawning the subprocess. If the system is already
    # under memory pressure, fail fast here rather than spawning a process that
    # will immediately get OOM-killed (which could cascade and harm other users).
    try:
        import psutil
        available_mb = psutil.virtual_memory().available // (1024 * 1024)
        if available_mb < _MIN_FREE_MB:
            raise RuntimeError(
                f"Memória insuficiente para gerar PDF "
                f"(disponível: {available_mb} MB, mínimo: {_MIN_FREE_MB} MB). "
                f"O RDO foi salvo — tente gerar o PDF novamente em alguns minutos."
            )
        logger.debug(f"pdf_utils: pre-flight OK — {available_mb} MB disponível")
    except ImportError:
        pass  # psutil not available — skip check, proceed

    prepared = _prepare_html(html, margin, display_header_footer, header_template, footer_template)

    # "spawn" starts a fresh Python interpreter — safe from asyncio/threading
    # inheritance issues (unlike "fork"). ~1-2s startup is fine for PDF generation.
    ctx = multiprocessing.get_context("spawn")
    q: multiprocessing.Queue = ctx.Queue()

    proc = ctx.Process(
        target=_xhtml2pdf_worker,
        args=(prepared, str(path), q),
        daemon=True,
    )

    t0 = time.monotonic()
    proc.start()
    proc.join(timeout=120)
    elapsed = time.monotonic() - t0

    if proc.is_alive():
        proc.kill()
        proc.join(timeout=5)
        raise RuntimeError("PDF generation timed out after 120s")

    if proc.exitcode not in (0, None):
        raise RuntimeError(f"PDF worker process crashed (exitcode={proc.exitcode})")

    # Check for application-level error reported by the worker
    try:
        err = q.get_nowait()
    except Exception:
        err = None

    if err:
        raise RuntimeError(f"PDF generation failed: {err}")

    if not path.exists() or path.stat().st_size < 100:
        raise RuntimeError("PDF file was not created or is suspiciously small")

    logger.debug(f"pdf_utils: PDF written → {path.name} ({elapsed:.1f}s)")


# ─── Worker function (executes inside isolated subprocess) ───────────────────

def _xhtml2pdf_worker(html: str, path_str: str, result_queue: "multiprocessing.Queue") -> None:
    """
    xhtml2pdf renderer — this function runs in a completely isolated subprocess.

    Any exception or OOM here only kills this worker process; the parent
    Reflex server process is unaffected.

    OS-level memory cap (Linux/Fly.io):
      resource.setrlimit(RLIMIT_AS, 400 MB) is set at startup of this subprocess.
      If xhtml2pdf tries to allocate more than 400 MB of virtual address space,
      the OS raises MemoryError inside THIS process — not OOM-killing the parent.
      This is a hard ceiling enforced by the kernel, not Python.
    """
    # ── OS-enforced memory cap — Linux only (Fly.io, Docker, most VPS) ───────
    # On Windows/macOS (local dev) this is silently skipped.
    # 400 MB virtual address space: generous for xhtml2pdf (~40 MB typical),
    # but hard-caps runaway allocations before they can pressure the host.
    try:
        import resource  # noqa: PLC0415 — stdlib, Linux only
        _400MB = 400 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (_400MB, _400MB))
    except (ImportError, ValueError, resource.error):  # type: ignore[attr-defined]
        pass  # Windows / macOS / insufficient privileges — skip silently

    try:
        from xhtml2pdf import pisa  # type: ignore[import]  # noqa: PLC0415

        with open(path_str, "wb") as fh:
            result = pisa.CreatePDF(html, dest=fh, encoding="utf-8")

        if result.err:
            result_queue.put(f"xhtml2pdf reported {result.err} error(s)")
        else:
            result_queue.put(None)  # None = success sentinel

    except MemoryError:
        result_queue.put("PDF worker atingiu limite de memória (400 MB) — documento muito grande?")
    except Exception as exc:  # noqa: BLE001
        result_queue.put(str(exc))


# ─── HTML preparation helpers ─────────────────────────────────────────────────

_DEFAULT_HEADER_HTML = (
    '<div style="width:100%;box-sizing:border-box;'
    'font-family:Arial,sans-serif;font-size:8px;color:#9CA3AF;'
    'display:flex;justify-content:space-between;align-items:center;'
    'border-bottom:1px solid #E5E7EB;padding-bottom:4px;">'
    '<span style="font-weight:700;color:#C98B2A;letter-spacing:0.12em;">'
    "BOMTEMPO INTELLIGENCE</span>"
    "<span>Relatório Executivo · Confidencial</span>"
    "</div>"
)

_DEFAULT_FOOTER_HTML = (
    '<div style="width:100%;box-sizing:border-box;'
    'font-family:Arial,sans-serif;font-size:8px;color:#9CA3AF;'
    'display:flex;justify-content:space-between;align-items:center;'
    'border-top:1px solid #E5E7EB;padding-top:4px;">'
    "<span>Documento Confidencial — Uso Interno</span>"
    "<span>Página <pdf:pagenumber /> de <pdf:pagecount /></span>"
    "</div>"
)


def _prepare_html(
    html: str,
    margin: dict | None,
    display_header_footer: bool,
    header_template: str | None,
    footer_template: str | None,
) -> str:
    """
    Inject @page CSS margins and optional fixed-position header/footer into HTML.

    xhtml2pdf renders elements with `position: fixed` as running headers/footers
    that repeat on every page. <pdf:pagenumber /> and <pdf:pagecount /> are
    xhtml2pdf-specific tags for page numbering.
    """
    _m = margin or {"top": "1.8cm", "right": "1.4cm", "bottom": "1.8cm", "left": "1.4cm"}
    top    = _m.get("top",    "1.8cm")
    right  = _m.get("right",  "1.4cm")
    bottom = _m.get("bottom", "1.8cm")
    left   = _m.get("left",   "1.4cm")

    # When header/footer is enabled, increase top/bottom margins to prevent overlap.
    # Fixed-position elements occupy space that is NOT subtracted from the flow area
    # automatically — we must pad the page margins manually.
    if display_header_footer and top not in ("0", "0cm", "0mm", "0px", "0pt"):
        top    = "2.2cm"
        bottom = "2.0cm"

    page_css = (
        "<style>"
        f"@page {{ margin: {top} {right} {bottom} {left}; }}"
        "</style>"
    )

    # Ensure valid HTML structure
    if "<html" not in html.lower():
        html = f"<html><head></head><body>{html}</body></html>"

    # Inject @page style into <head>
    if "</head>" in html:
        html = html.replace("</head>", f"{page_css}</head>", 1)
    else:
        html = page_css + html

    if display_header_footer:
        _header = header_template if header_template is not None else _DEFAULT_HEADER_HTML
        _footer = footer_template if footer_template is not None else _DEFAULT_FOOTER_HTML

        # xhtml2pdf: position:fixed elements repeat on every page
        hf_html = (
            f'<div style="position:fixed;top:0;left:0;right:0;height:0.7cm;">'
            f"{_header}"
            f"</div>"
            f'<div style="position:fixed;bottom:0;left:0;right:0;height:0.7cm;">'
            f"{_footer}"
            f"</div>"
        )

        if "<body" in html:
            # Insert immediately after <body ...>
            idx = html.index("<body")
            end_tag = html.index(">", idx) + 1
            html = html[:end_tag] + hf_html + html[end_tag:]
        else:
            html = hf_html + html

    return html
