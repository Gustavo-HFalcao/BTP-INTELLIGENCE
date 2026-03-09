"""
Supabase REST API Client — Bomtempo Dashboard
Usa httpx (já disponível) para comunicar com a API PostgREST do Supabase.

Usa SUPABASE_SERVICE_KEY (service_role) — chave server-side que bypassa RLS.
Nunca é exposta ao browser (Reflex roda Python no servidor).
"""

import os
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

from bomtempo.core.logging_utils import get_logger

load_dotenv()

logger = get_logger(__name__)

# ── Credentials ────────────────────────────────────────────────────────────────
# Service role key lida do .env — bypassa RLS com segurança (server-side only).
SUPABASE_URL = "https://nychzaapchxdlsffotcq.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
REST_BASE = f"{SUPABASE_URL}/rest/v1"

if not SUPABASE_KEY:
    logger.error(
        "SUPABASE_SERVICE_KEY não encontrada no .env. "
        "Adicione: SUPABASE_SERVICE_KEY=sb_secret_..."
    )


def _headers(prefer_return: bool = False) -> Dict[str, str]:
    h = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if prefer_return:
        h["Prefer"] = "return=representation"
    return h


# ── CRUD helpers ───────────────────────────────────────────────────────────────


def sb_select_paginated(
    table: str,
    page: int = 1,
    limit: int = 50,
    filters: Dict[str, Any] = None,
    ilike_filters: Dict[str, str] = None,
    order: str = "created_at.desc",
    select: str = "*",
) -> tuple:
    """
    SELECT with server-side pagination using PostgREST Range header.
    Returns (rows: List[Dict], total_count: int).

    filters       — exact match: {"column": "value"}
    ilike_filters — case-insensitive LIKE: {"column": "pattern"}
    """
    try:
        offset = (page - 1) * limit
        range_end = offset + limit - 1
        h = _headers()
        h["Prefer"] = "count=exact"
        h["Range-Unit"] = "items"
        h["Range"] = f"{offset}-{range_end}"

        params: Dict[str, str] = {"select": select, "order": order}
        for k, v in (filters or {}).items():
            params[k] = f"eq.{v}"
        for k, v in (ilike_filters or {}).items():
            params[k] = f"ilike.*{v}*"

        resp = httpx.get(
            f"{REST_BASE}/{table}",
            headers=h,
            params=params,
            timeout=15,
        )
        if resp.status_code in (200, 206):
            rows = resp.json()
            # Content-Range: 0-49/150
            total = 0
            cr = resp.headers.get("Content-Range", "")
            if "/" in cr:
                try:
                    total = int(cr.split("/")[1])
                except ValueError:
                    total = len(rows)
            else:
                total = len(rows)
            return rows, total
        logger.error(f"sb_select_paginated {table} → {resp.status_code}: {resp.text[:300]}")
        return [], 0
    except Exception as e:
        logger.error(f"sb_select_paginated {table} exception: {e}")
        return [], 0


def sb_select(
    table: str,
    filters: Dict[str, Any] = None,
    order: str = "",
    limit: int = 1000,
) -> List[Dict]:
    """SELECT * FROM table WHERE column=eq.value ORDER BY ... LIMIT n"""
    try:
        params: Dict[str, str] = {"select": "*"}
        for k, v in (filters or {}).items():
            params[k] = f"eq.{v}"
        if order:
            params["order"] = order
        params["limit"] = str(limit)

        resp = httpx.get(
            f"{REST_BASE}/{table}",
            headers=_headers(),
            params=params,
            timeout=15,
        )
        if resp.status_code == 200:
            result = resp.json()
            if not result:
                logger.warning(
                    f"Supabase SELECT {table}: 200 OK porém 0 linhas retornadas. "
                    f"Verifique se a tabela tem dados."
                )
            else:
                logger.info(
                    f"Supabase SELECT {table}: {len(result)} linhas, campos={list(result[0].keys())}"
                )
            return result
        logger.error(f"Supabase SELECT {table} → {resp.status_code}: {resp.text[:400]}")
        return []
    except Exception as e:
        logger.error(f"Supabase SELECT {table} exception: {e}")
        return []


