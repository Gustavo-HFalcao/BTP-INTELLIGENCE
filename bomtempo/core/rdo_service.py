"""
RDO v2 Service — Lógica de negócio para o módulo RDO revampado.

Tabelas novas: rdo_master, rdo2_mao_obra, rdo2_atividades,
               rdo2_equipamentos, rdo2_materiais, rdo2_evidencias
Bucket: rdo-pdfs (existente), rdo-evidencias (novo)
"""

import html as _html_mod
import io
import math
import threading
from datetime import datetime

from typing import Any, Dict, List, Optional, Tuple

from bomtempo.core.ai_client import ai_client
from bomtempo.core.config import Config
from bomtempo.core.logging_utils import get_logger
from bomtempo.core.pdf_utils import html_to_pdf
from bomtempo.core.supabase_client import (
    sb_delete,
    sb_insert,
    sb_select,
    sb_storage_upload,
    sb_update,
    sb_upsert,
)

logger = get_logger(__name__)

SUPABASE_URL = Config.SUPABASE_URL


# ── Geo utilities ────────────────────────────────────────────────────────────

def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in meters between two GPS points."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _forward_geocode(address: str) -> tuple:
    """Forward geocode a Brazilian address via Nominatim. Returns (lat, lng) or (0.0, 0.0)."""
    if not address or len(address.strip()) < 5:
        return 0.0, 0.0
    try:
        import httpx
        resp = httpx.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 1, "countrycodes": "br"},
            headers={"User-Agent": "BomtempoRDO/2.0"},
            timeout=10,
        )
        if resp.status_code == 200:
            results = resp.json()
            if results:
                return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as e:
        logger.warning(f"Forward geocode falhou: {e}")
    return 0.0, 0.0


def _reverse_geocode(lat: float, lng: float) -> str:
    """Reverse geocode via OpenStreetMap Nominatim. Returns human-readable address."""
    try:
        import httpx
        resp = httpx.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"format": "json", "lat": lat, "lon": lng, "zoom": 16, "addressdetails": 1},
            headers={"User-Agent": "BomtempoRDO/2.0"},
            timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json()
            addr = data.get("address", {})
            road   = addr.get("road") or addr.get("pedestrian") or ""
            number = addr.get("house_number") or ""
            suburb = addr.get("suburb") or addr.get("neighbourhood") or ""
            city   = addr.get("city") or addr.get("town") or addr.get("municipality") or ""
            parts  = [f"{road}{', ' + number if number else ''}", suburb, city]
            return ", ".join(p for p in parts if p) or data.get("display_name", "")[:80]
    except Exception as e:
        logger.warning(f"Reverse geocode falhou: {e}")
    return ""


# ── Image utilities ──────────────────────────────────────────────────────────

_PT_MONTHS = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]

def _pt_datetime_str(dt: datetime) -> str:
    """Formata datetime no estilo Auvo: '15 de mar. de 2026, 08:06:15 BRT'."""
    try:
        return f"{dt.day} de {_PT_MONTHS[dt.month-1]}. de {dt.year}, {dt.strftime('%H:%M:%S')} BRT"
    except Exception:
        return dt.strftime("%d/%m/%Y %H:%M:%S")

def _decimal_to_dms(deg: float, is_lat: bool) -> str:
    """Converte graus decimais para formato DMS: '7° 10\' 4\" S'."""
    ref = ("N" if deg >= 0 else "S") if is_lat else ("E" if deg >= 0 else "W")
    deg = abs(deg)
    d = int(deg)
    minutes = (deg - d) * 60
    m = int(minutes)
    s = int(round((minutes - m) * 60))
    return f"{d}° {m}' {s}\" {ref}"

def _fetch_map_thumbnail(lat: float, lng: float, size: Tuple[int,int] = (180, 130)) -> Optional[bytes]:
    """Baixa miniatura do mapa via OSM staticmap (fire-and-check). Retorna None se falhar."""
    try:
        import httpx
        url = (
            f"https://staticmap.openstreetmap.de/staticmap.php"
            f"?center={lat:.6f},{lng:.6f}&zoom=15&size={size[0]}x{size[1]}"
            f"&markers={lat:.6f},{lng:.6f},ol-marker"
        )
        r = httpx.get(url, timeout=5, follow_redirects=True)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
            return r.content
    except Exception as e:
        logger.debug(f"Map thumbnail falhou: {e}")
    return None

def _extract_exif_gps(img_bytes: bytes) -> Tuple[float, float]:
    """Extract GPS lat/lng from image EXIF. Returns (0.0, 0.0) if not found."""
    try:
        from PIL import Image
        from PIL.ExifTags import GPSTAGS, TAGS

        img = Image.open(io.BytesIO(img_bytes))
        exif_raw = img._getexif()  # type: ignore[attr-defined]
        if not exif_raw:
            return 0.0, 0.0

        gps_info: Dict[str, Any] = {}
        for tag, val in exif_raw.items():
            if TAGS.get(tag) == "GPSInfo":
                for k, v in val.items():
                    gps_info[GPSTAGS.get(k, k)] = v

        if "GPSLatitude" not in gps_info or "GPSLongitude" not in gps_info:
            return 0.0, 0.0

        def _dms(dms, ref: str) -> float:
            d, m, s = [float(x) for x in dms]
            dd = d + m / 60 + s / 3600
            return -dd if ref in ("S", "W") else dd

        lat = _dms(gps_info["GPSLatitude"],  gps_info.get("GPSLatitudeRef",  "N"))
        lng = _dms(gps_info["GPSLongitude"], gps_info.get("GPSLongitudeRef", "E"))
        return lat, lng
    except Exception as e:
        logger.debug(f"EXIF GPS: {e}")
        return 0.0, 0.0


