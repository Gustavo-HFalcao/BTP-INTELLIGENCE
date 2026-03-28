"""
HubState — State for Hub de Operações sub-modules:
  • Cronograma: CRUD de atividades, edição inline, gestão de dependências
  • Auditoria: Bolsões de imagens (Equipe, Falhas, Ferramentas, Gerais) com lightbox
  • Timeline: Log de eventos/registros do projeto, comentários, @mentions

Supabase tables required (see schema below):
  - hub_atividades: id, contrato, fase_macro, fase, atividade, responsavel,
                    inicio_previsto, termino_previsto, conclusao_pct, critico,
                    dependencia, observacoes, created_at, updated_at, created_by
  - hub_auditoria_imgs: id, contrato, categoria, url, legenda, data_captura, autor, created_at
  - hub_timeline: id, contrato, tipo, titulo, descricao, autor, created_at, mencoes (jsonb)
"""
import logging
from typing import Any, Dict, List
import reflex as rx

from bomtempo.core.supabase_client import sb_select, sb_insert, sb_update, sb_delete
from bomtempo.core.audit_logger import audit_log, AuditCategory

logger = logging.getLogger(__name__)

from datetime import timezone, timedelta
_BRT = timezone(timedelta(hours=-3))


def _utc_to_brt(ts: str) -> str:
    """Convert ISO UTC timestamp → BRT (UTC-3), formatted as DD/MM/YYYY HH:MM."""
    if not ts:
        return ""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00")[:32])
        brt = dt.astimezone(_BRT)
        return brt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return ts[:16].replace("T", " ")


def _utc_date_to_br(ts: str) -> str:
    """Convert ISO date string YYYY-MM-DD → DD/MM/YYYY."""
    if not ts:
        return ""
    try:
        parts = ts[:10].split("-")
        if len(parts) == 3:
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
    except Exception:
        pass
    return ts[:10]

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

ENTRY_TYPES = ["Atualização", "Marco", "Reunião", "Decisão", "Alerta", "Falha", "Documento", "Custo"]

AUDIT_CATEGORIES = [
    {"slug": "equipe",       "label": "Equipe com EPI",    "icon": "hard-hat",     "color": "#22c55e"},
    {"slug": "falhas",       "label": "Falhas & Logs",     "icon": "alert-triangle","color": "#EF4444"},
    {"slug": "ferramentas",  "label": "Ferramentas",       "icon": "wrench",       "color": "#2A9D8F"},
    {"slug": "gerais",       "label": "Imagens Gerais",    "icon": "image",        "color": "#C98B2A"},
]

FASE_COLORS: Dict[str, str] = {
    "civil":       "#C98B2A",
    "elétrica":    "#3B82F6",
    "eletrica":    "#3B82F6",
    "hidráulica":  "#2A9D8F",
    "hidraulica":  "#2A9D8F",
    "estrutural":  "#E89845",
    "mecânica":    "#A855F7",
    "mecanica":    "#A855F7",
    "licenciamento": "#64748B",
    "aprovações":  "#64748B",
    "aprovacoes":  "#64748B",
}


def _fase_color(fase: str) -> str:
    return FASE_COLORS.get(fase.lower().strip(), "#889999")


def _norm_str(v: object, fallback: str = "") -> str:
    if v is None or str(v) in ("None", "NaT", "nan", ""):
        return fallback
    return str(v)


def _norm_pct(v: object) -> str:
    try:
        return str(int(float(v or 0)))
    except (ValueError, TypeError):
        return "0"


# ─────────────────────────────────────────────────────────────────────────────
# State
# ─────────────────────────────────────────────────────────────────────────────

