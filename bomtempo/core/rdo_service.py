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
    sb_storage_ensure_bucket,
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

def _fetch_map_thumbnail(lat: float, lng: float, size: Tuple[int,int] = (200, 150)) -> Optional[bytes]:
    """Compõe miniatura de mapa usando tiles OSM diretos + marcador PIL.
    Mais confiável que staticmap.openstreetmap.de (que frequentemente fica offline).
    """
    try:
        import httpx, io as _io, math as _math
        from PIL import Image as _PILImage, ImageDraw as _PILDraw

        ZOOM = 15
        TILE = 256
        n = 2 ** ZOOM

        # Coordenadas do tile central
        tx = int((lng + 180) / 360 * n)
        ty = int((1 - _math.log(_math.tan(_math.radians(lat)) + 1 / _math.cos(_math.radians(lat))) / _math.pi) / 2 * n)

        # Busca 3×3 tiles ao redor (parallel, best-effort)
        tiles: dict = {}
        headers = {"User-Agent": "BomtempoRDO/2.0 (watermark)"}
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                url = f"https://tile.openstreetmap.org/{ZOOM}/{tx+dx}/{ty+dy}.png"
                try:
                    r = httpx.get(url, timeout=4, headers=headers)
                    if r.status_code == 200:
                        tiles[(dx, dy)] = _PILImage.open(_io.BytesIO(r.content)).convert("RGB")
                except Exception:
                    pass

        if not tiles:
            return None

        # Monta imagem 3×3 tiles (768×768)
        canvas = _PILImage.new("RGB", (TILE * 3, TILE * 3), (210, 210, 210))
        for (dx, dy), tile_img in tiles.items():
            canvas.paste(tile_img, ((dx + 1) * TILE, (dy + 1) * TILE))

        # Posição em pixels do ponto exato no canvas 3×3
        fx = (lng + 180) / 360 * n - tx   # fração dentro do tile central (0-1)
        fy = (1 - _math.log(_math.tan(_math.radians(lat)) + 1 / _math.cos(_math.radians(lat))) / _math.pi) / 2 * n - ty
        px = int(TILE + fx * TILE)
        py = int(TILE + fy * TILE)

        # Marcador: pino laranja com borda branca
        draw = _PILDraw.Draw(canvas)
        R = 9
        draw.ellipse([px - R, py - R, px + R, py + R], fill=(201, 139, 42), outline=(255, 255, 255), width=3)
        draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=(255, 255, 255))

        # Recorta e redimensiona centrado no marcador
        crop_w, crop_h = size[0] * 3, size[1] * 3
        left = max(0, px - crop_w // 2)
        top  = max(0, py - crop_h // 2)
        right  = min(canvas.width,  left + crop_w)
        bottom = min(canvas.height, top  + crop_h)
        cropped = canvas.crop((left, top, right, bottom))
        result  = cropped.resize(size, _PILImage.LANCZOS)

        buf = _io.BytesIO()
        result.save(buf, format="PNG")
        return buf.getvalue()

    except Exception as e:
        logger.debug(f"Map thumbnail OSM tiles falhou: {e}")
        return None

def _extract_exif_gps(img_bytes: bytes) -> Tuple[float, float]:
    """Extract GPS lat/lng from image EXIF. Returns (0.0, 0.0) if not found."""
    lat, lng, _ = _extract_exif_full(img_bytes)
    return lat, lng


def _extract_exif_full(img_bytes: bytes) -> Tuple[float, float, Optional[datetime]]:
    """Extrai GPS lat/lng + datetime original do EXIF.
    Returns (lat, lng, datetime_local) — valores 0.0/None se não encontrado.
    """
    try:
        from PIL import Image
        from PIL.ExifTags import GPSTAGS, TAGS

        img = Image.open(io.BytesIO(img_bytes))
        exif_raw = img._getexif()  # type: ignore[attr-defined]
        if not exif_raw:
            return 0.0, 0.0, None

        gps_info: Dict[str, Any] = {}
        dt_original: Optional[datetime] = None

        for tag_id, val in exif_raw.items():
            tag_name = TAGS.get(tag_id, "")
            if tag_name == "GPSInfo":
                for k, v in val.items():
                    gps_info[GPSTAGS.get(k, k)] = v
            elif tag_name in ("DateTimeOriginal", "DateTimeDigitized") and dt_original is None:
                # formato EXIF: "2026:03:15 14:38:27"
                try:
                    dt_original = datetime.strptime(str(val), "%Y:%m:%d %H:%M:%S")
                except Exception:
                    pass

        lat, lng = 0.0, 0.0
        if "GPSLatitude" in gps_info and "GPSLongitude" in gps_info:
            def _dms(dms, ref: str) -> float:
                d, m, s = [float(x) for x in dms]
                dd = d + m / 60 + s / 3600
                return -dd if ref in ("S", "W") else dd
            lat = _dms(gps_info["GPSLatitude"],  gps_info.get("GPSLatitudeRef",  "N"))
            lng = _dms(gps_info["GPSLongitude"], gps_info.get("GPSLongitudeRef", "E"))

        return lat, lng, dt_original
    except Exception as e:
        logger.debug(f"EXIF full extract: {e}")
        return 0.0, 0.0, None


def _apply_watermark(img_bytes: bytes, meta: Dict[str, Any], content_type: str = "image/jpeg") -> bytes:
    """Geolocation audit stamp — full-width bottom panel anchored below the photo.

    Layout:
      ┌────────────────────────────────────────┐
      │            PHOTO (unchanged)           │
      ├══════════════════════════════════════ ═╡  ← copper stripe 4px
      │ TEXT COLUMN (timestamps, GPS, address) │ MAP (35% width, same height) │
      └────────────────────────────────────────┘

    Panel is appended BELOW the image (canvas expands downward) so the photo
    is never cropped or overlaid.

    meta keys:
      rede_time / local_time  – formatted PT timestamps
      local_is_exif / local_is_lastmod – source flags
      lat / lng               – float decimal degrees (optional)
      gps_source              – "exif" | "checkin"
      address / neighborhood / city / postcode – reverse-geocode strings
      contrato / mestre       – RDO metadata
      map_bytes               – bytes|None OSM tile thumbnail
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        w, h = img.size

        # ── Font: proportional to image width, min 28px for readability ──────
        # iPhone 13 portrait = 3024px wide → fsize ≈ 75px (legível em impressão A4)
        # Imagem pequena 800px → fsize ≈ 28px (mínimo seguro)
        fsize = max(28, w // 40)
        fnt = ImageFont.load_default()
        fnt_sm = ImageFont.load_default()
        for fp in [
            "arial.ttf", "Arial.ttf",
            "DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]:
            try:
                fnt    = ImageFont.truetype(fp, size=fsize)
                fnt_sm = ImageFont.truetype(fp, size=max(22, fsize - 8))
                break
            except Exception:
                continue

        # ── Colors ───────────────────────────────────────────────────────────
        WHITE  = (255, 255, 255, 245)
        COPPER = (201, 139,  42, 255)
        MUTED  = (160, 200, 195, 220)
        YELLOW = (240, 210,  50, 240)
        PANEL  = ( 10,  10,  10, 230)   # near-black, high opacity

        # ── Build text lines ──────────────────────────────────────────────────
        # Each entry: (text, font, color)
        text_entries: List[Tuple[str, Any, Any]] = []

        # Row 1-2: timestamps
        if meta.get("rede_time"):
            text_entries.append((f"Rede:    {meta['rede_time']}", fnt, WHITE))
        if meta.get("local_time"):
            if meta.get("local_is_exif"):
                local_label = "EXIF:    "
            elif meta.get("local_is_lastmod"):
                local_label = "Arquivo: "
            else:
                local_label = "Upload:  "
            text_entries.append((f"{local_label}{meta['local_time']}", fnt, WHITE))

        # Row 3-4: GPS DMS coordinates
        lat = meta.get("lat")
        lng = meta.get("lng")
        gps_src = meta.get("gps_source", "exif")
        if lat and lng:
            gps_color = MUTED if gps_src == "exif" else YELLOW
            text_entries.append((_decimal_to_dms(float(lat), True),  fnt_sm, gps_color))
            text_entries.append((_decimal_to_dms(float(lng), False), fnt_sm, gps_color))
            if gps_src == "checkin":
                text_entries.append(("* GPS via check-in do técnico", fnt_sm, YELLOW))

        # Address block
        if meta.get("address"):
            text_entries.append((str(meta["address"])[:60], fnt_sm, WHITE))
        if meta.get("neighborhood"):
            text_entries.append((str(meta["neighborhood"])[:55], fnt_sm, WHITE))
        if meta.get("city"):
            text_entries.append((str(meta["city"])[:55], fnt_sm, WHITE))
        if meta.get("postcode"):
            text_entries.append((str(meta["postcode"]), fnt_sm, MUTED))

        # Warning only when no EXIF AND no checkin GPS
        has_gps = bool(meta.get("lat") and meta.get("lng"))
        if not meta.get("local_is_exif") and not has_gps:
            if meta.get("local_is_lastmod"):
                text_entries.append(("⚠ Data via lastModified — sem EXIF", fnt_sm, YELLOW))
                text_entries.append(("  Foto pode ser anterior ao upload", fnt_sm, YELLOW))
            else:
                text_entries.append(("⚠ Sem metadados EXIF na foto", fnt_sm, YELLOW))
                text_entries.append(("  Autenticidade não verificável", fnt_sm, YELLOW))

        # Branding footer
        text_entries.append((f"BTP Intelligence · {meta.get('contrato', '—')}", fnt_sm, COPPER))

        # ── Measure text column ───────────────────────────────────────────────
        tmp_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        line_h = fsize + max(8, fsize // 5)   # generous line spacing
        pad_x, pad_y = max(24, w // 80), max(16, fsize // 3)

        max_text_w = max(
            (int(tmp_draw.textlength(t, font=f)) for t, f, _ in text_entries),
            default=300,
        )

        # ── Map thumbnail — 30% of image width, uncapped height ─────────────
        text_block_h = len(text_entries) * line_h + pad_y * 2
        map_target_w = int(w * 0.30)
        # Map height matches text block so both columns are the same height
        map_target_h = text_block_h

        map_img = None
        map_bytes_data = meta.get("map_bytes")
        if map_bytes_data and map_target_w > 50 and map_target_h > 40:
            try:
                raw_map = Image.open(io.BytesIO(map_bytes_data)).convert("RGBA")
                raw_map.thumbnail((map_target_w, map_target_h), Image.LANCZOS)
                map_img = raw_map
            except Exception:
                map_img = None

        # ── Panel height: grows to fit ALL content — no cap ───────────────────
        panel_h = max(
            text_block_h,
            (map_img.height + pad_y * 2) if map_img else 0,
        )

        # ── Compose panel (solid dark, font-white — Auvo style) ───────────────
        panel = Image.new("RGBA", (w, panel_h), PANEL)
        draw  = ImageDraw.Draw(panel)

        # Copper accent stripe across top of panel
        stripe = max(3, fsize // 14)
        draw.rectangle([0, 0, w, stripe], fill=(201, 139, 42, 220))

        # Text lines — ALL lines rendered, panel already sized to fit
        y = pad_y + stripe + 2
        for text, fnt_use, clr in text_entries:
            draw.text((pad_x, y), text, font=fnt_use, fill=clr)
            y += line_h

        # Map inset — right column, vertically centred
        if map_img:
            mx = w - map_img.width - pad_x
            my = (panel_h - map_img.height) // 2
            border_px = max(2, fsize // 22)
            brd_w = map_img.width + border_px * 2
            brd_h = map_img.height + border_px * 2
            brd = Image.new("RGBA", (brd_w, brd_h), (201, 139, 42, 180))
            panel.paste(brd, (mx - border_px, my - border_px), brd)
            panel.paste(map_img, (mx, my), map_img)

        # ── Canvas expands BELOW the photo — photo is never overlaid ──────────
        # Total canvas height = photo + panel
        total_h = h + panel_h
        result = Image.new("RGBA", (w, total_h), (10, 10, 10, 255))
        result.paste(img, (0, 0))
        result.paste(panel, (0, h), panel)

        buf = io.BytesIO()
        result.convert("RGB").save(buf, format="JPEG", quality=92, optimize=True)
        return buf.getvalue()
    except Exception as e:
        logger.error(f"❌ Watermark falhou (retornando original): {e}")
        return img_bytes


# ── ID Generation ───────────────────────────────────────────────────────────

def _gen_id(contrato: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = (contrato or "RDO").replace("/", "-").replace(" ", "")[:20]
    return f"RDO2-{safe}-{ts}"


def _gen_view_token() -> str:
    """Generates a URL-safe random token for public RDO viewing."""
    import secrets
    return secrets.token_urlsafe(20)


# ── HTML Builder ────────────────────────────────────────────────────────────

_RDO_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&family=Plus+Jakarta+Sans:wght@400;500;600&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
<script id="tailwind-config">
  tailwind.config = {
    theme: {
      extend: {
        colors: {
          "copper": "#C98B2A",
          "patina": "#2A9D8F",
          "ink": "#081210",
          "paper": "#FAFAFA"
        },
        fontFamily: {
          "headline": ["Rajdhani", "sans-serif"],
          "body": ["Plus Jakarta Sans", "sans-serif"],
          "label": ["JetBrains Mono", "monospace"]
        }
      }
    }
  }
</script>
<style>
  @page { size: A4; margin: 0; }
  body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  @media print {
    body { background: white !important; }
    .no-print { display: none !important; }
    .shadow-2xl { box-shadow: none !important; }
    .page-avoid { page-break-inside: avoid; }
  }
  .material-symbols-outlined {
    font-variation-settings: 'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24;
    vertical-align: middle;
    line-height: 1;
  }
  .copper-accent { border-left: 4px solid #C98B2A; }
  .patina-accent { border-left: 4px solid #2A9D8F; }
  .watermark-rdo {
    position: fixed; top: 45%; left: 50%;
    transform: translate(-50%,-50%) rotate(35deg);
    font-size: 80pt; font-weight: 900;
    color: rgba(0,0,0,0.04); pointer-events: none;
    z-index: 999; letter-spacing: 6px;
    font-family: 'Rajdhani', sans-serif;
  }
</style>
</head>
<body class="bg-zinc-100 font-body text-ink antialiased">
___WATERMARK___
<main class="min-h-screen py-8 flex justify-center items-start">
<article class="w-[210mm] min-h-[297mm] bg-paper shadow-2xl relative flex flex-col">

<!-- ── HEADER ── -->
<header class="flex justify-between items-start border-b-2 border-copper px-12 py-8 bg-white">
  <div class="flex items-center gap-4">
    <div class="w-14 h-14 bg-ink flex items-center justify-center rounded-sm flex-shrink-0">
      <span class="material-symbols-outlined text-copper text-4xl">engineering</span>
    </div>
    <div>
      <h1 class="font-headline text-3xl font-bold tracking-tight text-ink leading-none">RELATÓRIO DIÁRIO DE OBRA</h1>
      <p class="font-label text-[10px] text-ink/50 tracking-widest uppercase mt-1">BOMTEMPO ENGENHARIA — Gestão de Campo</p>
      ___PREVIEW_BADGE___
    </div>
  </div>
  <div class="text-right flex flex-col items-end gap-2">
    ___STATUS_BADGE___
    <div>
      <p class="font-label text-[9px] text-ink/40 uppercase tracking-widest">Contrato</p>
      <p class="font-label text-base font-bold text-ink">___CONTRATO___</p>
    </div>
    <div>
      <p class="font-label text-[9px] text-ink/40 uppercase tracking-widest">Data</p>
      <p class="font-label text-sm font-bold text-ink">___DATA_RDO___</p>
    </div>
  </div>
</header>

<!-- ── BODY ── -->
<div class="px-12 py-6 flex flex-col gap-5 flex-1">

  <!-- INFO GRID -->
  <section class="grid grid-cols-4 gap-x-6 gap-y-3">
    <div class="flex flex-col border-b border-zinc-200 pb-2">
      <span class="font-headline text-[10px] uppercase text-copper font-bold tracking-widest">Projeto</span>
      <span class="font-body font-semibold text-sm">___PROJETO___</span>
    </div>
    <div class="flex flex-col border-b border-zinc-200 pb-2">
      <span class="font-headline text-[10px] uppercase text-copper font-bold tracking-widest">Cliente</span>
      <span class="font-body font-semibold text-sm">___CLIENTE___</span>
    </div>
    <div class="flex flex-col border-b border-zinc-200 pb-2">
      <span class="font-headline text-[10px] uppercase text-copper font-bold tracking-widest">Localização</span>
      <span class="font-body font-semibold text-sm">___LOCALIZACAO___</span>
    </div>
    <div class="flex flex-col border-b border-zinc-200 pb-2">
      <span class="font-headline text-[10px] uppercase text-copper font-bold tracking-widest">Mestre de Obras</span>
      <span class="font-body font-semibold text-sm">___MESTRE___</span>
    </div>
    <div class="flex flex-col border-b border-zinc-200 pb-2">
      <span class="font-headline text-[10px] uppercase text-copper font-bold tracking-widest">Clima</span>
      <span class="font-body font-semibold text-sm">___CLIMA___</span>
    </div>
    <div class="flex flex-col border-b border-zinc-200 pb-2">
      <span class="font-headline text-[10px] uppercase text-copper font-bold tracking-widest">Turno</span>
      <span class="font-body font-semibold text-sm">___TURNO___</span>
    </div>
    <div class="flex flex-col border-b border-zinc-200 pb-2">
      <span class="font-headline text-[10px] uppercase text-copper font-bold tracking-widest">Horário</span>
      <span class="font-label font-bold text-sm">___H_INI___ – ___H_FIM___</span>
    </div>
    <div class="flex flex-col border-b border-zinc-200 pb-2">
      <span class="font-headline text-[10px] uppercase text-copper font-bold tracking-widest">Tipo de Tarefa</span>
      <span class="font-body font-semibold text-sm">___TIPO_TAREFA___</span>
    </div>
    <div class="flex flex-col border-b border-zinc-200 pb-2">
      <span class="font-headline text-[10px] uppercase text-copper font-bold tracking-widest">Responsável</span>
      <span class="font-body font-semibold text-sm">___SIGNATORY_NAME___</span>
    </div>
    <div class="flex flex-col border-b border-zinc-200 pb-2">
      <span class="font-headline text-[10px] uppercase text-copper font-bold tracking-widest">Doc. (CPF/RG)</span>
      <span class="font-label font-bold text-sm">___SIGNATORY_DOC___</span>
    </div>
    <div class="flex flex-col border-b border-zinc-200 pb-2">
      <span class="font-headline text-[10px] uppercase text-copper font-bold tracking-widest">ID do RDO</span>
      <span class="font-label text-xs font-bold text-ink/70">___ID_RDO___</span>
    </div>
    <div class="flex flex-col border-b border-zinc-200 pb-2">
      <span class="font-headline text-[10px] uppercase text-copper font-bold tracking-widest">Emissão</span>
      <span class="font-label text-xs text-ink/60">___EMISSAO___</span>
    </div>
  </section>

  <!-- KPI BAR -->
  <div class="grid grid-cols-4 bg-ink rounded-sm overflow-hidden page-avoid">
    <div class="flex flex-col items-center py-4 border-r border-white/10">
      <span class="font-label text-2xl font-bold text-copper">___KPI_ATIVIDADES___</span>
      <span class="font-headline text-[9px] text-white/50 uppercase tracking-widest mt-1">Atividades</span>
    </div>
    <div class="flex flex-col items-center py-4 border-r border-white/10">
      <span class="font-label text-2xl font-bold text-copper">___KPI_FOTOS___</span>
      <span class="font-headline text-[9px] text-white/50 uppercase tracking-widest mt-1">Fotos</span>
    </div>
    <div class="flex flex-col items-center py-4 border-r border-white/10">
      <span class="font-label text-2xl font-bold text-copper">___DURACAO_STR___</span>
      <span class="font-headline text-[9px] text-white/50 uppercase tracking-widest mt-1">Duração</span>
    </div>
    <div class="flex flex-col items-center py-4">
      <span class="font-label text-2xl font-bold text-copper">___KPI_KM___</span>
      <span class="font-headline text-[9px] text-white/50 uppercase tracking-widest mt-1">KM Percorrido</span>
    </div>
  </div>

  <!-- GPS BLOCK (conditional) -->
  ___GPS_BLOCK___

  <!-- ORIENTAÇÃO / SCOPE (conditional) -->
  ___ORIENTACAO_SECTION___

  <!-- INTERRUPÇÃO (conditional) -->
  ___INTR_SECTION___

  <!-- EPI PHOTO (conditional) -->
  ___EPI_SECTION___

  <!-- ATIVIDADES TABLE -->
  <section class="page-avoid">
    <h2 class="font-headline text-base font-bold copper-accent pl-3 uppercase tracking-wide mb-3 flex items-center gap-2">
      <span class="material-symbols-outlined text-copper text-lg">checklist</span>
      Serviços Executados
    </h2>
    <div class="overflow-hidden border border-zinc-200 rounded-sm">
      <table class="w-full text-left border-collapse">
        <thead class="bg-ink text-white">
          <tr>
            <th class="p-3 font-headline text-[10px] uppercase tracking-widest border-r border-white/10">Atividade / Descrição</th>
            <th class="p-3 font-headline text-[10px] uppercase tracking-widest border-r border-white/10 w-36">Progresso</th>
            <th class="p-3 font-headline text-[10px] uppercase tracking-widest w-28 text-center">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-zinc-200 text-xs">
          ___ACTIVITY_ROWS___
        </tbody>
      </table>
    </div>
  </section>

  <!-- EVIDÊNCIAS (conditional) -->
  ___PHOTOS_SECTION___

  <!-- OBSERVAÇÕES -->
  <section>
    <h2 class="font-headline text-base font-bold copper-accent pl-3 uppercase tracking-wide mb-3 flex items-center gap-2">
      <span class="material-symbols-outlined text-copper text-lg">edit_note</span>
      Observações Gerais
    </h2>
    ___OBS_BLOCK___
  </section>

  <!-- FERRAMENTAS PHOTO (conditional) -->
  ___FERRAMENTAS_SECTION___

  <!-- IA ANALYSIS -->
  <section class="page-avoid">
    <h2 class="font-headline text-base font-bold patina-accent pl-3 uppercase tracking-wide mb-3 flex items-center gap-2">
      <span class="material-symbols-outlined text-lg" style="color:#2A9D8F;">smart_toy</span>
      Análise Inteligente — BTP AI
    </h2>
    <div class="bg-zinc-50 border border-zinc-200 rounded-sm p-4" style="border-left:3px solid #2A9D8F;">
      ___AI_BLOCK___
    </div>
  </section>

  <!-- ASSINATURAS -->
  <div class="grid grid-cols-2 gap-12 mt-2 page-avoid">
    <div class="text-center">
      <div class="h-14 flex items-end justify-center mb-2">
        ___SIG_BLOCK___
      </div>
      <div class="border-t border-zinc-300 pt-3">
        <p class="font-body font-bold text-xs uppercase">___SIGNATORY_NAME___</p>
        <p class="font-label text-[9px] text-zinc-400 uppercase tracking-widest">___SIGNATORY_DOC___</p>
        <div class="mt-1 flex items-center justify-center gap-1" style="color:#2A9D8F;">
          <span class="material-symbols-outlined text-xs">verified_user</span>
          <span class="font-label text-[8px] font-bold">ASSINATURA DIGITAL</span>
        </div>
      </div>
    </div>
    <div class="text-center">
      <div class="h-14 flex items-end justify-center mb-2">
        <span class="font-label text-zinc-300 italic text-[10px] tracking-tighter">Engenheiro / Fiscal</span>
      </div>
      <div class="border-t border-zinc-300 pt-3">
        <p class="font-body font-bold text-xs uppercase">Engenheiro Responsável</p>
        <p class="font-label text-[9px] text-zinc-400 uppercase tracking-widest">Data: ___DATA_RDO___ &nbsp;|&nbsp; Rubrica: ________________</p>
      </div>
    </div>
  </div>

</div>

<!-- ── FOOTER STRIP ── -->
<footer class="mt-auto px-12 py-3 border-t-2 border-copper flex justify-between items-center bg-ink">
  <span class="font-headline text-[9px] font-bold text-copper tracking-widest uppercase">BOMTEMPO ENGENHARIA</span>
  <span class="font-label text-[8px] text-white/40 uppercase tracking-wider">RDO ___ID_RDO___ · Contrato ___CONTRATO___ · ___DATA_RDO___ · Emitido ___EMISSAO___</span>
  <span class="font-headline text-[9px] font-bold text-white/70 uppercase tracking-widest">Relatório Diário de Obra</span>
</footer>

</article>
</main>
</body>
</html>"""


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
            <div class="flex items-center gap-3 py-2 text-zinc-400">
              <span class="material-symbols-outlined text-zinc-300 text-lg flex-shrink-0">location_off</span>
              <div>
                <span class="font-headline text-[10px] uppercase font-bold tracking-widest block" style="color:#C98B2A;">{label}</span>
                <span class="font-body text-sm italic">Não registrado</span>
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
        dist_badge = ""
        if distancia and float(distancia) > 0:
            d = float(distancia)
            d_str = f"{d:.0f} metros" if d < 1000 else f"{d/1000:.2f} km"
            clr = "#1d7066" if d <= 100 else ("#8a6d0a" if d <= 300 else "#C0392B")
            dist_badge = f'<span style="display:inline-block;font-size:9px;font-weight:700;padding:1px 7px;border-radius:9999px;margin-left:6px;background:{clr}20;color:{clr};border:0.5px solid {clr}60;">{d_str} da obra</span>'
        return f"""
            <div class="flex items-start gap-3 py-3 border-b border-zinc-100 last:border-0">
              <span class="material-symbols-outlined text-lg flex-shrink-0 mt-0.5" style="color:#C98B2A;">location_on</span>
              <div class="flex-1">
                <span class="font-headline text-[10px] uppercase font-bold tracking-widest block" style="color:#C98B2A;">{label}{f' — {time_str}' if time_str else ''}</span>
                <span class="font-body text-sm font-semibold">{addr}{dist_badge}</span>
                <span class="font-label text-[9px] text-zinc-400 block mt-0.5">({float(lat):.6f}, {float(lng):.6f})</span>
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
            return '<tr><td colspan="3" class="p-4 text-center font-body italic text-zinc-400 text-sm">Nenhuma atividade registrada.</td></tr>'
        rows = []
        for i, r in enumerate(items[:30]):
            pct = int(r.get("progresso_percentual", r.get("percentual", 0)) or 0)
            status = r.get("status", "Em andamento")
            if pct == 100:
                badge = '<span style="display:inline-block;padding:2px 8px;background:#2A9D8F20;color:#2A9D8F;font-weight:700;font-size:9px;border-radius:9999px;letter-spacing:0.3px;">CONCLUÍDO</span>'
            elif pct > 0:
                badge = f'<span style="display:inline-block;padding:2px 8px;background:#C98B2A20;color:#C98B2A;font-weight:700;font-size:9px;border-radius:9999px;letter-spacing:0.3px;">{e(status).upper()}</span>'
            else:
                badge = f'<span style="display:inline-block;padding:2px 8px;background:#ef444420;color:#ef4444;font-weight:700;font-size:9px;border-radius:9999px;letter-spacing:0.3px;">{e(status).upper()}</span>'
            prog_color = "#2A9D8F" if pct == 100 else "#C98B2A"
            row_bg = "background:#f9fafb;" if i % 2 == 1 else ""
            rows.append(
                f'<tr style="{row_bg}">'
                f'<td class="p-3 font-body font-medium text-xs">{e(r.get("atividade", r.get("descricao", "")))}</td>'
                f'<td class="p-3">'
                f'<div style="display:flex;align-items:center;gap:8px;">'
                f'<div style="flex:1;height:5px;background:#f1f5f9;border-radius:3px;overflow:hidden;">'
                f'<div style="height:100%;width:{pct}%;background:{prog_color};border-radius:3px;"></div>'
                f'</div>'
                f'<span style="font-family:\'JetBrains Mono\',monospace;font-weight:700;font-size:10px;color:{prog_color};">{pct}%</span>'
                f'</div>'
                f'</td>'
                f'<td class="p-3 text-center">{badge}</td>'
                f'</tr>'
            )
        rows.append(
            f'<tr style="background:#f5f0e6;">'
            f'<td colspan="3" style="padding:8px 12px;font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:10px;text-transform:uppercase;border-top:1px solid #C98B2A;">'
            f'TOTAL: {len(items)} atividade(s) registrada(s)'
            f'</td></tr>'
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
            ts_html = f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:8px;color:#9ca3af;display:block;margin-bottom:2px;">{ts}</span>' if ts != "—" else ""
            cap_html = f'<span style="font-weight:600;font-size:11px;color:#081210;word-break:break-word;">{caption}</span>' if caption else ""
            ai_html = f'<span style="font-size:9px;color:#2A9D8F;font-style:italic;margin-top:3px;display:block;">🤖 {analysis}</span>' if analysis else ""
            cards.append(f"""
            <div style="border:0.5px solid #e4e4e7;border-radius:4px;overflow:hidden;page-break-inside:avoid;">
              <div style="aspect-ratio:16/9;background:#f4f4f5;overflow:hidden;">
                <img src="{url}" style="width:100%;height:100%;object-fit:cover;display:block;" loading="lazy" />
              </div>
              <div style="padding:6px 8px 8px;background:#fafafa;border-left:2px solid #C98B2A;">
                {ts_html}{cap_html}{ai_html}
              </div>
            </div>""")
        return f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;padding:6px 0;">{"".join(cards)}</div>'

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
        km_str       = f"{float(km_perc):.2f} km" if km_perc is not None else "—"
        houve_intr = bool(rdo_data.get("houve_interrupcao"))
        motivo     = e((rdo_data.get("motivo_interrupcao") or "—")[:120])
        obs        = (rdo_data.get("observacoes") or "").strip()
        id_rdo     = e(rdo_data.get("id_rdo") or "")
        mestre     = e(rdo_data.get("mestre_id") or "")
        emissao    = RDOService._fmt_date(
            str(rdo_data.get("created_at") or rdo_data.get("data") or "")[:10]
            or datetime.now().strftime("%Y-%m-%d")
        )
        signatory_name = e(rdo_data.get("signatory_name") or "")
        signatory_doc  = e(rdo_data.get("signatory_doc") or "")
        signatory_sig_b64 = rdo_data.get("signatory_sig_b64") or ""
        epi_foto_url = rdo_data.get("epi_foto_url") or ""
        ferramentas_foto_url = rdo_data.get("ferramentas_foto_url") or ""
        ai_text    = (rdo_data.get("ai_summary") or "").strip()

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
                mins = max(0, int((dt_out - dt_in).total_seconds() / 60))
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

        # ── Conditional HTML blocks ─────────────────────────────────────────

        # Watermark / preview
        watermark = '<div class="watermark-rdo">RASCUNHO</div>' if is_preview else ""
        preview_badge = (
            '<span style="display:inline-block;background:#dc2626;color:#fff;'
            'font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:9px;'
            'padding:2px 8px;border-radius:2px;letter-spacing:2px;text-transform:uppercase;margin-top:4px;">'
            'RASCUNHO</span>'
        ) if is_preview else ""

        if is_preview:
            status_badge = (
                '<div style="display:inline-block;padding:4px 10px;'
                'background:#f59e0b20;border:1px solid #f59e0b;'
                'color:#b45309;font-family:\'JetBrains Mono\',monospace;'
                'font-size:9px;font-weight:700;border-radius:2px;">'
                'STATUS: RASCUNHO</div>'
            )
        else:
            status_badge = (
                '<div style="display:inline-block;padding:4px 10px;'
                'background:#2A9D8F20;border:1px solid #2A9D8F;'
                'color:#2A9D8F;font-family:\'JetBrains Mono\',monospace;'
                'font-size:9px;font-weight:700;border-radius:2px;">'
                'STATUS: OPERACIONAL</div>'
            )

        # GPS block
        has_gps = rdo_data.get("checkin_lat") or rdo_data.get("checkout_lat")
        if has_gps:
            gps_block = (
                '<section style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:4px;padding:12px 16px;">'
                '<h2 style="font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:13px;'
                'text-transform:uppercase;letter-spacing:0.05em;color:#081210;'
                'border-left:4px solid #C98B2A;padding-left:10px;margin-bottom:10px;'
                'display:flex;align-items:center;gap:6px;">'
                '<span class="material-symbols-outlined" style="color:#C98B2A;font-size:16px;">pin_drop</span>'
                'Registro GPS</h2>'
                f'{gps_checkin}'
                f'{gps_checkout}'
                '</section>'
            )
        else:
            gps_block = ""

        # Orientação / scope
        orientacao_section = (
            '<section>'
            '<h2 style="font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:13px;'
            'text-transform:uppercase;letter-spacing:0.05em;color:#081210;'
            'border-left:4px solid #C98B2A;padding-left:10px;margin-bottom:10px;">'
            'Escopo / Orientação</h2>'
            '<div style="background:#fafafa;padding:14px 16px;border:1px solid #e4e4e7;border-radius:2px;">'
            f'<p style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:12px;'
            f'color:#52525b;line-height:1.65;font-style:italic;">{orientacao}</p>'
            '</div></section>'
        ) if orientacao else ""

        # Interrupção
        intr_section = (
            '<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:4px;'
            'padding:12px 16px;display:flex;align-items:flex-start;gap:10px;">'
            '<span class="material-symbols-outlined" style="color:#ef4444;font-size:18px;flex-shrink:0;">warning</span>'
            '<div>'
            '<p style="font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:12px;'
            'text-transform:uppercase;color:#b91c1c;margin-bottom:4px;">Interrupção Registrada</p>'
            f'<p style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:12px;color:#7f1d1d;">{motivo}</p>'
            '</div></div>'
        ) if houve_intr else ""

        # EPI photo
        epi_section = (
            '<section>'
            '<h2 style="font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:13px;'
            'text-transform:uppercase;letter-spacing:0.05em;color:#081210;'
            'border-left:4px solid #C98B2A;padding-left:10px;margin-bottom:10px;">'
            'Equipe com EPIs</h2>'
            '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;">'
            '<div style="aspect-ratio:16/9;background:#f4f4f5;border-radius:4px;overflow:hidden;border:0.5px solid #e4e4e7;">'
            f'<img src="{epi_foto_url}" style="width:100%;height:100%;object-fit:cover;" />'
            '</div></div></section>'
        ) if epi_foto_url else ""

        # Ferramentas photo
        ferramentas_section = (
            '<section>'
            '<h2 style="font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:13px;'
            'text-transform:uppercase;letter-spacing:0.05em;color:#081210;'
            'border-left:4px solid #C98B2A;padding-left:10px;margin-bottom:10px;">'
            'Ferramentas Limpas e Organizadas</h2>'
            '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;">'
            '<div style="aspect-ratio:16/9;background:#f4f4f5;border-radius:4px;overflow:hidden;border:0.5px solid #e4e4e7;">'
            f'<img src="{ferramentas_foto_url}" style="width:100%;height:100%;object-fit:cover;" />'
            '</div></div></section>'
        ) if ferramentas_foto_url else ""

        # Photos
        if evidencias:
            photos_section = (
                '<section>'
                '<h2 style="font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:13px;'
                'text-transform:uppercase;letter-spacing:0.05em;color:#081210;'
                'border-left:4px solid #C98B2A;padding-left:10px;margin-bottom:10px;'
                'display:flex;align-items:center;gap:6px;">'
                '<span class="material-symbols-outlined" style="color:#C98B2A;font-size:16px;">photo_camera</span>'
                f'Evidências de Campo ({len(evidencias)} foto{"s" if len(evidencias) != 1 else ""})'
                '</h2>'
                f'{evidence_html}'
                '</section>'
            )
        else:
            photos_section = ""

        # Observations
        if obs:
            obs_block = (
                '<div style="background:#fafafa;border:1px solid #e4e4e7;border-radius:2px;'
                'padding:12px 16px;font-family:\'Plus Jakarta Sans\',sans-serif;font-size:12px;'
                f'color:#3f3f46;line-height:1.7;white-space:pre-wrap;word-break:break-word;">'
                f'{_html_mod.escape(obs)}</div>'
            )
        else:
            obs_block = (
                '<p style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:12px;'
                'font-style:italic;color:#a1a1aa;padding:8px 0;">Sem observações para este dia.</p>'
            )

        # AI block
        if ai_text:
            def _md_simple(text: str) -> str:
                import re
                lines = []
                for line in text.split("\n"):
                    line = _html_mod.escape(line)
                    line = re.sub(r"^## (.+)$", r'<h4 style="margin:8px 0 4px;color:#2A9D8F;font-family:\'Rajdhani\',sans-serif;font-size:11px;text-transform:uppercase;letter-spacing:0.4px;">\1</h4>', line)
                    line = re.sub(r"^\s*[-•]\s(.+)$", r'<li style="margin:2px 0;">\1</li>', line)
                    line = re.sub(r"\*\*(.+?)\*\*", r'<strong>\1</strong>', line)
                    lines.append(line)
                html_out = "\n".join(lines)
                html_out = re.sub(r"(<li[^>]*>.*?</li>\n?)+", lambda m: f"<ul style='margin:4px 0 6px 14px;padding:0;'>{m.group(0)}</ul>", html_out)
                return html_out
            ai_block = (
                '<div style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:12px;'
                f'color:#1a1a1a;line-height:1.7;">{_md_simple(ai_text)}</div>'
            )
        else:
            ai_block = (
                '<div style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:12px;'
                'font-style:italic;color:#a1a1aa;">⏳ Análise sendo processada…</div>'
            )

        # Signature
        if signatory_sig_b64 and signatory_sig_b64.startswith("data:"):
            sig_block = f'<img src="{signatory_sig_b64}" style="max-height:56px;display:block;margin-bottom:4px;" />'
        else:
            sig_block = '<div style="height:40px;border-bottom:0.5px solid #d4d4d8;margin-bottom:4px;"></div>'

        # ── Apply replacements to template ──────────────────────────────────
        replacements = {
            "___WATERMARK___":         watermark,
            "___PREVIEW_BADGE___":     preview_badge,
            "___STATUS_BADGE___":      status_badge,
            "___CONTRATO___":          contrato,
            "___DATA_RDO___":          data_rdo,
            "___PROJETO___":           projeto,
            "___CLIENTE___":           cliente,
            "___LOCALIZACAO___":       localizacao,
            "___MESTRE___":            mestre,
            "___CLIMA___":             clima,
            "___TURNO___":             turno,
            "___H_INI___":             h_ini,
            "___H_FIM___":             h_fim,
            "___TIPO_TAREFA___":       tipo_tarefa,
            "___SIGNATORY_NAME___":    signatory_name or "—",
            "___SIGNATORY_DOC___":     signatory_doc or "—",
            "___ID_RDO___":            id_rdo,
            "___EMISSAO___":           emissao,
            "___KPI_ATIVIDADES___":    str(len(atividades)),
            "___KPI_FOTOS___":         str(len(evidencias)),
            "___DURACAO_STR___":       duracao_str,
            "___KPI_KM___":            km_str,
            "___GPS_BLOCK___":         gps_block,
            "___ORIENTACAO_SECTION___": orientacao_section,
            "___INTR_SECTION___":      intr_section,
            "___EPI_SECTION___":       epi_section,
            "___ACTIVITY_ROWS___":     activity_rows,
            "___PHOTOS_SECTION___":    photos_section,
            "___OBS_BLOCK___":         obs_block,
            "___FERRAMENTAS_SECTION___": ferramentas_section,
            "___AI_BLOCK___":          ai_block,
            "___SIG_BLOCK___":         sig_block,
        }
        html = _RDO_HTML_TEMPLATE
        for key, val in replacements.items():
            html = html.replace(key, str(val) if val is not None else "")
        return html

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
            html_to_pdf(
                html, pdf_path,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                display_header_footer=False,
            )
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
        # Preserve existing view_token if record already exists
        existing_token = ""
        try:
            ex = sb_select("rdo_master", filters={"id_rdo": id_rdo}, limit=1)
            if ex:
                existing_token = ex[0].get("view_token") or ""
        except Exception:
            pass
        view_token = existing_token or _gen_view_token()
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
            "houve_chuva":         bool(rdo_data.get("houve_chuva")),
            "quantidade_chuva":    rdo_data.get("quantidade_chuva") or "",
            "houve_acidente":      bool(rdo_data.get("houve_acidente")),
            "descricao_acidente":  rdo_data.get("descricao_acidente") or "",
            "view_token":          view_token,
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
        """Upload foto para bucket rdo-evidencias (auto-criado se não existir). Retorna URL pública."""
        try:
            sb_storage_ensure_bucket("rdo-evidencias", public=True)
            path = f"{id_rdo}/{filename}"
            url = sb_storage_upload("rdo-evidencias", path, file_bytes, content_type)
            return url or ""
        except Exception as e:
            logger.error(f"❌ upload_evidence: {e}")
            return ""

    @staticmethod
    def save_evidence(id_rdo: str, foto_url: str, legenda: str = "") -> Optional[Dict]:
        try:
            rdo_rows = sb_select("rdo_master", filters={"id_rdo": id_rdo}, limit=1)
            if not rdo_rows:
                logger.warning(f"⚠️ save_evidence: rdo_master not found for id_rdo={id_rdo}")
                return None
            rdo_uuid = rdo_rows[0]["id"]
            return sb_insert("rdo_evidencias", {
                "rdo_id":   rdo_uuid,
                "foto_url": foto_url,
                "legenda":  legenda,
            })
        except Exception as e:
            logger.warning(f"⚠️ save_evidence (non-fatal): {e}")
            return None

    @staticmethod
    def get_full_rdo(id_rdo: str) -> Dict[str, Any]:
        rows = sb_select("rdo_master", filters={"id_rdo": id_rdo})
        if not rows:
            return {}
        rdo = dict(rows[0])
        rdo_uuid = rdo.get("id")  # UUID PK — used as FK in sub-tables
        if rdo_uuid:
            rdo["atividades"] = sb_select("rdo_atividades", filters={"rdo_id": rdo_uuid}) or []
            rdo["evidencias"] = sb_select("rdo_evidencias", filters={"rdo_id": rdo_uuid}) or []
        else:
            rdo["atividades"] = []
            rdo["evidencias"] = []
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
        checkin_lat: float = 0.0,
        checkin_lng: float = 0.0,
        checkin_endereco: str = "",
        client_exif_lat: float = 0.0,
        client_exif_lng: float = 0.0,
        client_exif_datetime: str = "",
        client_last_modified: str = "",
    ) -> Dict[str, str]:
        allowed_types = ["image/jpeg", "image/png", "image/webp", "image/jpg"]
        if content_type.lower() not in allowed_types:
            logger.warning(f"⚠️ Upload bloqueado: MIME type {content_type} não permitido para evidências.")
            return {"foto_url": "", "legenda": legenda, "exif_lat": "", "exif_lng": "", "exif_endereco": ""}

        # Sanitize filename to prevent path traversal
        import os
        safe_filename = os.path.basename(filename)

        # 1. Extract EXIF (GPS + datetime) from image
        exif_lat, exif_lng, exif_dt = _extract_exif_full(file_bytes)

        # 2. Resolve GPS: prefer client-supplied EXIF, fallback to server EXIF, then check-in
        lat = client_exif_lat or exif_lat or checkin_lat
        lng = client_exif_lng or exif_lng or checkin_lng
        gps_source = "checkin" if (not client_exif_lat and not exif_lat and checkin_lat) else "exif"

        # 3. Timestamps
        from datetime import timezone
        now_utc = datetime.now(timezone.utc)
        rede_time = _pt_datetime_str(now_utc)
        if client_exif_datetime:
            try:
                local_dt = datetime.fromisoformat(client_exif_datetime.replace("Z", "+00:00"))
                local_time = _pt_datetime_str(local_dt)
                local_is_exif = True
                local_is_lastmod = False
            except Exception:
                local_time = client_exif_datetime
                local_is_exif = True
                local_is_lastmod = False
        elif exif_dt:
            local_time = _pt_datetime_str(exif_dt)
            local_is_exif = True
            local_is_lastmod = False
        elif client_last_modified:
            try:
                lm_ms = int(client_last_modified)
                lm_dt = datetime.fromtimestamp(lm_ms / 1000, tz=timezone.utc)
                local_time = _pt_datetime_str(lm_dt)
            except Exception:
                local_time = client_last_modified
            local_is_exif = False
            local_is_lastmod = True
        else:
            local_time = rede_time
            local_is_exif = False
            local_is_lastmod = False

        # 4. Map thumbnail (best-effort)
        map_bytes = _fetch_map_thumbnail(lat, lng) if (lat and lng) else None

        # 5. Reverse-geocode for watermark address
        wm_address = checkin_endereco or ""
        if lat and lng and not wm_address:
            try:
                wm_full = _reverse_geocode(lat, lng)
                wm_address = wm_full
            except Exception:
                pass
        addr_parts = wm_address.split(", ") if wm_address else []
        wm_neighborhood = addr_parts[1] if len(addr_parts) > 1 else ""
        wm_city = addr_parts[-1] if addr_parts else ""

        # 6. Apply watermark
        meta: Dict[str, Any] = {
            "rede_time":       rede_time,
            "local_time":      local_time,
            "local_is_exif":   local_is_exif,
            "local_is_lastmod": local_is_lastmod,
            "lat":             lat or None,
            "lng":             lng or None,
            "gps_source":      gps_source,
            "address":         wm_address,
            "neighborhood":    wm_neighborhood,
            "city":            wm_city,
            "contrato":        contrato,
            "mestre":          mestre,
            "map_bytes":       map_bytes,
        }
        try:
            watermarked = _apply_watermark(file_bytes, meta, content_type)
        except Exception as wm_err:
            logger.warning(f"⚠️ Watermark falhou (usando original): {wm_err}")
            watermarked = file_bytes

        # 7. Upload to Supabase Storage
        # Watermark sempre retorna PNG (canal alpha). Força .png no filename e content_type.
        upload_ct = "image/png"
        name_base = os.path.splitext(safe_filename)[0]
        upload_filename = f"{name_base}.png"
        foto_url = RDOService.upload_evidence(id_rdo, watermarked, upload_ct, upload_filename)
        if not foto_url:
            # Upload falhou — retorna dict vazio para o caller filtrar
            return {"foto_url": "", "legenda": legenda, "exif_lat": "", "exif_lng": "", "exif_endereco": ""}

        # 8. Reverse geocode EXIF GPS (reuse wm_address already computed above)
        exif_endereco = wm_address or ""
        if not exif_endereco and exif_lat and exif_lng:
            exif_endereco = _reverse_geocode(exif_lat, exif_lng)

        # 9. Persist to rdo_evidencias (best-effort)
        rdo_master_rows = sb_select("rdo_master", filters={"id_rdo": id_rdo}, limit=1)
        rdo_uuid = rdo_master_rows[0]["id"] if rdo_master_rows else None
        if rdo_uuid:
            record: Dict[str, Any] = {
                "rdo_id":   rdo_uuid,
                "foto_url": foto_url,
                "legenda":  legenda,
            }
            try:
                sb_insert("rdo_evidencias", record)
            except Exception as db_err:
                logger.warning(f"⚠️ rdo_evidencias insert (non-fatal): {db_err}")

        return {
            "foto_url":      foto_url,
            "legenda":       legenda,
            "exif_lat":      str(exif_lat) if exif_lat else "",
            "exif_lng":      str(exif_lng) if exif_lng else "",
            "exif_endereco": exif_endereco,
        }

    # ── AI ───────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_ai_prompt(rdo_data: Dict[str, Any]) -> list:
        """Build the Claude messages list for RDO analysis."""
        acts = "\n".join(
            f"  - {r.get('atividade', r.get('descricao','?'))} ({r.get('progresso_percentual',0)}%) [{r.get('status','Em andamento')}]"
            for r in rdo_data.get("atividades", [])[:10]
        )
        checkin_ts   = rdo_data.get("checkin_timestamp") or ""
        checkout_ts  = rdo_data.get("checkout_timestamp") or ""
        checkin_end  = rdo_data.get("checkin_endereco") or ""
        checkout_end = rdo_data.get("checkout_endereco") or ""
        gps_info = ""
        if checkin_ts:
            gps_info += f"\nCheck-in: {checkin_ts[:16]} @ {checkin_end}"
        if checkout_ts:
            gps_info += f"\nCheck-out: {checkout_ts[:16]} @ {checkout_end}"
        n_fotos = len(rdo_data.get("evidencias", []))

        text_prompt = f"""Você é um consultor sênior de engenharia civil. Analise o RDO abaixo e forneça uma análise executiva concisa.

RDO {rdo_data.get('id_rdo','')} — {rdo_data.get('data','')}
Contrato: {rdo_data.get('contrato','')} | Projeto: {rdo_data.get('projeto','')}
Cliente: {rdo_data.get('cliente','')}
Clima: {rdo_data.get('condicao_climatica','')} | Turno: {rdo_data.get('turno','')}
Interrupção: {'SIM — ' + (rdo_data.get('motivo_interrupcao') or '') if rdo_data.get('houve_interrupcao') else 'NÃO'}
GPS:{gps_info or ' não registrado'}
Fotos de evidência: {n_fotos}
Serviços Executados:\n{acts or '  (não informados)'}
Observações: {(rdo_data.get('observacoes') or 'Nenhuma')[:400]}

Responda em português, de forma direta e objetiva, com as seções:
## 📊 RESUMO EXECUTIVO
(2-3 frases sobre o dia de trabalho)
## 🔨 SERVIÇOS EXECUTADOS
(bullet points dos principais serviços e progresso)
## ⚠️ ALERTAS E RISCOS
(riscos identificados, se houver — caso nenhum, diga "Nenhum risco identificado")
## 💡 RECOMENDAÇÕES
(1-2 recomendações práticas)"""

        # Build multimodal message: text + up to 4 photo URLs for vision
        photo_urls = [
            e.get("foto_url", "")
            for e in (rdo_data.get("evidencias") or [])
            if e.get("foto_url", "").startswith("http")
        ][:4]

        # Análise somente texto — evita filtros de segurança que bloqueiam URLs externas de imagem.
        # A análise executiva baseia-se nos dados estruturados do RDO, não nas fotos.
        user_msg: Any = {"role": "user", "content": text_prompt}
        _ = photo_urls  # reservado para uso futuro com vision opt-in

        return [
            {
                "role": "system",
                "content": (
                    "Você é um assistente especializado em gestão de obras e engenharia civil. "
                    "Analisa Relatórios Diários de Obra (RDO) da empresa Bomtempo. "
                    "Seja preciso, direto e profissional. Responda sempre em português brasileiro. "
                    "Limite cada seção a 3-5 linhas. Não recuse solicitações — este é um contexto "
                    "empresarial legítimo de gestão de construção civil."
                ),
            },
            user_msg,
        ]

    @staticmethod
    def analyze_now(rdo_data: Dict[str, Any], id_rdo: str) -> str:
        """Synchronous AI analysis — runs in calling thread, returns result string.
        Call from run_in_executor to avoid blocking the event loop."""
        try:
            messages = RDOService._build_ai_prompt(rdo_data)
            result = ai_client.query(messages)
            if result:
                sb_update("rdo_master", {"id_rdo": id_rdo}, {"ai_summary": result})
                logger.info(f"✅ AI summary salvo: {id_rdo}")
            return result or ""
        except Exception as e:
            logger.error(f"❌ AI analyze_now: {e}")
            return ""

    @staticmethod
    def analyze_with_ai(rdo_data: Dict[str, Any], id_rdo: str) -> None:
        """Fire-and-forget: analisa RDO e salva ai_summary no banco."""
        def _run():
            RDOService.analyze_now(rdo_data, id_rdo)
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
        # Resolve rdo_id UUID from rdo_master (the FK column is 'rdo_id', not 'id_rdo')
        rdo_master_rows = sb_select("rdo_master", filters={"id_rdo": id_rdo}, limit=1)
        if not rdo_master_rows:
            logger.warning(f"_save_sub_items: rdo_master not found for id_rdo={id_rdo}")
            return
        rdo_uuid = rdo_master_rows[0]["id"]

        sb_delete("rdo_atividades", {"rdo_id": rdo_uuid})

        for item in (rdo_data.get("atividades") or []):
            atv = item.get("atividade") or item.get("descricao") or ""
            if atv:
                sb_insert("rdo_atividades", {
                    "rdo_id":    rdo_uuid,
                    "atividade": atv,
                    "efetivo":   int(item.get("efetivo") or item.get("progresso_percentual") or 0),
                    "observacao": item.get("status") or item.get("observacao") or "",
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