def _apply_watermark(img_bytes: bytes, meta: Dict[str, Any], content_type: str = "image/jpeg") -> bytes:
    """Overlay Auvo-style geolocation stamp: top-left text panel + top-right map thumbnail.

    meta keys:
      rede_time   – str, network/server time (formatted PT)
      local_time  – str, device/EXIF time (formatted PT)
      lat / lng   – float, GPS decimal degrees (optional)
      address     – str, street + number (optional)
      neighborhood– str (optional)
      city        – str, "Cidade UF" (optional)
      postcode    – str (optional)
      contrato    – str
      mestre      – str
      map_bytes   – bytes|None, pre-fetched map thumbnail (optional)
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        w, h = img.size

        # ── Fonts ────────────────────────────────────────────────
        fsize = max(13, w // 50)
        fnt = fnt_sm = ImageFont.load_default()
        for fp in [
            "arial.ttf", "Arial.ttf",
            "DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]:
            try:
                fnt_sm = ImageFont.truetype(fp, size=max(11, fsize - 2))
                break
            except Exception:
                continue

        # ── Build text lines ──────────────────────────────────────
        WHITE   = (255, 255, 255, 230)
        COPPER  = (201, 139, 42,  230)
        MUTED   = (180, 210, 205, 200)

        text_entries: List[Tuple[str, Any, Any]] = []  # (text, font, color)

        if meta.get("rede_time"):
            text_entries.append((f"Rede: {meta['rede_time']}", fnt_sm, WHITE))
        if meta.get("local_time"):
            text_entries.append((f"Local: {meta['local_time']}", fnt_sm, WHITE))

        lat = meta.get("lat")
        lng = meta.get("lng")
        if lat and lng:
            lat_dms = _decimal_to_dms(float(lat), True)
            lng_dms = _decimal_to_dms(float(lng), False)
            text_entries.append((f"{lat_dms}, {lng_dms}", fnt_sm, MUTED))

        if meta.get("address"):
            text_entries.append((str(meta["address"])[:48], fnt_sm, WHITE))
        if meta.get("neighborhood"):
            text_entries.append((str(meta["neighborhood"])[:40], fnt_sm, WHITE))
        if meta.get("city"):
            text_entries.append((str(meta["city"])[:40], fnt_sm, WHITE))
        if meta.get("postcode"):
            text_entries.append((str(meta["postcode"]), fnt_sm, MUTED))

        # BTP branding footer
        text_entries.append((f"BTP Intelligence · {meta.get('contrato','—')}", fnt_sm, COPPER))

        # ── Measure text area ─────────────────────────────────────
        tmp_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        line_h = fsize + 5
        text_w = max(
            int(tmp_draw.textlength(t, font=f) + 24)
            for t, f, _ in text_entries
        ) if text_entries else 200
        text_h = len(text_entries) * line_h + 16

        # ── Map thumbnail (top-right) ─────────────────────────────
        map_img = None
        map_bytes = meta.get("map_bytes")
        if map_bytes:
            try:
                map_img = Image.open(io.BytesIO(map_bytes)).convert("RGBA")
                thumb_w = min(int(w * 0.22), 200)
                thumb_h = int(thumb_w * 0.72)
                map_img = map_img.resize((thumb_w, thumb_h), Image.LANCZOS)
            except Exception:
                map_img = None

        # ── Compose text panel ────────────────────────────────────
        panel = Image.new("RGBA", (text_w, text_h), (0, 0, 0, 175))
        draw  = ImageDraw.Draw(panel)
        y = 8
        for text, fnt_use, clr in text_entries:
            draw.text((12, y), text, font=fnt_use, fill=clr)
            y += line_h

        # ── Composite onto image ──────────────────────────────────
        canvas = img.copy()
        canvas.paste(panel, (0, 0), panel)   # top-left
        if map_img:
            mx = w - map_img.width - 4
            # thin border around map
            border = Image.new("RGBA", (map_img.width + 4, map_img.height + 4), (201, 139, 42, 200))
            canvas.paste(border, (mx - 2, -2), border)
            canvas.paste(map_img, (mx, 0), map_img)

        out = canvas.convert("RGB")
        buf = io.BytesIO()
        fmt = "PNG" if "png" in content_type.lower() else "JPEG"
        out.save(buf, format=fmt, quality=88)
        return buf.getvalue()
    except Exception as e:
        logger.warning(f"Watermark falhou: {e}")
        return img_bytes


# ── ID Generation ───────────────────────────────────────────────────────────

def _gen_id(contrato: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = (contrato or "RDO").replace("/", "-").replace(" ", "")[:20]
    return f"RDO2-{safe}-{ts}"


# ── HTML Builder ────────────────────────────────────────────────────────────

class RDOService:

    @staticmethod
    def _e(s) -> str:
        return _html_mod.escape(str(s) if s is not None else "—")

    @staticmethod
    def _fmt_date(d: str) -> str:
        try:
            return datetime.strptime(str(d), "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            return str(d) if d else "—"

    @staticmethod
    def _fmt_ts(ts) -> str:
        if not ts:
            return "—"
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            return dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            return str(ts)[:16]

    @staticmethod
    def _build_gps_row(label: str, lat, lng, endereco: str, ts, distancia=None) -> str:
        if not lat and not lng:
            return f"""
            <div class="gps-row gps-empty">
              <div class="gps-icon">📍</div>
              <div class="gps-text">
                <span class="gps-label">{label}</span>
                <span class="gps-val gps-none">Não registrado</span>
              </div>
            </div>"""
        time_str = ""
        if ts:
            try:
                dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                time_str = dt.strftime("%H:%M")
            except Exception:
                time_str = str(ts)[:5]
        addr = RDOService._e(endereco or f"Lat {float(lat):.6f}, Lng {float(lng):.6f}")
        # Distance badge (matching Auvo style)
        dist_badge = ""
        if distancia and float(distancia) > 0:
            d = float(distancia)
            d_str = f"{d:.0f} metros" if d < 1000 else f"{d/1000:.2f} km"
            clr = "#1d7066" if d <= 100 else ("#8a6d0a" if d <= 300 else "#C0392B")
            dist_badge = f'<span class="dist-badge" style="background:{clr}20;color:{clr};border:0.5px solid {clr}60;">{d_str} da obra</span>'
        return f"""
            <div class="gps-row">
              <div class="gps-icon">📍</div>
              <div class="gps-text">
                <span class="gps-label">{label}{f' — {time_str}' if time_str else ''}</span>
                <span class="gps-val">{addr} {dist_badge}</span>
                <span class="gps-coords">({float(lat):.6f}, {float(lng):.6f})</span>
              </div>
            </div>"""

    @staticmethod
    def _labor_rows(items: list) -> str:
        e = RDOService._e
        if not items:
            return '<tr><td colspan="3" class="empty-row">Nenhum profissional registrado.</td></tr>'
        rows = [
            f"<tr><td>{e(r.get('profissao', r.get('funcao', '')))}</td>"
            f'<td class="center">{e(r.get("quantidade", r.get("qtd", 1)))}</td>'
            f"<td>{e(r.get('observacoes', r.get('obs', '')) or '—')}</td></tr>"
            for r in items[:30]
        ]
        rows.append(
            f'<tr class="total-row"><td colspan="3">TOTAL: {len(items)} profissional(is) em campo</td></tr>'
        )
        return "\n".join(rows)

    @staticmethod
    def _activity_rows(items: list) -> str:
        e = RDOService._e
        if not items:
            return '<tr><td colspan="3" class="empty-row">Nenhuma atividade registrada.</td></tr>'
        rows = []
        for r in items[:30]:
            pct = int(r.get("progresso_percentual", r.get("percentual", 0)) or 0)
            status = r.get("status", "Em andamento")
            sc = "badge-done" if pct == 100 else ("badge-progress" if pct > 0 else "badge-pending")
            rows.append(
                f"<tr><td>{e(r.get('atividade', r.get('descricao', '')))}</td>"
                f"<td>"
                f'<div class="prog-wrap"><div class="prog-fill" style="width:{pct}%"></div></div>'
                f'<span class="prog-pct">{pct}%</span>'
                f"</td>"
                f'<td><span class="badge {sc}">{e(status)}</span></td></tr>'
            )
        return "\n".join(rows)

    @staticmethod
    def _equip_rows(items: list) -> str:
        e = RDOService._e
        if not items:
            return '<tr><td colspan="3" class="empty-row">Nenhum equipamento registrado.</td></tr>'
        rows = []
        for r in items[:25]:
            status = r.get("status", "Operando")
            sc = "badge-done" if status == "Operando" else ("badge-pending" if status == "Parado" else "badge-warn")
            rows.append(
                f"<tr><td>{e(r.get('equipamento', r.get('descricao', '')))}</td>"
                f'<td class="center">{e(r.get("quantidade", 1))}</td>'
                f'<td class="center"><span class="badge {sc}">{e(status)}</span></td></tr>'
            )
        return "\n".join(rows)

    @staticmethod
    def _material_rows(items: list) -> str:
        e = RDOService._e
        if not items:
            return '<tr><td colspan="3" class="empty-row">Nenhum material registrado.</td></tr>'
        return "\n".join(
            f"<tr><td>{e(r.get('material', r.get('descricao', '')))}</td>"
            f'<td class="center">{e(r.get("quantidade", "—"))}</td>'
            f'<td class="center">{e(r.get("unidade", "un"))}</td></tr>'
            for r in items[:25]
        )

    @staticmethod
    def _evidence_grid(items: list) -> str:
        if not items:
            return ""
        cards = []
        for item in items[:20]:
            url = item.get("foto_url", "")
            caption = RDOService._e(item.get("legenda") or "")
            analysis = RDOService._e(item.get("analise_vision") or "")
            ts = RDOService._fmt_ts(item.get("timestamp_foto"))
            cards.append(f"""
            <div class="ev-card">
              <img src="{url}" class="ev-img" loading="lazy" />
              <div class="ev-meta">
                {f'<div class="ev-ts">{ts}</div>' if ts != "—" else ""}
                {f'<div class="ev-cap">{caption}</div>' if caption else ""}
                {f'<div class="ev-ai">🤖 {analysis}</div>' if analysis else ""}
              </div>
            </div>""")
        return f'<div class="ev-grid">{"".join(cards)}</div>'

    @staticmethod
    def build_html(rdo_data: Dict[str, Any], is_preview: bool = False) -> str:
        e = RDOService._e

        contrato   = e(rdo_data.get("contrato") or "SEM-CONTRATO")
        data_rdo   = RDOService._fmt_date(rdo_data.get("data") or datetime.now().strftime("%Y-%m-%d"))

        projeto    = e(rdo_data.get("projeto") or "—")
        cliente    = e(rdo_data.get("cliente") or "—")
        localizacao= e(rdo_data.get("localizacao") or "—")
        clima      = e(rdo_data.get("condicao_climatica") or rdo_data.get("clima") or "—")
        turno      = e(rdo_data.get("turno") or "—")
        tipo_tarefa  = e(rdo_data.get("tipo_tarefa") or "Diário de Obra")
        orientacao   = e(rdo_data.get("orientacao") or "")
        km_perc      = rdo_data.get("km_percorrido")
        km_str       = f"{float(km_perc):.2f} km" if km_perc else "—"
        houve_intr = bool(rdo_data.get("houve_interrupcao"))
        motivo     = e((rdo_data.get("motivo_interrupcao") or "—")[:120])
        obs        = (rdo_data.get("observacoes") or "").strip()
        id_rdo     = e(rdo_data.get("id_rdo") or "")
        mestre     = e(rdo_data.get("mestre_id") or "")
        signatory_name = e(rdo_data.get("signatory_name") or "")
        signatory_doc  = e(rdo_data.get("signatory_doc") or "")
        signatory_sig_b64 = rdo_data.get("signatory_sig_b64") or ""
        epi_foto_url = rdo_data.get("epi_foto_url") or ""
        ferramentas_foto_url = rdo_data.get("ferramentas_foto_url") or ""
        ai_text    = (rdo_data.get("ai_summary") or "").strip()
        status     = (rdo_data.get("status") or "finalizado").upper()

        # Computed duration from GPS timestamps
        checkin_ts  = rdo_data.get("checkin_timestamp") or ""
        checkout_ts = rdo_data.get("checkout_timestamp") or ""
        duracao_str = "—"
        h_ini = "—"
        h_fim = "—"
        try:
            if checkin_ts:
                dt_in = datetime.fromisoformat(str(checkin_ts).replace("Z", "+00:00"))
                h_ini = dt_in.strftime("%H:%M")
            if checkout_ts:
                dt_out = datetime.fromisoformat(str(checkout_ts).replace("Z", "+00:00"))
                h_fim = dt_out.strftime("%H:%M")
            if checkin_ts and checkout_ts:
                mins = int((dt_out - dt_in).total_seconds() / 60)
                if mins > 0:
                    duracao_str = f"{mins // 60:02d}h{mins % 60:02d}m"
        except Exception:
            pass

        # Distance in GPS block
        checkin_dist  = rdo_data.get("checkin_distancia_obra") or 0.0
        checkout_dist = rdo_data.get("checkout_distancia_obra") or 0.0

        atividades   = rdo_data.get("atividades", [])
        evidencias   = rdo_data.get("evidencias", [])

        # Sub-sections
        gps_checkin  = RDOService._build_gps_row(
            "Check-in",
            rdo_data.get("checkin_lat"), rdo_data.get("checkin_lng"),
            rdo_data.get("checkin_endereco"), rdo_data.get("checkin_timestamp"),
            distancia=checkin_dist,
        )
        gps_checkout = RDOService._build_gps_row(
            "Check-out",
            rdo_data.get("checkout_lat"), rdo_data.get("checkout_lng"),
            rdo_data.get("checkout_endereco"), rdo_data.get("checkout_timestamp"),
            distancia=checkout_dist,
        )

        activity_rows = RDOService._activity_rows(atividades)
        evidence_html = RDOService._evidence_grid(evidencias)

        obs_block = (
            f'<div class="obs-box">{_html_mod.escape(obs).replace(chr(10), "<br>")}</div>'
            if obs else
            '<p class="empty-row" style="padding:10px 12px;">Sem observações para este dia.</p>'
        )

        # Signature block — support base64 data URL
        if signatory_sig_b64 and signatory_sig_b64.startswith("data:"):
            sig_block = f'<img src="{signatory_sig_b64}" style="max-height:72px;display:block;margin-bottom:4px;" />'
        else:
            sig_block = '<div style="height:52px;border-bottom:0.5px solid #ccc;margin-bottom:4px;"></div>'

        ai_block = (
            f'<div class="ai-content"><pre style="white-space:pre-wrap;font-family:inherit;margin:0;">{_html_mod.escape(ai_text)}</pre></div>'
            if ai_text else
            '<div class="ai-pending">⏳ Análise sendo processada…</div>'
        )

        intr_cls  = 'class="info-label danger"' if houve_intr else 'class="info-label"'
        intr_vcls = 'class="info-value danger-bg"' if houve_intr else 'class="info-value"'
        intr_val  = f"SIM — {motivo}" if houve_intr else "NÃO"

        watermark     = '<div class="watermark">RASCUNHO</div>' if is_preview else ""
        preview_badge = '<span class="preview-badge">RASCUNHO</span>' if is_preview else ""
        status_cls    = "status-draft" if is_preview else "status-final"

        # EPI photo slot
        epi_section = ""
        if epi_foto_url:
            epi_section = f"""
            <div class="section-hdr"><div class="sec-badge">🦺</div><div class="sec-title">Equipe com EPIs</div></div>
            <div class="ev-grid"><div class="ev-card"><img src="{epi_foto_url}" class="ev-img" loading="lazy" /></div></div>"""

        # Ferramentas photo slot
        ferramentas_section = ""
        if ferramentas_foto_url:
            ferramentas_section = f"""
            <div class="section-hdr"><div class="sec-badge">🔧</div><div class="sec-title">Ferramentas Limpas e Organizadas</div></div>
            <div class="ev-grid"><div class="ev-card"><img src="{ferramentas_foto_url}" class="ev-img" loading="lazy" /></div></div>"""

        photos_section = (
            f"""<div class="section-hdr">
              <div class="sec-badge">📷</div>
              <div class="sec-title">Registro Fotográfico ({len(evidencias)} foto{'s' if len(evidencias)!=1 else ''})</div>
            </div>
            {evidence_html}"""
            if evidencias else ""
        )

        emissao = datetime.now().strftime("%d/%m/%Y às %H:%M")

        css = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'IBM Plex Sans', 'Arial', sans-serif; background: #fff; color: #1a1a1a; font-size: 9pt; line-height: 1.45; }

/* ── Header ── */
.header { background: #0B1A15; color: #fff; padding: 14px 22px 12px; border-top: 3px solid #C98B2A; display: flex; justify-content: space-between; align-items: center; gap: 20px; }
.hdr-left { flex: 1; }
.brand { display: flex; align-items: baseline; gap: 6px; margin-bottom: 2px; }
.brand-main { font-size: 20pt; font-weight: 700; color: #fff; letter-spacing: -0.5px; }
.brand-accent { font-size: 20pt; font-weight: 700; color: #C98B2A; letter-spacing: -0.5px; }
.brand-doc { font-size: 8pt; color: #90B0A8; margin-top: 2px; letter-spacing: 1px; text-transform: uppercase; }
.preview-badge { display: inline-block; background: #C0392B; color: #fff; font-size: 6pt; font-weight: 700; padding: 2px 8px; border-radius: 3px; letter-spacing: 1.5px; margin-top: 5px; }
.hdr-right { display: flex; gap: 10px; }
.hdr-box { background: #162820; border-radius: 6px; padding: 8px 16px; text-align: center; min-width: 130px; }
.hdr-box-lbl { font-size: 5.5pt; color: #C98B2A; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; }
.hdr-box-val { font-size: 14pt; font-weight: 700; color: #fff; margin-top: 2px; font-family: 'IBM Plex Mono', monospace; }
.hdr-box-sub { font-size: 7pt; color: #90B0A8; margin-top: 2px; }
.status-final { display: inline-block; background: #1d7066; color: #fff; font-size: 6pt; font-weight: 700; padding: 2px 7px; border-radius: 3px; margin-top: 4px; letter-spacing: 1px; }
.status-draft  { display: inline-block; background: #8a6d0a; color: #fff; font-size: 6pt; font-weight: 700; padding: 2px 7px; border-radius: 3px; margin-top: 4px; letter-spacing: 1px; }

/* ── Content wrapper ── */
.content { padding: 10px 22px 0; }

/* ── Info grid ── */
.info-grid { display: grid; grid-template-columns: 90px 1fr 90px 1fr; border: 0.5px solid #D4C8A8; margin-bottom: 8px; }
.info-label { background: #ECEAE0; font-weight: 600; font-size: 7pt; text-transform: uppercase; letter-spacing: 0.3px; padding: 6px 8px; border-bottom: 0.3px solid #D4C8A8; border-right: 0.5px solid #D4C8A8; display: flex; align-items: center; }
.info-value { background: #F8F7F2; font-size: 8.5pt; padding: 6px 8px; border-bottom: 0.3px solid #D4C8A8; border-right: 0.5px solid #D4C8A8; display: flex; align-items: center; word-break: break-word; }
.info-label.danger { color: #C0392B; }
.info-value.danger-bg { background: #FAE5E5; }

/* ── KPI bar ── */
.kpi-bar { background: #162820; display: flex; border-radius: 6px; overflow: hidden; margin-bottom: 8px; }
.kpi-item { flex: 1; text-align: center; padding: 10px 6px; border-right: 0.5px solid #2a3a38; }
.kpi-item:last-child { border-right: none; }
.kpi-val { font-size: 15pt; font-weight: 700; color: #C98B2A; display: block; font-family: 'IBM Plex Mono', monospace; }
.kpi-lbl { font-size: 6pt; color: #90B0A8; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; display: block; }

/* ── GPS section ── */
.gps-block { background: #F0F7F5; border: 0.5px solid #B0D4CE; border-radius: 4px; padding: 8px 12px; margin-bottom: 8px; display: flex; gap: 12px; }
.gps-row { display: flex; align-items: flex-start; gap: 10px; padding: 6px 0; border-bottom: 0.3px solid #D4E8E4; }
.gps-row:last-child { border-bottom: none; }
.gps-empty { opacity: 0.5; }
.gps-icon { font-size: 14pt; flex-shrink: 0; margin-top: 1px; }
.gps-text { flex: 1; }
.gps-label { display: block; font-size: 7pt; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #1d7066; }
.gps-val { display: block; font-size: 8.5pt; color: #1a1a1a; margin-top: 1px; }
.gps-coords { display: block; font-size: 6.5pt; color: #888; font-family: 'IBM Plex Mono', monospace; margin-top: 1px; }
.gps-none { color: #aaa !important; font-style: italic; }
.dist-badge { display:inline-block; font-size:6.5pt; font-weight:700; padding:1px 6px; border-radius:8px; margin-left:6px; vertical-align:middle; letter-spacing:0.3px; }

/* ── Section header ── */
.section-hdr { background: #0B1A15; color: #fff; padding: 7px 12px; display: flex; align-items: center; gap: 10px; margin-top: 10px; border-left: 3px solid #C98B2A; page-break-inside: avoid; }
.sec-badge { background: #C98B2A; color: #fff; font-size: 7pt; font-weight: 700; min-width: 20px; height: 20px; border-radius: 3px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; padding: 0 4px; }
.sec-title { font-size: 8.5pt; font-weight: 700; letter-spacing: 0.8px; text-transform: uppercase; }

/* ── Tables ── */
table { width: 100%; border-collapse: collapse; font-size: 8pt; page-break-inside: auto; }
thead { display: table-header-group; }
thead th { font-size: 7pt; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; padding: 7px 8px; color: #fff; text-align: left; }
tbody tr:nth-child(odd) td { background: #fff; }
tbody tr:nth-child(even) td { background: #F4F2EA; }
tbody tr td { padding: 6px 8px; border-bottom: 0.3px solid #D4C8A8; vertical-align: middle; }
.center { text-align: center; }
.w50 { width: 50px; } .w60 { width: 60px; } .w80 { width: 80px; } .w110 { width: 110px; }
.total-row td { background: #EAE4D0 !important; font-weight: 600; font-size: 7.5pt; border-top: 1px solid #C98B2A; }
.empty-row { color: #999; font-style: italic; text-align: center; padding: 12px 8px; background: #F8F7F2 !important; }
.tbl-green thead { background: #1d7066; }
.tbl-copper thead { background: #9B6820; }
.tbl-teal thead { background: #1d6e63; }
.tbl-slate thead { background: #355B5A; }

/* ── Progress bar ── */
.prog-wrap { display: inline-block; width: 60px; height: 6px; background: #E0DDD4; border-radius: 3px; vertical-align: middle; margin-right: 4px; overflow: hidden; }
.prog-fill { height: 100%; background: linear-gradient(90deg, #2A9D8F, #1d7066); border-radius: 3px; }
.prog-pct { font-size: 8pt; font-weight: 600; color: #1d7066; vertical-align: middle; }

/* ── Badges ── */
.badge { display: inline-block; font-size: 6.5pt; font-weight: 700; padding: 2px 7px; border-radius: 10px; letter-spacing: 0.3px; }
.badge-done { background: #D4EDE9; color: #1d7066; }
.badge-progress { background: #FFF3CC; color: #8a6d0a; }
.badge-pending { background: #FDECEA; color: #C0392B; }
.badge-warn { background: #FCE8D0; color: #9B4400; }

/* ── Observations ── */
.obs-box { background: #F8F7F2; border: 0.5px solid #D4C8A8; padding: 10px 12px; font-size: 8.5pt; line-height: 1.65; white-space: pre-wrap; word-break: break-word; }

/* ── Evidence photos ── */
.ev-grid { display: flex; flex-wrap: wrap; gap: 8px; padding: 8px 0; }
.ev-card { width: 160px; border: 0.5px solid #D4C8A8; border-radius: 4px; overflow: hidden; }
.ev-img { width: 100%; height: 110px; object-fit: cover; display: block; }
.ev-meta { padding: 5px 6px; background: #F8F7F2; font-size: 7pt; }
.ev-ts { color: #888; margin-bottom: 2px; }
.ev-cap { font-weight: 600; color: #1a1a1a; word-break: break-word; }
.ev-ai { color: #1d7066; margin-top: 3px; font-style: italic; font-size: 6.5pt; }

/* ── AI Analysis ── */
.ai-box { background: #F0F7F5; border: 0.5px solid #B0D4CE; border-left: 3px solid #2A9D8F; border-radius: 4px; padding: 10px 14px; margin-top: 2px; }
.ai-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.ai-icon { font-size: 14pt; }
.ai-title { font-size: 8pt; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #1d7066; }
.ai-content { font-size: 8pt; line-height: 1.65; color: #1a1a1a; }
.ai-pending { color: #999; font-style: italic; font-size: 8pt; }

/* ── Signature ── */
.signatures { display: flex; gap: 14px; margin-top: 12px; }
.sig-box { flex: 1; border: 0.5px solid #D4C8A8; background: #F8F7F2; padding: 8px 10px; min-height: 64px; }
.sig-lbl { font-weight: 700; font-size: 6.5pt; text-transform: uppercase; color: #0B1A15; letter-spacing: 0.3px; }
.sig-sub { font-size: 6.5pt; color: #888; margin-top: 16px; border-top: 0.5px solid #D4C8A8; padding-top: 4px; }

/* ── Footer ── */
.footer { background: #0B1A15; color: #fff; padding: 7px 22px; display: flex; justify-content: space-between; align-items: center; margin-top: 12px; border-top: 1.5px solid #C98B2A; }
.footer-l { font-weight: 700; font-size: 7pt; color: #C98B2A; }
.footer-c { font-size: 6.5pt; color: #90B0A8; }
.footer-r { font-size: 7pt; color: #fff; }

/* ── Watermark ── */
.watermark { position: fixed; top: 45%; left: 50%; transform: translate(-50%,-50%) rotate(35deg); font-size: 80pt; font-weight: 900; color: rgba(0,0,0,0.04); pointer-events: none; z-index: 999; letter-spacing: 6px; }
"""

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body>
{watermark}