def sb_insert(table: str, data: Dict[str, Any]) -> Optional[Dict]:
    """INSERT a row; returns the inserted record or None on failure."""
    try:
        resp = httpx.post(
            f"{REST_BASE}/{table}",
            headers=_headers(prefer_return=True),
            json=data,
            timeout=15,
        )
        if resp.status_code in (200, 201):
            result = resp.json()
            return result[0] if isinstance(result, list) and result else result
        err_msg = f"Supabase INSERT {table} → {resp.status_code}: {resp.text[:400]}"
        logger.error(err_msg)
        raise ValueError(err_msg)
    except Exception as e:
        logger.error(f"Supabase INSERT {table} exception: {e}")
        raise e


def sb_upsert(
    table: str,
    record: Dict[str, Any],
    on_conflict: str = "ID",
) -> Dict:
    """INSERT OR UPDATE a single record using PostgREST conflict resolution.

    If the row with the given `on_conflict` column value exists → UPDATE.
    If it doesn't exist → INSERT a new row.
    Unlike sb_update, never silently skips when the ID is not found.

    Returns {"upserted": 1} on success, raises ValueError on failure.
    """
    try:
        h = _headers()
        h["Prefer"] = "return=representation,resolution=merge-duplicates"
        resp = httpx.post(
            f"{REST_BASE}/{table}",
            headers=h,
            params={"on_conflict": on_conflict},
            json=record,
            timeout=15,
        )
        if resp.status_code in (200, 201):
            return {"upserted": 1}
        err_msg = f"Supabase UPSERT {table} → {resp.status_code}: {resp.text[:400]}"
        logger.error(err_msg)
        raise ValueError(err_msg)
    except Exception as e:
        logger.error(f"Supabase UPSERT {table} exception: {e}")
        raise e


def sb_update(
    table: str,
    filters: Dict[str, Any],
    data: Dict[str, Any],
) -> bool:
    """PATCH rows matching filters with data."""
    try:
        params = {k: f"eq.{v}" for k, v in filters.items()}
        resp = httpx.patch(
            f"{REST_BASE}/{table}",
            headers=_headers(),
            params=params,
            json=data,
            timeout=15,
        )
        if resp.status_code not in (200, 204):
            err_msg = f"Supabase UPDATE {table} → {resp.status_code}: {resp.text[:400]}"
            logger.error(err_msg)
            raise ValueError(err_msg)
        return True
    except Exception as e:
        logger.error(f"Supabase UPDATE {table} exception: {e}")
        raise e


# ── Storage helpers ────────────────────────────────────────────────────────────


def sb_storage_upload(
    bucket: str, path: str, file_bytes: bytes, content_type: str = "application/octet-stream"
) -> Optional[str]:
    """
    Upload de arquivo para o Supabase Storage.
    Retorna a URL pública permanente ou None em caso de erro.

    Padrão de uso:
        url = sb_storage_upload("rdo-pdfs", f"{id_rdo}.pdf", pdf_bytes, "application/pdf")
        # Armazene url no banco — funciona independente de restarts/deploys.

    Para imagens de NF, fotos de obra etc.:
        url = sb_storage_upload("reembolso-fotos", f"{id_reembolso}/nota.jpg", img_bytes, "image/jpeg")
    """
    try:
        upload_url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{path}"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": content_type,
            "x-upsert": "true",  # sobrescreve se já existir
        }
        resp = httpx.post(upload_url, headers=headers, content=file_bytes, timeout=60)
        if resp.status_code in (200, 201):
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}"
            logger.info(f"✅ Storage upload: {bucket}/{path} → {public_url}")
            return public_url
        logger.error(f"Storage upload {bucket}/{path} → {resp.status_code}: {resp.text[:300]}")
        return None
    except Exception as e:
        logger.error(f"Storage upload exception: {e}")
        return None


def sb_delete(table: str, filters: Dict[str, Any]) -> bool:
    """DELETE rows matching filters."""
    try:
        params = {k: f"eq.{v}" for k, v in filters.items()}
        resp = httpx.delete(
            f"{REST_BASE}/{table}",
            headers=_headers(),
            params=params,
            timeout=15,
        )
        return resp.status_code in (200, 204)
    except Exception as e:
        logger.error(f"Supabase DELETE {table} exception: {e}")
        return False