class HubState(rx.State):
    """Hub de Operações — Cronograma, Auditoria, Timeline state."""

    # ── Loading flags ────────────────────────────────────────────────────────
    cron_loading: bool = False
    audit_loading: bool = False
    timeline_loading: bool = False

    # ══════════════════════════════════════════════════════════════════════════
    # CRONOGRAMA
    # ══════════════════════════════════════════════════════════════════════════

    # List of normalized activity dicts for the selected contract
    # Keys: id, contrato, fase_macro, fase, atividade, responsavel,
    #       inicio_previsto, termino_previsto, conclusao_pct, critico,
    #       dependencia, observacoes, color
    cron_rows: List[Dict[str, str]] = []

    # Filter
    cron_fase_filter: str = ""
    cron_search: str = ""
    cron_search_input: str = ""  # UI-only: updated on_change, committed on_blur/Enter
    cron_show_only_critical: bool = False

    # Inline edit dialog
    cron_show_dialog: bool = False
    cron_edit_id: str = ""          # empty = new
    cron_edit_atividade: str = ""
    cron_edit_fase_macro: str = ""
    cron_edit_fase: str = ""
    cron_edit_responsavel: str = ""
    cron_edit_inicio: str = ""
    cron_edit_termino: str = ""
    cron_edit_pct: str = "0"
    cron_edit_critico: bool = False
    cron_edit_dependencia: str = ""
    cron_edit_observacoes: str = ""
    cron_saving: bool = False
    cron_error: str = ""

    # Delete confirm
    cron_delete_id: str = ""
    cron_delete_name: str = ""
    cron_show_delete: bool = False

    # ══════════════════════════════════════════════════════════════════════════
    # AUDITORIA (photo gallery bolsões)
    # ══════════════════════════════════════════════════════════════════════════

    # List of all images for selected contract
    # Keys: id, contrato, categoria, url, legenda, data_captura, autor
    audit_images: List[Dict[str, str]] = []

    # Currently open bolsão slug (e.g. "equipe", "falhas", "ferramentas", "gerais")
    audit_open_category: str = ""

    # Lightbox
    audit_lightbox_url: str = ""
    audit_lightbox_legenda: str = ""
    audit_lightbox_data: str = ""
    audit_lightbox_autor: str = ""

    # Upload dialog
    audit_show_upload: bool = False
    audit_upload_category: str = ""
    audit_upload_url: str = ""
    audit_upload_legenda: str = ""
    audit_uploading: bool = False
    audit_upload_error: str = ""

    # ══════════════════════════════════════════════════════════════════════════
    # TIMELINE
    # ══════════════════════════════════════════════════════════════════════════

    # Feed of log entries for selected contract
    # Keys: id, contrato, tipo, titulo, descricao, autor, created_at,
    #       is_document, is_cost, custo_valor, custo_categoria,
    #       anexo_url, anexo_nome
    timeline_entries: List[Dict[str, str]] = []

    # New entry form
    tl_entry_type: str = "Atualização"
    tl_titulo: str = ""
    tl_descricao: str = ""
    tl_submitting: bool = False
    tl_error: str = ""

    # mention users
    tl_mention_users: List[str] = []   # usernames disponíveis para @mention

    # custo fields
    tl_custo_valor: str = ""       # valor do custo (string para input)
    tl_custo_categoria: str = "Operacional"  # categoria do custo

    # New: file attachment
    tl_anexo_url: str = ""         # URL do arquivo no Supabase Storage após upload
    tl_anexo_nome: str = ""        # nome original do arquivo
    tl_uploading_anexo: bool = False

    # Filter + search
    tl_filter_tipo: str = ""
    tl_search: str = ""            # busca por título/descrição
    tl_search_input: str = ""  # UI-only input buffer

    # ══════════════════════════════════════════════════════════════════════════
    # MACRO/MICRO hierarchy
    # ══════════════════════════════════════════════════════════════════════════

    # Edit fields for hierarchical properties
    cron_edit_nivel: str = "macro"       # "macro" | "micro"
    cron_edit_peso: str = "100"          # peso_pct relative to parent (macro) or project (macro)
    cron_edit_parent_id: str = ""        # parent macro id (only for micros)

    # Which macro rows are expanded (showing micros) — list of macro ids
    cron_expanded_macros: List[str] = []

    # Pending activities awaiting approval (role=gestor)
    pending_activities: List[Dict[str, str]] = []
    cron_approve_loading: bool = False

    # ══════════════════════════════════════════════════════════════════════════
    # GANTT PREMIUM — weather + IA climate
    # ══════════════════════════════════════════════════════════════════════════

    # IA climate analysis result
    cron_climate_analysis: str = ""
    cron_climate_loading: bool = False

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    @rx.var
    def filtered_cron_rows(self) -> List[Dict[str, str]]:
        """Apply fase filter, search, and critical-only to cron_rows."""
        rows = self.cron_rows
        if self.cron_fase_filter:
            rows = [r for r in rows if r.get("fase_macro", "") == self.cron_fase_filter]
        if self.cron_show_only_critical:
            rows = [r for r in rows if r.get("critico", "") == "1"]
        if self.cron_search:
            q = self.cron_search.lower()
            rows = [
                r for r in rows
                if q in r.get("atividade", "").lower()
                or q in r.get("responsavel", "").lower()
                or q in r.get("fase", "").lower()
            ]
        return rows

    @rx.var
    def cron_unique_fases(self) -> List[str]:
        seen = []
        for r in self.cron_rows:
            f = r.get("fase_macro", "").strip()
            if f and f not in seen:
                seen.append(f)
        return seen

    @rx.var
    def cron_stats(self) -> Dict[str, str]:
        total = len(self.cron_rows)
        done = sum(1 for r in self.cron_rows if int(r.get("conclusao_pct", "0") or "0") >= 100)
        critical = sum(1 for r in self.cron_rows if r.get("critico", "") == "1")
        pct = round(done / total * 100) if total else 0
        return {
            "total": str(total),
            "done": str(done),
            "critical": str(critical),
            "pct": str(pct),
        }

    @rx.var
    def audit_category_counts(self) -> Dict[str, str]:
        counts: Dict[str, str] = {}
        for cat in AUDIT_CATEGORIES:
            slug = cat["slug"]
            counts[slug] = str(sum(1 for img in self.audit_images if img.get("categoria") == slug))
        return counts

    @rx.var
    def audit_open_images(self) -> List[Dict[str, str]]:
        if not self.audit_open_category:
            return []
        return [img for img in self.audit_images if img.get("categoria") == self.audit_open_category]

    @rx.var
    def filtered_timeline(self) -> List[Dict[str, str]]:
        rows = self.timeline_entries
        if self.tl_filter_tipo:
            rows = [e for e in rows if e.get("tipo") == self.tl_filter_tipo]
        if self.tl_search:
            q = self.tl_search.lower()
            rows = [e for e in rows if q in e.get("titulo", "").lower() or q in e.get("descricao", "").lower()]
        return rows

    @rx.var
    def audit_lightbox_open(self) -> bool:
        return self.audit_lightbox_url != ""

    @rx.var
    def cron_activity_options(self) -> List[str]:
        """List of existing activity names for dependency dropdown (excludes current edit)."""
        return [
            r.get("atividade", "")
            for r in self.cron_rows
            if r.get("atividade") and r.get("id") != self.cron_edit_id
        ]

    @rx.var
    def gantt_rows(self) -> List[Dict[str, str]]:
        """
        Returns filtered_cron_rows enriched with Gantt positioning data:
          - gantt_left_pct: CSS left% within the Gantt timeline (string, e.g. "12.5")
          - gantt_width_pct: CSS width% within the Gantt timeline (string, e.g. "30.0")
          - gantt_overdue: "1" if termino_iso < today and conclusao_pct < 100
        All activities without valid ISO dates get left="0", width="100".
        """
        from datetime import date
        rows = self.filtered_cron_rows
        if not rows:
            return []

        # Compute global min/max from all rows (not just filtered) for consistent scale
        all_rows = self.cron_rows
        dates_start = []
        dates_end = []
        for r in all_rows:
            s = r.get("inicio_iso", "")
            e = r.get("termino_iso", "")
            if s and len(s) >= 10:
                try:
                    dates_start.append(date.fromisoformat(s[:10]))
                except Exception:
                    pass
            if e and len(e) >= 10:
                try:
                    dates_end.append(date.fromisoformat(e[:10]))
                except Exception:
                    pass

        if not dates_start or not dates_end:
            return [dict(r, gantt_left_pct="0", gantt_width_pct="100", gantt_overdue="0") for r in rows]

        global_start = min(dates_start)
        global_end = max(dates_end)
        total_days = (global_end - global_start).days or 1
        today = date.today()

        result = []
        for r in rows:
            s_iso = r.get("inicio_iso", "")
            e_iso = r.get("termino_iso", "")
            try:
                s_date = date.fromisoformat(s_iso[:10]) if s_iso and len(s_iso) >= 10 else global_start
                e_date = date.fromisoformat(e_iso[:10]) if e_iso and len(e_iso) >= 10 else global_end
                left_days = (s_date - global_start).days
                dur_days = max((e_date - s_date).days, 1)
                left_pct = round(left_days / total_days * 100, 1)
                width_pct = round(dur_days / total_days * 100, 1)
                # Clamp
                if left_pct < 0:
                    left_pct = 0.0
                if left_pct + width_pct > 100:
                    width_pct = 100.0 - left_pct
                overdue = "1" if e_date < today and int(r.get("conclusao_pct", "0") or "0") < 100 else "0"
            except Exception:
                left_pct, width_pct, overdue = 0.0, 100.0, "0"

            result.append(dict(
                r,
                gantt_left_pct=str(left_pct),
                gantt_width_pct=str(max(width_pct, 0.8)),
                gantt_overdue=overdue,
            ))
        return result

    @rx.var
    def gantt_date_range(self) -> Dict[str, str]:
        """Returns {'start': 'DD/MM/YYYY', 'end': 'DD/MM/YYYY'} for display."""
        from datetime import date
        if not self.cron_rows:
            return {"start": "—", "end": "—"}
        dates_s, dates_e = [], []
        for r in self.cron_rows:
            s = r.get("inicio_iso", "")
            e = r.get("termino_iso", "")
            if s and len(s) >= 10:
                try:
                    dates_s.append(date.fromisoformat(s[:10]))
                except Exception:
                    pass
            if e and len(e) >= 10:
                try:
                    dates_e.append(date.fromisoformat(e[:10]))
                except Exception:
                    pass
        if not dates_s or not dates_e:
            return {"start": "—", "end": "—"}
        def fmt(d: date) -> str:
            return d.strftime("%d/%m/%Y")
        return {"start": fmt(min(dates_s)), "end": fmt(max(dates_e))}

    @rx.var
    def cron_macro_rows(self) -> List[Dict[str, str]]:
        """All macro-level activities (nivel=='macro' or nivel missing/empty)."""
        return [r for r in self.filtered_cron_rows if r.get("nivel", "macro") in ("macro", "")]

    @rx.var
    def cron_display_rows(self) -> List[Dict[str, str]]:
        """
        Flat ordered list for rx.foreach — macros interleaved with their micros.
        Each row has _display_mode: 'macro' | 'micro' | 'pending_micro'.
        Micros only appear when their parent macro is in cron_expanded_macros.
        """
        result: List[Dict[str, str]] = []
        all_rows = self.filtered_cron_rows
        # Separate macros and micros
        macros = [r for r in all_rows if r.get("nivel", "macro") in ("macro", "")]
        micros = [r for r in all_rows if r.get("nivel", "") == "micro"]
        expanded = self.cron_expanded_macros

        for macro in macros:
            macro_id = macro.get("id", "")
            # Calculate macro_progress from micros if any
            children = [m for m in micros if m.get("parent_id", "") == macro_id]
            if children:
                total_peso = sum(int(c.get("peso_pct", "0") or "0") for c in children)
                if total_peso > 0:
                    weighted_pct = sum(
                        int(c.get("conclusao_pct", "0") or "0") * int(c.get("peso_pct", "0") or "0")
                        for c in children
                    ) / total_peso
                else:
                    weighted_pct = 0.0
                computed_pct = str(round(weighted_pct))
                has_micros = "1"
            else:
                computed_pct = macro.get("conclusao_pct", "0")
                has_micros = "0"

            is_expanded = "1" if macro_id in expanded else "0"
            result.append(dict(
                macro,
                _display_mode="macro",
                _has_micros=has_micros,
                _is_expanded=is_expanded,
                _computed_pct=computed_pct,
                _micro_count=str(len(children)),
            ))

            # Append micros if expanded
            if macro_id in expanded:
                for micro in children:
                    result.append(dict(
                        micro,
                        _display_mode="micro",
                        _has_micros="0",
                        _is_expanded="0",
                        _computed_pct=micro.get("conclusao_pct", "0"),
                        _micro_count="0",
                    ))

        # Standalone entries that are micros with no parent in current filter
        macro_ids = {m.get("id", "") for m in macros}
        orphan_micros = [m for m in micros if m.get("parent_id", "") not in macro_ids]
        for micro in orphan_micros:
            result.append(dict(
                micro,
                _display_mode="micro",
                _has_micros="0",
                _is_expanded="0",
                _computed_pct=micro.get("conclusao_pct", "0"),
                _micro_count="0",
            ))

        return result

    @rx.var
    def cron_pending_rows(self) -> List[Dict[str, str]]:
        """Activities flagged as pendente_aprovacao=True."""
        return [r for r in self.cron_rows if r.get("pendente_aprovacao", "0") == "1"]

    @rx.var
    def cron_parent_options(self) -> List[Dict[str, str]]:
        """List of macros for parent dropdown when creating/editing a micro."""
        return [
            {"id": r.get("id", ""), "label": r.get("atividade", "")}
            for r in self.cron_rows
            if r.get("nivel", "macro") in ("macro", "") and r.get("id") != self.cron_edit_id
        ]

    # ══════════════════════════════════════════════════════════════════════════
    # CRONOGRAMA — Load & CRUD
    # ══════════════════════════════════════════════════════════════════════════

    @rx.event(background=True)
    async def load_cronograma(self, contrato: str):
        """Load activities for a given contract from hub_atividades table."""
        async with self:
            self.cron_loading = True
            self.cron_rows = []
            self.cron_fase_filter = ""
            self.cron_search = ""

        try:
            rows = sb_select(
                "hub_atividades",
                filters={"contrato": contrato},
                order="fase_macro.asc,inicio_previsto.asc",
                limit=500,
            )
            normalized = []
            for r in rows:
                fase = _norm_str(r.get("fase", ""))
                pendente_raw = r.get("pendente_aprovacao", False)
                pendente = "1" if str(pendente_raw or "").upper() in ("TRUE", "1", "SIM", "YES") else "0"
                normalized.append({
                    "id":              _norm_str(r.get("id")),
                    "contrato":        _norm_str(r.get("contrato")),
                    "fase_macro":      _norm_str(r.get("fase_macro")),
                    "fase":            fase,
                    "atividade":       _norm_str(r.get("atividade")),
                    "responsavel":     _norm_str(r.get("responsavel"), "—"),
                    "inicio_previsto": _utc_date_to_br(_norm_str(r.get("inicio_previsto"))),
                    "termino_previsto": _utc_date_to_br(_norm_str(r.get("termino_previsto"))),
                    # raw ISO dates kept for Gantt/weather lookups
                    "inicio_iso": _norm_str(r.get("inicio_previsto"))[:10],
                    "termino_iso": _norm_str(r.get("termino_previsto"))[:10],
                    "conclusao_pct":   _norm_pct(r.get("conclusao_pct")),
                    "critico":         "1" if str(r.get("critico", "") or "").upper() in ("TRUE", "1", "SIM") else "0",
                    "dependencia":     _norm_str(r.get("dependencia")),
                    "observacoes":     _norm_str(r.get("observacoes")),
                    "color":           _fase_color(fase),
                    # Hierarchical fields
                    "nivel":           _norm_str(r.get("nivel"), "macro"),
                    "parent_id":       _norm_str(r.get("parent_id")),
                    "peso_pct":        _norm_pct(r.get("peso_pct") if r.get("peso_pct") is not None else 100),
                    "pendente_aprovacao": pendente,
                })
        except Exception as e:
            logger.error(f"load_cronograma error: {e}")
            normalized = []

        async with self:
            self.cron_rows = normalized
            self.cron_loading = False

    def set_cron_fase_filter(self, value: str):
        self.cron_fase_filter = "" if self.cron_fase_filter == value else value

    def set_cron_search(self, value: str):
        self.cron_search = value

    def commit_cron_search(self, _value: str = ""):
        """Commit search from blur or Enter key — only then triggers filtered_cron_rows recalc."""
        self.cron_search = self.cron_search_input

    def set_cron_search_input(self, value: str):
        """Update local input var without triggering filtered_cron_rows recalc."""
        self.cron_search_input = value

    def handle_cron_search_key(self, key: str):
        if key == "Enter":
            self.cron_search = self.cron_search_input

    def toggle_cron_critical(self):
        self.cron_show_only_critical = not self.cron_show_only_critical

    # ── Dialog open/close ─────────────────────────────────────────────────────

    def open_cron_new_root(self):
        self.open_cron_new("")

    def open_cron_new(self, parent_id: str = ""):
        self.cron_edit_id = ""
        self.cron_edit_atividade = ""
        self.cron_edit_fase_macro = ""
        self.cron_edit_fase = ""
        self.cron_edit_responsavel = ""
        self.cron_edit_inicio = ""
        self.cron_edit_termino = ""
        self.cron_edit_pct = "0"
        self.cron_edit_critico = False
        self.cron_edit_dependencia = ""
        self.cron_edit_observacoes = ""
        self.cron_error = ""
        # Hierarchy defaults
        if parent_id:
            self.cron_edit_nivel = "micro"
            self.cron_edit_parent_id = parent_id
            # Inherit fase_macro from parent
            parent = next((r for r in self.cron_rows if r["id"] == parent_id), None)
            if parent:
                self.cron_edit_fase_macro = parent.get("fase_macro", "")
                self.cron_edit_fase = parent.get("fase", "")
        else:
            self.cron_edit_nivel = "macro"
            self.cron_edit_parent_id = ""
        self.cron_edit_peso = "100"
        self.cron_show_dialog = True

    def open_cron_edit(self, row_id: str):
        row = next((r for r in self.cron_rows if r["id"] == row_id), None)
        if not row:
            return
        self.cron_edit_id = row_id
        self.cron_edit_atividade = row.get("atividade", "")
        self.cron_edit_fase_macro = row.get("fase_macro", "")
        self.cron_edit_fase = row.get("fase", "")
        self.cron_edit_responsavel = row.get("responsavel", "")
        self.cron_edit_inicio = row.get("inicio_iso", row.get("inicio_previsto", ""))
        self.cron_edit_termino = row.get("termino_iso", row.get("termino_previsto", ""))
        self.cron_edit_pct = row.get("conclusao_pct", "0")
        self.cron_edit_critico = row.get("critico", "0") == "1"
        self.cron_edit_dependencia = row.get("dependencia", "")
        self.cron_edit_observacoes = row.get("observacoes", "")
        # Hierarchy
        self.cron_edit_nivel = row.get("nivel", "macro")
        self.cron_edit_parent_id = row.get("parent_id", "")
        self.cron_edit_peso = row.get("peso_pct", "100")
        self.cron_error = ""
        self.cron_show_dialog = True

    def close_cron_dialog(self):
        self.cron_show_dialog = False

    def set_cron_show_dialog(self, v: bool):
        self.cron_show_dialog = v

    def set_cron_edit_atividade(self, v: str): self.cron_edit_atividade = v
    def set_cron_edit_fase_macro(self, v: str): self.cron_edit_fase_macro = v
    def set_cron_edit_fase(self, v: str): self.cron_edit_fase = v
    def set_cron_edit_responsavel(self, v: str): self.cron_edit_responsavel = v
    def set_cron_edit_inicio(self, v: str): self.cron_edit_inicio = v
    def set_cron_edit_termino(self, v: str): self.cron_edit_termino = v
    def set_cron_edit_pct(self, v): self.cron_edit_pct = str(v)
    def toggle_cron_edit_critico(self): self.cron_edit_critico = not self.cron_edit_critico
    def set_cron_edit_dependencia(self, v: str): self.cron_edit_dependencia = "" if v == "__none__" else v
    def set_cron_edit_observacoes(self, v: str): self.cron_edit_observacoes = v
    def set_cron_edit_nivel(self, v: str): self.cron_edit_nivel = v
    def set_cron_edit_peso(self, v): self.cron_edit_peso = str(v)
    def set_cron_edit_parent_id(self, v: str): self.cron_edit_parent_id = v

    def toggle_macro_expanded(self, macro_id: str):
        if macro_id in self.cron_expanded_macros:
            self.cron_expanded_macros = [x for x in self.cron_expanded_macros if x != macro_id]
        else:
            new_list = list(self.cron_expanded_macros)
            new_list.append(macro_id)
            self.cron_expanded_macros = new_list

    # ── Save ─────────────────────────────────────────────────────────────────

    @rx.event(background=True)
    async def save_cron_activity(self):
        """INSERT or UPDATE a hub_atividade row."""
        from bomtempo.state.global_state import GlobalState

        contrato = ""
        atividade_nome = ""
        edit_id = ""
        edit_inicio = ""
        edit_termino = ""
        edit_pct = 0
        edit_critico = False
        edit_dependencia = ""
        edit_observacoes = ""
        edit_fase_macro = ""
        edit_fase = ""
        edit_responsavel = ""
        edit_nivel = "macro"
        edit_parent_id = ""
        edit_peso = 100

        async with self:
            if not self.cron_edit_atividade.strip():
                self.cron_error = "Nome da atividade é obrigatório."
                return
            self.cron_saving = True
            self.cron_error = ""
            contrato = self.cron_rows[0].get("contrato", "") if self.cron_rows else ""
            atividade_nome = self.cron_edit_atividade.strip()
            edit_id = self.cron_edit_id
            edit_fase_macro = self.cron_edit_fase_macro.strip()
            edit_fase = self.cron_edit_fase.strip()
            edit_responsavel = self.cron_edit_responsavel.strip()
            edit_inicio = self.cron_edit_inicio or None
            edit_termino = self.cron_edit_termino or None
            edit_pct = int(self.cron_edit_pct or 0)
            edit_critico = self.cron_edit_critico
            edit_dependencia = self.cron_edit_dependencia.strip()
            edit_observacoes = self.cron_edit_observacoes.strip()
            edit_nivel = self.cron_edit_nivel or "macro"
            edit_parent_id = self.cron_edit_parent_id or None
            edit_peso = int(self.cron_edit_peso or 100)
            # Sempre busca GlobalState para client_id + fallback de contrato
            gs = await self.get_state(GlobalState)
            if not contrato:
                contrato = str(gs.selected_contrato or gs.selected_project or "")
            client_id = str(gs.current_client_id or "")

        try:
            data: Dict[str, Any] = {
                "contrato":         contrato,
                "fase_macro":       edit_fase_macro,
                "fase":             edit_fase,
                "atividade":        atividade_nome,
                "responsavel":      edit_responsavel,
                "inicio_previsto":  edit_inicio,
                "termino_previsto": edit_termino,
                "conclusao_pct":    edit_pct,
                "critico":          edit_critico,
                "dependencia":      edit_dependencia,
                "observacoes":      edit_observacoes,
                "nivel":            edit_nivel,
                "parent_id":        edit_parent_id,
                "peso_pct":         edit_peso,
                "client_id":        client_id,
            }

            if edit_id:
                sb_update("hub_atividades", filters={"id": edit_id}, data=data)
                action = f"Atividade '{atividade_nome}' atualizada"
            else:
                sb_insert("hub_atividades", data)
                action = f"Atividade '{atividade_nome}' criada"

            audit_log(
                category=AuditCategory.DATA_EDIT,
                action=action,
                username="",
                entity_type="hub_atividades",
                entity_id=edit_id or "new",
                metadata={"contrato": contrato, "atividade": atividade_nome},
            )

        except Exception as e:
            logger.error(f"save_cron_activity error: {e}")
            async with self:
                self.cron_error = f"Erro: {str(e)[:120]}"
                self.cron_saving = False
            return

        # Reload
        async with self:
            self.cron_show_dialog = False
            self.cron_saving = False

        yield HubState.load_cronograma(contrato)

    # ── Delete ────────────────────────────────────────────────────────────────

    def request_cron_delete(self, row_id: str):
        row = next((r for r in self.cron_rows if r["id"] == row_id), None)
        self.cron_delete_id = row_id
        self.cron_delete_name = row.get("atividade", row_id) if row else row_id
        self.cron_show_delete = True

    def cancel_cron_delete(self):
        self.cron_delete_id = ""
        self.cron_show_delete = False

    @rx.event(background=True)
    async def confirm_cron_delete(self):
        row_id = ""
        name = ""
        contrato = ""
        async with self:
            row_id = str(self.cron_delete_id)
            name = str(self.cron_delete_name)
            contrato = self.cron_rows[0].get("contrato", "") if self.cron_rows else ""
            self.cron_show_delete = False
            self.cron_delete_id = ""

        try:
            sb_delete("hub_atividades", filters={"id": row_id})
            audit_log(
                category=AuditCategory.DATA_DELETE,
                action=f"Atividade '{name}' excluída",
                username="",
                entity_type="hub_atividades",
                entity_id=row_id,
            )
        except Exception as e:
            logger.error(f"confirm_cron_delete error: {e}")

        if contrato:
            yield HubState.load_cronograma(contrato)

    # ── Approve / Reject pending activities ───────────────────────────────────

    @rx.event(background=True)
    async def approve_pending_activity(self, activity_id: str):
        """Approve a pending activity (set pendente_aprovacao=False)."""
        contrato = ""
        async with self:
            self.cron_approve_loading = True
            contrato = self.cron_rows[0].get("contrato", "") if self.cron_rows else ""
        try:
            sb_update("hub_atividades", filters={"id": activity_id}, data={"pendente_aprovacao": False})
        except Exception as e:
            logger.error(f"approve_pending_activity error: {e}")
        async with self:
            self.cron_approve_loading = False
        if contrato:
            yield HubState.load_cronograma(contrato)

    @rx.event(background=True)
    async def reject_pending_activity(self, activity_id: str):
        """Reject (delete) a pending activity."""
        contrato = ""
        async with self:
            self.cron_approve_loading = True
            contrato = self.cron_rows[0].get("contrato", "") if self.cron_rows else ""
        try:
            sb_delete("hub_atividades", filters={"id": activity_id})
        except Exception as e:
            logger.error(f"reject_pending_activity error: {e}")
        async with self:
            self.cron_approve_loading = False
        if contrato:
            yield HubState.load_cronograma(contrato)

    # ── IA Climate Analysis ────────────────────────────────────────────────────

    @rx.event(background=True)
    async def analyze_climate_impact(self):
        """Cross-reference scheduled activities with weather forecast via IA."""
        from bomtempo.state.global_state import GlobalState

        weather = {}
        rows = []
        async with self:
            self.cron_climate_loading = True
            self.cron_climate_analysis = ""
            gs = await self.get_state(GlobalState)
            weather = dict(gs.weather_data) if gs.weather_data else {}
            rows = list(self.cron_rows)

        # Build context
        from datetime import date
        today_iso = date.today().isoformat()
        weather_summary = ""
        if weather and weather.get("daily_time"):
            lines = []
            for i, dt in enumerate(weather["daily_time"][:7]):
                prob = weather["daily_rain_prob"][i] if i < len(weather.get("daily_rain_prob", [])) else 0
                rain = weather["daily_rain_sum"][i] if i < len(weather.get("daily_rain_sum", [])) else 0
                lines.append(f"  {dt}: chuva {rain:.1f}mm, prob. {prob}%")
            weather_summary = "\n".join(lines)
        else:
            weather_summary = "  Dados climáticos não disponíveis"

        activities_summary = ""
        if rows:
            act_lines = []
            for r in rows[:20]:
                act_lines.append(
                    f"  • {r['atividade']} ({r['fase_macro']}) | {r['inicio_previsto']} → {r['termino_previsto']} | {r['conclusao_pct']}% | crítico: {'sim' if r['critico']=='1' else 'não'}"
                )
            activities_summary = "\n".join(act_lines)
        else:
            activities_summary = "  Nenhuma atividade cadastrada"

        messages = [
            {
                "role": "user",
                "content": (
                    f"Você é um engenheiro de obras sênior analisando impacto climático em um cronograma de construção.\n\n"
                    f"DATA ATUAL: {today_iso}\n\n"
                    f"PREVISÃO CLIMÁTICA (próximos 7 dias):\n{weather_summary}\n\n"
                    f"ATIVIDADES DO CRONOGRAMA:\n{activities_summary}\n\n"
                    f"Analise quais atividades previstas para os próximos 7 dias serão impactadas pela chuva, "
                    f"especialmente as críticas. Dê recomendações práticas: o que antecipar, o que proteger, "
                    f"o que reagendar. Seja direto e objetivo, máximo 200 palavras."
                ),
            }
        ]

        try:
            import queue as _queue
            import threading
            result_queue: _queue.Queue = _queue.Queue()

            def _run_analysis():
                try:
                    # Use direct AI call
                    from bomtempo.core.ai_client import ai_client
                    full_text = ""
                    for chunk in ai_client.query_stream(messages):
                        full_text += chunk
                    result_queue.put(("ok", full_text))
                except Exception as ex:
                    result_queue.put(("err", str(ex)))

            t = threading.Thread(target=_run_analysis, daemon=True)
            t.start()
            t.join(timeout=60)

            if not result_queue.empty():
                status, text = result_queue.get()
                async with self:
                    self.cron_climate_analysis = text if status == "ok" else f"Erro na análise: {text[:200]}"
            else:
                async with self:
                    self.cron_climate_analysis = "Tempo esgotado ao consultar IA. Tente novamente."

        except Exception as e:
            logger.error(f"analyze_climate_impact error: {e}")
            async with self:
                self.cron_climate_analysis = f"Erro: {str(e)[:200]}"
        finally:
            async with self:
                self.cron_climate_loading = False

    def clear_climate_analysis(self):
        self.cron_climate_analysis = ""

    # ══════════════════════════════════════════════════════════════════════════
    # AUDITORIA — Load, gallery, lightbox
    # ══════════════════════════════════════════════════════════════════════════

    @rx.event(background=True)
    async def load_auditoria(self, contrato: str):
        async with self:
            self.audit_loading = True
            self.audit_images = []
            self.audit_open_category = ""

        # Captura client_id para isolamento de tenant
        client_id = ""
        try:
            from bomtempo.state.global_state import GlobalState
            _gs = await self.get_state(GlobalState)
            client_id = str(_gs.current_client_id or "")
        except Exception:
            pass

        try:
            # 1. Manual uploads in hub_auditoria_imgs
            _audit_filters: dict = {"contrato": contrato}
            if client_id:
                _audit_filters["client_id"] = client_id
            rows = sb_select(
                "hub_auditoria_imgs",
                filters=_audit_filters,
                order="created_at.desc",
                limit=500,
            )
            imgs = [
                {
                    "id":           _norm_str(r.get("id")),
                    "contrato":     _norm_str(r.get("contrato")),
                    "categoria":    _norm_str(r.get("categoria")),
                    "url":          _norm_str(r.get("url")),
                    "legenda":      _norm_str(r.get("legenda")),
                    "data_captura": _utc_date_to_br(_norm_str(r.get("data_captura"))),
                    "autor":        _norm_str(r.get("autor"), "—"),
                }
                for r in rows
            ]

            # 2. Integrate RDO photos from rdo_master (epi, ferramentas, evidencias)
            try:
                _rdo_filters: dict = {"contrato": contrato}
                if client_id:
                    _rdo_filters["client_id"] = client_id
                rdos = sb_select(
                    "rdo_master",
                    filters=_rdo_filters,
                    order="created_at.desc",
                    limit=200,
                )
                import json as _json
                for rdo in (rdos or []):
                    rdo_date = _utc_date_to_br(_norm_str(rdo.get("created_at", "") or rdo.get("data_rdo", "")))
                    rdo_autor = _norm_str(rdo.get("mestre_id", rdo.get("responsavel_tecnico", "RDO")))
                    rdo_id = _norm_str(rdo.get("id_rdo", rdo.get("id", "")))

                    # EPI photo
                    epi_url = _norm_str(rdo.get("epi_foto_url", ""))
                    if epi_url:
                        imgs.append({
                            "id":           f"rdo_epi_{rdo_id}",
                            "contrato":     contrato,
                            "categoria":    "equipe",
                            "url":          epi_url,
                            "legenda":      f"EPI — RDO {rdo_id[:8]}",
                            "data_captura": rdo_date,
                            "autor":        rdo_autor,
                        })

                    # Ferramentas photo
                    ferr_url = _norm_str(rdo.get("ferramentas_foto_url", ""))
                    if ferr_url:
                        imgs.append({
                            "id":           f"rdo_ferr_{rdo_id}",
                            "contrato":     contrato,
                            "categoria":    "ferramentas",
                            "url":          ferr_url,
                            "legenda":      f"Ferramentas — RDO {rdo_id[:8]}",
                            "data_captura": rdo_date,
                            "autor":        rdo_autor,
                        })

                    # Evidence photos (jsonb array)
                    evidencias_raw = rdo.get("evidencias") or []
                    if isinstance(evidencias_raw, str):
                        try:
                            evidencias_raw = _json.loads(evidencias_raw)
                        except Exception:
                            evidencias_raw = []
                    for idx, ev in enumerate(evidencias_raw or []):
                        ev_url = _norm_str(ev.get("foto_url", "") if isinstance(ev, dict) else "")
                        if ev_url:
                            legenda = _norm_str(ev.get("legenda", "") if isinstance(ev, dict) else "")
                            imgs.append({
                                "id":           f"rdo_ev_{rdo_id}_{idx}",
                                "contrato":     contrato,
                                "categoria":    "gerais",
                                "url":          ev_url,
                                "legenda":      legenda or f"Foto {idx+1} — RDO {rdo_id[:8]}",
                                "data_captura": rdo_date,
                                "autor":        rdo_autor,
                            })
            except Exception as e2:
                logger.warning(f"load_auditoria RDO integration error (non-fatal): {e2}")

        except Exception as e:
            logger.error(f"load_auditoria error: {e}")
            imgs = []

        async with self:
            self.audit_images = imgs
            self.audit_loading = False

    def open_audit_category(self, slug: str):
        # Toggle: clicking same category closes it
        self.audit_open_category = "" if self.audit_open_category == slug else slug

    def close_audit_category(self):
        self.audit_open_category = ""
        self.audit_lightbox_url = ""

    def open_lightbox(self, img_id: str):
        img = next((i for i in self.audit_images if i["id"] == img_id), None)
        if img:
            self.audit_lightbox_url = img["url"]
            self.audit_lightbox_legenda = img["legenda"]
            self.audit_lightbox_data = img["data_captura"]
            self.audit_lightbox_autor = img["autor"]

    def close_lightbox(self):
        self.audit_lightbox_url = ""

    def open_audit_upload(self, slug: str):
        self.audit_upload_category = slug
        self.audit_upload_url = ""
        self.audit_upload_legenda = ""
        self.audit_upload_error = ""
        self.audit_show_upload = True

    def close_audit_upload(self):
        self.audit_show_upload = False

    def set_audit_upload_url(self, v: str): self.audit_upload_url = v
    def set_audit_upload_legenda(self, v: str): self.audit_upload_legenda = v

    @rx.event(background=True)
    async def save_audit_image(self):
        from bomtempo.state.global_state import GlobalState

        contrato = ""
        autor = ""
        upload_category = ""
        upload_url = ""
        upload_legenda = ""

        async with self:
            if not self.audit_upload_url.strip():
                self.audit_upload_error = "URL da imagem é obrigatória."
                return
            self.audit_uploading = True
            self.audit_upload_error = ""
            contrato = self.audit_images[0]["contrato"] if self.audit_images else ""
            upload_category = str(self.audit_upload_category)
            upload_url = str(self.audit_upload_url).strip()
            upload_legenda = str(self.audit_upload_legenda).strip()
            gs = await self.get_state(GlobalState)
            autor = str(gs.current_user_name or "")
            if not contrato:
                contrato = str(gs.selected_contrato or gs.selected_project or "")

        from datetime import date as _date
        try:
            sb_insert("hub_auditoria_imgs", {
                "contrato":     contrato,
                "categoria":    upload_category,
                "url":          upload_url,
                "legenda":      upload_legenda,
                "autor":        autor,
                "data_captura": _date.today().isoformat(),
                "client_id":    str(gs.current_client_id or ""),
            })
        except Exception as e:
            logger.error(f"save_audit_image error: {e}")
            async with self:
                self.audit_upload_error = f"Erro: {str(e)[:100]}"
                self.audit_uploading = False
            return

        async with self:
            self.audit_show_upload = False
            self.audit_uploading = False

        yield HubState.load_auditoria(contrato)

    @rx.event(background=True)
    async def delete_audit_image(self, img_id: str):
        contrato = ""
        async with self:
            contrato = self.audit_images[0]["contrato"] if self.audit_images else ""
        try:
            sb_delete("hub_auditoria_imgs", filters={"id": img_id})
        except Exception as e:
            logger.error(f"delete_audit_image error: {e}")
        if contrato:
            yield HubState.load_auditoria(contrato)

    # ══════════════════════════════════════════════════════════════════════════
    # TIMELINE — Load & post
    # ══════════════════════════════════════════════════════════════════════════

    @rx.event(background=True)
    async def load_timeline(self, contrato: str):
        async with self:
            self.timeline_loading = True
            self.timeline_entries = []

        # Captura client_id para isolamento de tenant
        _tl_client_id = ""
        try:
            from bomtempo.state.global_state import GlobalState
            _tl_gs = await self.get_state(GlobalState)
            _tl_client_id = str(_tl_gs.current_client_id or "")
        except Exception:
            pass

        try:
            _tl_filters: dict = {"contrato": contrato}
            if _tl_client_id:
                _tl_filters["client_id"] = _tl_client_id
            rows = sb_select(
                "hub_timeline",
                filters=_tl_filters,
                order="created_at.desc",
                limit=200,
            )
            entries = [
                {
                    "id":              _norm_str(r.get("id")),
                    "contrato":        _norm_str(r.get("contrato")),
                    "tipo":            _norm_str(r.get("tipo"), "Atualização"),
                    "titulo":          _norm_str(r.get("titulo")),
                    "descricao":       _norm_str(r.get("descricao")),
                    "autor":           _norm_str(r.get("autor"), "—"),
                    "created_at":      _utc_to_brt(_norm_str(r.get("created_at"))),
                    "is_document":     "1" if r.get("is_document") else "0",
                    "is_cost":         "1" if r.get("is_cost") else "0",
                    "custo_valor":     _norm_str(r.get("custo_valor")),
                    "custo_categoria": _norm_str(r.get("custo_categoria")),
                    "anexo_url":       _norm_str(r.get("anexo_url")),
                    "anexo_nome":      _norm_str(r.get("anexo_nome")),
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"load_timeline error: {e}")
            entries = []

        # Load mention users list
        try:
            login_rows = sb_select("login", limit=100) or []
            mention_users = [str(r.get("user", "")).strip() for r in login_rows if r.get("user")]
        except Exception:
            mention_users = []

        async with self:
            self.timeline_entries = entries
            self.timeline_loading = False
            if mention_users:
                self.tl_mention_users = mention_users

    def set_tl_entry_type(self, v: str): self.tl_entry_type = v
    def set_tl_titulo(self, v: str): self.tl_titulo = v
    def set_tl_descricao(self, v: str): self.tl_descricao = v
    def set_tl_filter_tipo(self, v: str):
        self.tl_filter_tipo = "" if self.tl_filter_tipo == v else v
    def set_tl_search(self, v: str): self.tl_search = v
    def set_tl_search_input(self, v: str): self.tl_search_input = v
    def commit_tl_search(self, _v: str = ""):
        self.tl_search = self.tl_search_input
    def handle_tl_search_key(self, key: str):
        if key == "Enter":
            self.tl_search = self.tl_search_input
    def set_tl_custo_valor(self, v: str): self.tl_custo_valor = v
    def set_tl_custo_categoria(self, v: str): self.tl_custo_categoria = v

    async def upload_tl_anexo(self, files: list[rx.UploadFile]):
        """Upload file attachment to Supabase Storage bucket 'timeline-anexos'."""
        if not files:
            return
        file = files[0]
        self.tl_uploading_anexo = True
        yield

        try:
            import asyncio as _asyncio
            import re as _re
            from datetime import datetime as _dt
            from bomtempo.core.supabase_client import sb_storage_ensure_bucket, sb_storage_upload

            data = await file.read()
            nome = getattr(file, "filename", getattr(file, "name", "arquivo"))
            safe_name = _re.sub(r"[^\w\.\-]", "_", nome)
            path = f"{_dt.now().strftime('%Y%m%d_%H%M%S')}_{safe_name}"

            loop = _asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: sb_storage_ensure_bucket("timeline-anexos", public=True))
            url = await loop.run_in_executor(None, lambda: sb_storage_upload("timeline-anexos", path, data, "application/octet-stream"))

            self.tl_anexo_url = url or ""
            self.tl_anexo_nome = nome
            self.tl_uploading_anexo = False
        except Exception as e:
            logger.error(f"upload_tl_anexo error: {e}")
            self.tl_uploading_anexo = False
            self.tl_error = f"Erro no upload: {str(e)[:80]}"

    @rx.event(background=True)
    async def submit_timeline_entry(self):
        from bomtempo.state.global_state import GlobalState

        contrato = ""
        autor = ""
        entry_tipo = ""
        entry_titulo = ""
        entry_descricao = ""
        entry_is_document = False
        entry_is_cost = False
        entry_custo_valor = ""
        entry_custo_categoria = ""
        entry_anexo_url = ""
        entry_anexo_nome = ""
        entry_mencoes: list = []

        async with self:
            if not self.tl_titulo.strip():
                self.tl_error = "Título é obrigatório."
                return
            self.tl_submitting = True
            self.tl_error = ""
            contrato = self.timeline_entries[0]["contrato"] if self.timeline_entries else ""
            entry_tipo = str(self.tl_entry_type)
            entry_titulo = str(self.tl_titulo).strip()
            entry_descricao = str(self.tl_descricao).strip()
            entry_is_document = entry_tipo == "Documento"
            entry_is_cost = entry_tipo == "Custo"
            entry_custo_valor = str(self.tl_custo_valor)
            entry_custo_categoria = str(self.tl_custo_categoria)
            entry_anexo_url = str(self.tl_anexo_url)
            entry_anexo_nome = str(self.tl_anexo_nome)
            # Extract @mentions from title + description
            import re as _re
            raw_text = f"{entry_titulo} {entry_descricao}"
            entry_mencoes = list(set(_re.findall(r"@(\w+)", raw_text)))
            gs = await self.get_state(GlobalState)
            autor = str(gs.current_user_name or "")
            if not contrato:
                contrato = str(gs.selected_contrato or gs.selected_project or "")

        try:
            sb_insert("hub_timeline", {
                "contrato":        contrato,
                "tipo":            entry_tipo,
                "titulo":          entry_titulo,
                "descricao":       entry_descricao,
                "autor":           autor,
                "mencoes":         entry_mencoes,
                "is_document":     entry_is_document,
                "is_cost":         entry_is_cost,
                "custo_valor":     float(entry_custo_valor.replace(",", ".")) if entry_is_cost and entry_custo_valor else None,
                "custo_categoria": entry_custo_categoria if entry_is_cost else None,
                "anexo_url":       entry_anexo_url or None,
                "anexo_nome":      entry_anexo_nome or None,
                "client_id":       str(gs.current_client_id or ""),
            })
            audit_log(
                category=AuditCategory.DATA_EDIT,
                action=f"Timeline entry: [{entry_tipo}] {entry_titulo[:60]}",
                username=autor,
                entity_type="hub_timeline",
                entity_id=contrato,
            )
            # Create notifications for @mentioned users
            if entry_mencoes:
                _notif_msg = f"@{autor} mencionou você: [{entry_tipo}] {entry_titulo[:80]}"
                for mentioned_user in entry_mencoes:
                    if mentioned_user:
                        try:
                            sb_insert("user_notifications", {
                                "recipient": mentioned_user,
                                "sender": autor,
                                "message": _notif_msg,
                                "source_type": "mention",
                                "source_id": contrato,
                                "contrato": contrato,
                                "read": False,
                                "client_id": str(gs.current_client_id or ""),
                            })
                        except Exception as ne:
                            logger.warning(f"Failed to create notification for @{mentioned_user}: {ne}")
        except Exception as e:
            logger.error(f"submit_timeline_entry error: {e}")
            async with self:
                self.tl_error = f"Erro: {str(e)[:100]}"
                self.tl_submitting = False
            return

        async with self:
            self.tl_titulo = ""
            self.tl_descricao = ""
            self.tl_entry_type = "Atualização"
            self.tl_custo_valor = ""
            self.tl_custo_categoria = "Operacional"
            self.tl_anexo_url = ""
            self.tl_anexo_nome = ""
            self.tl_submitting = False

        yield HubState.load_timeline(contrato)

    @rx.event(background=True)
    async def delete_timeline_entry(self, entry_id: str):
        contrato = ""
        async with self:
            contrato = self.timeline_entries[0]["contrato"] if self.timeline_entries else ""
        try:
            sb_delete("hub_timeline", filters={"id": entry_id})
        except Exception as e:
            logger.error(f"delete_timeline_entry error: {e}")
        if contrato:
            yield HubState.load_timeline(contrato)