<div class="header">
  <div class="hdr-left">
    <div class="brand">
      <span class="brand-main">BOMTEMPO</span>
      <span class="brand-accent">ENGENHARIA</span>
    </div>
    <div class="brand-doc">Relatório Diário de Obra — v2</div>
    {preview_badge}
    <div style="margin-top:4px;"><span class="{status_cls}">{status}</span></div>
  </div>
  <div class="hdr-right">
    <div class="hdr-box">
      <div class="hdr-box-lbl">Contrato</div>
      <div class="hdr-box-val">{contrato}</div>
      <div class="hdr-box-sub">{clima}</div>
    </div>
    <div class="hdr-box">
      <div class="hdr-box-lbl">Data</div>
      <div class="hdr-box-val" style="font-size:11pt;">{data_rdo}</div>
      <div class="hdr-box-sub">{turno}</div>
    </div>
  </div>
</div>

<div class="content">

  <!-- Info Grid -->
  <div class="info-grid">
    <div class="info-label">Projeto</div><div class="info-value">{projeto}</div>
    <div class="info-label">Cliente</div><div class="info-value">{cliente}</div>
    <div class="info-label">Localização</div><div class="info-value">{localizacao}</div>
    <div class="info-label">Horário</div><div class="info-value">{h_ini} – {h_fim} <span style="color:#888;margin-left:6px;">({duracao_str})</span></div>
    <div class="info-label">Tipo Tarefa</div><div class="info-value">{tipo_tarefa}</div>
    <div class="info-label">Orientação</div><div class="info-value">{orientacao if orientacao else '—'}</div>
    <div class="info-label">Mestre</div><div class="info-value">{mestre}</div>
    <div class="info-label">ID RDO</div><div class="info-value" style="font-size:7.5pt;font-family:'IBM Plex Mono',monospace;">{id_rdo}</div>
    <div {intr_cls}>Interrupção</div><div {intr_vcls}>{intr_val}</div>
    <div class="info-label">Emissão</div><div class="info-value">{emissao}</div>
    <div class="info-label">Responsável</div><div class="info-value">{signatory_name or '—'}</div>
    <div class="info-label">Doc. (CPF/RG)</div><div class="info-value">{signatory_doc or '—'}</div>
  </div>

  <!-- KPI Bar -->
  <div class="kpi-bar">
    <div class="kpi-item"><span class="kpi-val">{len(atividades)}</span><span class="kpi-lbl">Atividades</span></div>
    <div class="kpi-item"><span class="kpi-val">{len(evidencias)}</span><span class="kpi-lbl">Fotos</span></div>
    <div class="kpi-item"><span class="kpi-val">{duracao_str}</span><span class="kpi-lbl">Duração</span></div>
    <div class="kpi-item"><span class="kpi-val">{km_str}</span><span class="kpi-lbl">Km percorrido</span></div>
  </div>

  <!-- GPS Timeline -->
  <div class="gps-block">
    {gps_checkin}
    {gps_checkout}
  </div>

  <!-- EPI Photo -->
  {epi_section}

  <!-- Atividades -->
  <div class="section-hdr"><div class="sec-badge">1</div><div class="sec-title">Serviços Executados</div></div>
  <table class="tbl-teal">
    <thead><tr><th>Atividade / Descrição</th><th class="center w110">Progresso</th><th class="center w80">Status</th></tr></thead>
    <tbody>{activity_rows}</tbody>
  </table>

  <!-- Fotos do Dia (se houver) -->
  {photos_section}

  <!-- Observações -->
  <div class="section-hdr"><div class="sec-badge">📝</div><div class="sec-title">Observações Gerais</div></div>
  {obs_block}

  <!-- Ferramentas Photo -->
  {ferramentas_section}

  <!-- Análise IA -->
  <div class="section-hdr"><div class="sec-badge">🤖</div><div class="sec-title">Análise Inteligente — BTP AI</div></div>
  <div class="ai-box">
    <div class="ai-header">
      <span class="ai-icon">🤖</span>
      <span class="ai-title">Resumo Executivo Gerado por IA</span>
    </div>
    {ai_block}
  </div>

  <!-- Assinatura -->
  <div class="signatures">
    <div class="sig-box">
      <div class="sig-lbl">Mestre de Obras / Responsável</div>
      {sig_block}
      <div class="sig-sub">{signatory_name or 'Assinatura digital'}{(' — ' + signatory_doc) if signatory_doc else ''} — {data_rdo}</div>
    </div>
    <div class="sig-box">
      <div class="sig-lbl">Engenheiro Responsável / Fiscal</div>
      <div class="sig-sub">Data: {data_rdo} &nbsp;|&nbsp; Rubrica: ________________</div>
    </div>
  </div>
</div>

<div class="footer">
  <div class="footer-l">BOMTEMPO INTELLIGENCE</div>
  <div class="footer-c">RDO{f' · {id_rdo}' if id_rdo else ''} · Contrato {contrato} · {data_rdo} · Emitido em {emissao}</div>
  <div class="footer-r">Relatório Diário de Obra</div>
</div>
</body>
</html>"""

    # ── PDF Generation ──────────────────────────────────────────────────────

    @staticmethod
    def generate_pdf(
        rdo_data: Dict[str, Any],
        is_preview: bool = False,
        id_rdo: str = "",
    ) -> tuple:
        """Returns (pdf_path: str, pdf_url: str)."""
        try:
            Config.RDO_PDF_DIR.mkdir(parents=True, exist_ok=True)
            contrato = rdo_data.get("contrato", "X")
            data     = rdo_data.get("data", datetime.now().strftime("%Y-%m-%d"))

            if is_preview:
                filename = f"RDO2-PREVIEW-{contrato}-{data}.pdf"
            elif id_rdo:
                filename = f"{id_rdo}.pdf"
            else:
                filename = f"RDO2-{contrato}-{data}.pdf"

            pdf_path = Config.RDO_PDF_DIR / filename
            html = RDOService.build_html(rdo_data, is_preview=is_preview)
            html_to_pdf(html, pdf_path)
            logger.info(f"✅ RDO2 PDF gerado: {pdf_path.name}")
            return str(pdf_path), ""
        except Exception as e:
            logger.error(f"❌ generate_pdf: {e}")
            return "", ""

    # ── Database operations ──────────────────────────────────────────────────

    @staticmethod
    def upsert_draft(rdo_data: Dict[str, Any], mestre_id: str = "") -> str:
        """Upsert rdo_master com status=rascunho. Retorna id_rdo."""
        id_rdo = rdo_data.get("id_rdo") or _gen_id(rdo_data.get("contrato", ""))
        record = {
            "id_rdo":              id_rdo,
            "status":              "rascunho",
            "contrato":            rdo_data.get("contrato") or "",
            "projeto":             rdo_data.get("projeto") or "",
            "cliente":             rdo_data.get("cliente") or "",
            "localizacao":         rdo_data.get("localizacao") or "",
            "data":                rdo_data.get("data") or datetime.now().strftime("%Y-%m-%d"),
            "turno":               rdo_data.get("turno") or "Diurno",
            "hora_inicio":         rdo_data.get("hora_inicio") or "07:00",
            "hora_termino":        rdo_data.get("hora_termino") or "17:00",
            "tipo_tarefa":         rdo_data.get("tipo_tarefa") or "Diário de Obra",
            "orientacao":          rdo_data.get("orientacao") or "",
            "km_percorrido":       rdo_data.get("km_percorrido"),
            "condicao_climatica":  rdo_data.get("condicao_climatica") or rdo_data.get("clima") or "Ensolarado",
            "houve_interrupcao":   bool(rdo_data.get("houve_interrupcao")),
            "motivo_interrupcao":  rdo_data.get("motivo_interrupcao") or "",
            "observacoes":         rdo_data.get("observacoes") or "",
            "checkin_timestamp":   rdo_data.get("checkin_timestamp"),
            "checkin_lat":         rdo_data.get("checkin_lat"),
            "checkin_lng":         rdo_data.get("checkin_lng"),
            "checkin_endereco":    rdo_data.get("checkin_endereco") or "",
            "checkout_lat":        rdo_data.get("checkout_lat"),
            "checkout_lng":        rdo_data.get("checkout_lng"),
            "checkout_endereco":   rdo_data.get("checkout_endereco") or "",
            "checkout_timestamp":  rdo_data.get("checkout_timestamp"),
            "signatory_name":      rdo_data.get("signatory_name") or "",
            "signatory_doc":       rdo_data.get("signatory_doc") or "",
            "signatory_sig_b64":   rdo_data.get("signatory_sig_b64") or "",
            "epi_foto_url":        rdo_data.get("epi_foto_url") or "",
            "ferramentas_foto_url": rdo_data.get("ferramentas_foto_url") or "",
            "mestre_id":           mestre_id or rdo_data.get("mestre_id") or "",
            "updated_at":          datetime.now().isoformat(),
        }
        record = {k: v for k, v in record.items() if v is not None}
        sb_upsert("rdo_master", record, on_conflict="id_rdo")
        RDOService._save_sub_items(id_rdo, rdo_data)
        return id_rdo

    @staticmethod
    def finalize_rdo(
        id_rdo: str,
        pdf_path: str,
        pdf_url: str,
        rdo_data: Dict[str, Any],
    ) -> bool:
        """Marca RDO como finalizado e salva PDF + checkout + assinatura."""
        patch: Dict[str, Any] = {
            "status":           "finalizado",
            "pdf_path":         pdf_path,
            "pdf_url":          pdf_url,
            "updated_at":       datetime.now().isoformat(),
        }
        for field in [
            "checkout_timestamp", "checkout_lat", "checkout_lng", "checkout_endereco",
            "assinatura_url", "assinatura_nome",
        ]:
            if rdo_data.get(field) is not None:
                patch[field] = rdo_data[field]
        return sb_update("rdo_master", {"id_rdo": id_rdo}, patch)

    @staticmethod
    def update_pdf_info(id_rdo: str, pdf_url: str) -> bool:
        return sb_update("rdo_master", {"id_rdo": id_rdo}, {"pdf_url": pdf_url})

    @staticmethod
    def upload_pdf(pdf_path: str, id_rdo: str) -> str:
        try:
            with open(pdf_path, "rb") as f:
                data = f.read()
            url = sb_storage_upload("rdo-pdfs", f"{id_rdo}.pdf", data, "application/pdf")
            return url or ""
        except Exception as e:
            logger.error(f"❌ upload_pdf: {e}")
            return ""

    @staticmethod
    def upload_evidence(id_rdo: str, file_bytes: bytes, content_type: str, filename: str) -> str:
        """Upload foto para bucket rdo-evidencias. Retorna URL pública."""
        try:
            path = f"{id_rdo}/{filename}"
            url = sb_storage_upload("rdo-evidencias", path, file_bytes, content_type)
            return url or ""
        except Exception as e:
            logger.error(f"❌ upload_evidence: {e}")
            return ""

    @staticmethod
    def save_evidence(id_rdo: str, foto_url: str, legenda: str = "") -> Optional[Dict]:
        return sb_insert("rdo_evidencias", {
            "id_rdo": id_rdo,
            "foto_url": foto_url,
            "legenda": legenda,
        })

    @staticmethod
    def get_full_rdo(id_rdo: str) -> Dict[str, Any]:
        rows = sb_select("rdo_master", filters={"id_rdo": id_rdo})
        if not rows:
            return {}
        rdo = dict(rows[0])
        rdo["mao_obra"]     = sb_select("rdo_mao_obra",     filters={"id_rdo": id_rdo}) or []
        rdo["atividades"]   = sb_select("rdo_atividades",   filters={"id_rdo": id_rdo}) or []
        rdo["equipamentos"] = sb_select("rdo_equipamentos", filters={"id_rdo": id_rdo}) or []
        rdo["materiais"]    = sb_select("rdo_materiais",    filters={"id_rdo": id_rdo}) or []
        rdo["evidencias"]   = sb_select("rdo_evidencias",   filters={"id_rdo": id_rdo}) or []
        return rdo

    @staticmethod
    def get_by_token(view_token: str) -> Dict[str, Any]:
        rows = sb_select("rdo_master", filters={"view_token": view_token})
        if not rows:
            return {}
        return RDOService.get_full_rdo(rows[0]["id_rdo"])

    @staticmethod
    def get_rdos_list(
        contrato: str = "",
        mestre_id: str = "",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        filters: Dict[str, Any] = {}
        if contrato:
            filters["contrato"] = contrato
        if mestre_id:
            filters["mestre_id"] = mestre_id
        return sb_select("rdo_master", filters=filters, order="created_at.desc", limit=limit) or []

    @staticmethod
    def get_active_draft(mestre_id: str, contrato: str = "") -> Optional[Dict[str, Any]]:
        """Retorna rascunho ativo do mestre (se existir)."""
        filters: Dict[str, Any] = {"status": "rascunho", "mestre_id": mestre_id}
        if contrato:
            filters["contrato"] = contrato
        rows = sb_select("rdo_master", filters=filters, order="updated_at.desc", limit=1)
        return dict(rows[0]) if rows else None

    @staticmethod
    def get_all_rdos(limit: int = 500) -> List[Dict[str, Any]]:
        """Retorna todos os RDOs finalizados (admin view). Alias para get_rdos_list sem filtros."""
        return sb_select("rdo_master", order="created_at.desc", limit=limit) or []

    @staticmethod
    def delete_draft(id_rdo: str) -> bool:
        return sb_delete("rdo_master", {"id_rdo": id_rdo})

    # ── Geocoding utilities ──────────────────────────────────────────────────

    @staticmethod
    def backfill_obras_geocode(dry_run: bool = False) -> dict:
        """Forward-geocode all obras rows that have Localização but no lat/lng.
        Returns {"updated": N, "failed": N, "skipped": N}.
        Safe to run multiple times (skips rows that already have coords).
        """
        import time
        rows = sb_select("obras", limit=500)
        updated = failed = skipped = 0
        for r in rows:
            if r.get("lat") or not r.get("localizacao"):
                skipped += 1
                continue
            address = str(r["localizacao"]).strip()
            lat, lng = _forward_geocode(address)
            if lat:
                if not dry_run:
                    sb_update("obras", {"id": r.get("id")}, {"lat": lat, "lng": lng})
                updated += 1
                logger.info(f"✅ Geocoded '{address}' → {lat:.5f}, {lng:.5f}")
            else:
                failed += 1
                logger.warning(f"⚠️  Geocode sem resultado: '{address}'")
            time.sleep(1.1)  # Nominatim rate-limit: 1 req/s
        return {"updated": updated, "failed": failed, "skipped": skipped}

    # ── Obra GPS coords ──────────────────────────────────────────────────────

    @staticmethod
    def get_obra_coords(contrato: str) -> Tuple[float, float]:
        """Look up lat/lng from the obras table for a given contrato. Returns (0, 0) if missing."""
        if not contrato:
            return 0.0, 0.0
        try:
            rows = sb_select("obras", filters={"contrato": contrato}, limit=1)
            if rows:
                r = rows[0]
                lat = float(r.get("lat") or r.get("latitude") or 0.0)
                lng = float(r.get("lng") or r.get("longitude") or 0.0)
                return lat, lng
        except Exception as e:
            logger.warning(f"get_obra_coords({contrato}): {e}")
        return 0.0, 0.0

    # ── Evidence pipeline ─────────────────────────────────────────────────────

    @staticmethod
    def process_evidence(
        id_rdo: str,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        legenda: str,
        mestre: str,
        contrato: str,
        data: str,
    ) -> Dict[str, str]:
        """Full pipeline: EXIF extract → watermark → upload → geocode → DB insert.
        Returns a dict suitable for evidencias_items display.
        """
        # 1. EXIF GPS
        exif_lat, exif_lng = _extract_exif_gps(file_bytes)

        # 2. Build watermark metadata
        now = datetime.now()
        rede_str  = _pt_datetime_str(now)
        # If EXIF has a timestamp use it as "local", else same as network
        local_str = rede_str

        # Reverse-geocode now (for watermark address breakdown)
        address_parts: Dict[str, str] = {}
        if exif_lat and exif_lng:
            try:
                import httpx
                resp = httpx.get(
                    "https://nominatim.openstreetmap.org/reverse",
                    params={"format":"json","lat":exif_lat,"lon":exif_lng,"zoom":16,"addressdetails":1},
                    headers={"User-Agent":"BomtempoRDO/2.0"},
                    timeout=8,
                )
                if resp.status_code == 200:
                    addr = resp.json().get("address", {})
                    road   = addr.get("road") or addr.get("pedestrian") or ""
                    number = addr.get("house_number") or ""
                    address_parts["address"]      = f"{road}{', ' + number if number else ''}"
                    address_parts["neighborhood"] = addr.get("suburb") or addr.get("neighbourhood") or ""
                    city   = addr.get("city") or addr.get("town") or addr.get("municipality") or ""
                    state  = addr.get("state_district") or addr.get("state") or ""
                    # Abbreviate state to 2 chars if long
                    state_ab = state[:2].upper() if len(state) > 3 else state.upper()
                    address_parts["city"]         = f"{city} {state_ab}".strip()
                    address_parts["postcode"]     = addr.get("postcode") or ""
            except Exception:
                pass

        # Fetch map thumbnail (best-effort, won't block on failure)
        map_bytes = None
        if exif_lat and exif_lng:
            map_bytes = _fetch_map_thumbnail(exif_lat, exif_lng)

        wm_meta: Dict[str, Any] = {
            "rede_time":    rede_str,
            "local_time":   local_str,
            "lat":          exif_lat if exif_lat else None,
            "lng":          exif_lng if exif_lng else None,
            "address":      address_parts.get("address", ""),
            "neighborhood": address_parts.get("neighborhood", ""),
            "city":         address_parts.get("city", ""),
            "postcode":     address_parts.get("postcode", ""),
            "contrato":     contrato,
            "mestre":       mestre,
            "data":         data,
            "map_bytes":    map_bytes,
        }
        watermarked = _apply_watermark(file_bytes, wm_meta, content_type)

        # 3. Upload to Supabase Storage
        foto_url = RDOService.upload_evidence(id_rdo, watermarked, content_type, filename)

        # 4. Reverse geocode EXIF GPS
        exif_endereco = ""
        if exif_lat and exif_lng:
            exif_endereco = _reverse_geocode(exif_lat, exif_lng)

        # 5. Persist to rdo_evidencias
        record: Dict[str, Any] = {
            "id_rdo":        id_rdo,
            "foto_url":      foto_url,
            "legenda":       legenda,
            "timestamp_foto": datetime.now().isoformat(),
        }
        if exif_lat:
            record["exif_lat"] = exif_lat
            record["exif_lng"] = exif_lng
        if exif_endereco:
            record["exif_endereco"] = exif_endereco
        sb_insert("rdo_evidencias", record)

        return {
            "foto_url":      foto_url,
            "legenda":       legenda,
            "exif_lat":      str(exif_lat) if exif_lat else "",
            "exif_lng":      str(exif_lng) if exif_lng else "",
            "exif_endereco": exif_endereco,
        }

    # ── AI ───────────────────────────────────────────────────────────────────

    @staticmethod
    def analyze_with_ai(rdo_data: Dict[str, Any], id_rdo: str) -> None:
        """Fire-and-forget: analisa RDO e salva ai_summary no banco."""
        def _run():
            try:
                acts = "\n".join(
                    f"  - {r.get('atividade', r.get('descricao','?'))} ({r.get('progresso_percentual',0)}%) [{r.get('status','Em andamento')}]"
                    for r in rdo_data.get("atividades", [])[:10]
                )
                checkin_ts  = rdo_data.get("checkin_timestamp") or ""
                checkout_ts = rdo_data.get("checkout_timestamp") or ""
                checkin_end = rdo_data.get("checkin_endereco") or ""
                checkout_end = rdo_data.get("checkout_endereco") or ""
                gps_info = ""
                if checkin_ts:
                    gps_info += f"\nCheck-in: {checkin_ts[:16]} @ {checkin_end}"
                if checkout_ts:
                    gps_info += f"\nCheck-out: {checkout_ts[:16]} @ {checkout_end}"
                prompt = f"""Você é um consultor sênior de engenharia civil. Analise o RDO abaixo.

RDO {rdo_data.get('id_rdo','')} — {rdo_data.get('data','')}
Contrato: {rdo_data.get('contrato','')} | Projeto: {rdo_data.get('projeto','')}
Clima: {rdo_data.get('condicao_climatica','')} | Turno: {rdo_data.get('turno','')}
Interrupção: {'SIM — ' + (rdo_data.get('motivo_interrupcao') or '') if rdo_data.get('houve_interrupcao') else 'NÃO'}
GPS:{gps_info or ' não registrado'}
Serviços Executados:\n{acts or '  (não informados)'}
Observações: {(rdo_data.get('observacoes') or 'Nenhuma')[:300]}

Responda em português com seções:
## 📊 RESUMO EXECUTIVO
## 🔨 SERVIÇOS EXECUTADOS
## ⚠️ ALERTAS E RISCOS
## 💡 RECOMENDAÇÕES"""
                messages = [
                    {"role": "system", "content": "Seja preciso, direto e profissional. Responda em português."},
                    {"role": "user", "content": prompt},
                ]
                result = ai_client.query(messages)
                sb_update("rdo_master", {"id_rdo": id_rdo}, {"ai_summary": result})
                logger.info(f"✅ AI summary salvo: {id_rdo}")
            except Exception as e:
                logger.error(f"❌ AI analyze: {e}")

        threading.Thread(target=_run, daemon=True).start()

    @staticmethod
    def send_email(
        recipients: List[str],
        rdo_data: Dict[str, Any],
        pdf_path: str,
        view_url: str,
        ai_text: str = "",
    ) -> None:
        """Fire-and-forget email send."""
        from bomtempo.core.email_service import EmailService

        def _run():
            try:
                EmailService.send_rdo2_email(recipients, rdo_data, pdf_path, view_url, ai_text)
            except Exception as e:
                logger.error(f"❌ send_email rdo2: {e}")

        threading.Thread(target=_run, daemon=True).start()

    # ── Private ──────────────────────────────────────────────────────────────

    @staticmethod
    def _save_sub_items(id_rdo: str, rdo_data: Dict[str, Any]) -> None:
        # Only save atividades — mao_obra, equipamentos, materiais removed from form
        sb_delete("rdo_atividades", {"id_rdo": id_rdo})

        for item in (rdo_data.get("atividades") or []):
            atv = item.get("atividade") or item.get("descricao") or ""
            if atv:
                sb_insert("rdo_atividades", {
                    "id_rdo":               id_rdo,
                    "atividade":            atv,
                    "progresso_percentual": int(item.get("progresso_percentual") or item.get("percentual") or 0),
                    "status":               item.get("status") or "Em andamento",
                })


# ── Startup geocode backfill ─────────────────────────────────────────────────

def ensure_geocodes_async() -> None:
    """Run backfill_obras_geocode in a daemon thread at startup (fire-and-forget).
    Only geocodes obras rows that have Localização but no lat/lng yet.
    Safe to call multiple times — skips rows that already have coordinates.

    SQL migrations needed before this module can save new fields:
        ALTER TABLE rdo_master ADD COLUMN IF NOT EXISTS signatory_name text DEFAULT '';
        ALTER TABLE rdo_master ADD COLUMN IF NOT EXISTS signatory_doc text DEFAULT '';
        ALTER TABLE rdo_master ADD COLUMN IF NOT EXISTS signatory_sig_b64 text DEFAULT '';
        ALTER TABLE rdo_master ADD COLUMN IF NOT EXISTS epi_foto_url text DEFAULT '';
        ALTER TABLE rdo_master ADD COLUMN IF NOT EXISTS ferramentas_foto_url text DEFAULT '';
        ALTER TABLE rdo_master ADD COLUMN IF NOT EXISTS checkout_lat float8;
        ALTER TABLE rdo_master ADD COLUMN IF NOT EXISTS checkout_lng float8;
        ALTER TABLE rdo_master ADD COLUMN IF NOT EXISTS checkout_endereco text DEFAULT '';
        ALTER TABLE rdo_master ADD COLUMN IF NOT EXISTS checkout_timestamp timestamptz;
    """
    def _run():
        try:
            result = RDOService.backfill_obras_geocode()
            logger.info(f"🌐 Geocode backfill: {result}")
        except Exception as e:
            logger.warning(f"⚠️ Geocode backfill error: {e}")

    threading.Thread(target=_run, daemon=True).start()


# Run geocode backfill at module import (no-op if all obras already have coords)
ensure_geocodes_async()
