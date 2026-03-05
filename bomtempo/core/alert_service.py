"""
AlertService — Bomtempo Intelligence
Manages alert subscriptions, sweep execution, email dispatch, and
background scheduling for the Proactive Alerts module.

Tables used (zero schema migrations required):
  • email_sender       — one row per (contract, email, module='alertas_ALERT_TYPE')
  • alert_subscriptions — one row per alert_type (global on/off toggle)
                          user_email = 'scheduler@bomtempo.com.br' (sentinel)
  • alert_history      — one row per sweep execution (project_code, alert_type, message)
"""
from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from bomtempo.core.logging_utils import get_logger
from bomtempo.core.supabase_client import sb_delete, sb_insert, sb_select, sb_update

logger = get_logger(__name__)

# ── Alert type registry ────────────────────────────────────────────────────────

ALERT_TYPES: Dict[str, Dict[str, str]] = {
    "daily": {
        "label": "Resumo Diário",
        "category": "cronologico",
        "icon": "sun",
        "color": "#2A9D8F",
        "description": "Resumo automático enviado diariamente às 18h com avanço físico, risco e efetivo de campo.",
        "schedule": "Todos os dias às 18h",
    },
    "weekly": {
        "label": "Resumo Semanal",
        "category": "cronologico",
        "icon": "calendar-days",
        "color": "#3B82F6",
        "description": "Consolidado semanal enviado toda segunda-feira às 8h com comparativo da semana anterior.",
        "schedule": "Toda segunda-feira às 8h",
    },
    "monthly": {
        "label": "Fechamento de Medição",
        "category": "cronologico",
        "icon": "file-text",
        "color": "#C98B2A",
        "description": "Balanço financeiro enviado todo dia 25 com execução vs planejado do ciclo.",
        "schedule": "Todo dia 25 às 9h",
    },
    "risk_high": {
        "label": "Risco Alto (≥70)",
        "category": "reativo",
        "icon": "alert-triangle",
        "color": "#EF4444",
        "description": "Disparado quando o score de risco geral do contrato atinge ou ultrapassa 70.",
        "schedule": "Verificado diariamente às 18h",
    },
    "budget_overage": {
        "label": "Budget Estourado >5%",
        "category": "reativo",
        "icon": "trending-up",
        "color": "#F59E0B",
        "description": "Disparado quando o valor realizado ultrapassa o planejado em mais de 5%.",
        "schedule": "Verificado diariamente às 18h",
    },
    "rdo_pending": {
        "label": "RDO Pendente (48h)",
        "category": "reativo",
        "icon": "clock",
        "color": "#8B5CF6",
        "description": "Disparado quando nenhum RDO foi submetido para um contrato há mais de 48 horas.",
        "schedule": "Verificado diariamente às 18h",
    },
}

_SENTINEL_EMAIL = "scheduler@bomtempo.com.br"
_TABLE_SUBS = "alert_subscriptions"   # global toggle per alert_type
_TABLE_EMAIL = "email_sender"          # per-contract email recipients
_TABLE_HIST = "alert_history"

# ── Module name helpers ───────────────────────────────────────────────────────

def _module_name(alert_type: str) -> str:
    return f"alertas_{alert_type}"

def _alert_type_from_module(module: str) -> str:
    return module.replace("alertas_", "", 1)


class AlertService:

    # ────────────────────────────────────────────────────────────────────────
    # Toggle state — alert_subscriptions table (global on/off per alert_type)
    # ────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _ensure_toggle_row(alert_type: str) -> Optional[Dict]:
        """Ensure a toggle row exists for the given alert_type. Creates if missing."""
        rows = sb_select(_TABLE_SUBS, filters={"alert_type": alert_type, "user_email": _SENTINEL_EMAIL})
        if rows:
            return rows[0]
        try:
            return sb_insert(_TABLE_SUBS, {
                "user_email": _SENTINEL_EMAIL,
                "alert_type": alert_type,
                "is_active": True,
            })
        except Exception as exc:
            logger.warning(f"[AlertService._ensure_toggle_row] {exc}")
            return None

    @staticmethod
    def get_toggle_states() -> Dict[str, bool]:
        """Returns {alert_type: is_active} for all alert types."""
        rows = sb_select(_TABLE_SUBS, filters={"user_email": _SENTINEL_EMAIL}) or []
        state: Dict[str, bool] = {k: True for k in ALERT_TYPES}  # default all active
        for row in rows:
            at = str(row.get("alert_type", ""))
            if at in state:
                state[at] = bool(row.get("is_active", True))
        return state

    @staticmethod
    def set_toggle(alert_type: str, is_active: bool) -> bool:
        """Toggle a global alert type on or off."""
        row = AlertService._ensure_toggle_row(alert_type)
        if not row:
            return False
        try:
            sb_update(_TABLE_SUBS, {"id": row["id"]}, {"is_active": is_active})
            return True
        except Exception as exc:
            logger.error(f"[AlertService.set_toggle] {exc}")
            return False

    # ────────────────────────────────────────────────────────────────────────
    # Subscription CRUD — email_sender table
    # ────────────────────────────────────────────────────────────────────────

    @staticmethod
    def get_email_subscriptions() -> List[Dict]:
        """All alertas subscriptions from email_sender, grouped by (alert_type, contract)."""
        all_rows: List[Dict] = []
        for at in ALERT_TYPES:
            rows = sb_select(_TABLE_EMAIL, filters={"module": _module_name(at)}) or []
            all_rows.extend(rows)

        groups: Dict[Tuple[str, str], Dict] = {}
        for row in all_rows:
            module = str(row.get("module", ""))
            at = _alert_type_from_module(module)
            ct = str(row.get("contract", "")).strip()
            key = (at, ct)
            if key not in groups:
                meta = ALERT_TYPES.get(at, {})
                groups[key] = {
                    "alert_type": at,
                    "alert_label": meta.get("label", at),
                    "alert_color": meta.get("color", "#C98B2A"),
                    "contract": ct,
                    "email_chips": [],
                    "key": f"{at}|{ct}",
                }
            email = str(row.get("email", "")).strip()
            row_id = str(row.get("id", ""))
            if email:
                groups[key]["email_chips"].append({"email": email, "id": row_id})

        result = list(groups.values())
        for g in result:
            g["count"] = str(len(g["email_chips"]))
            g["emails_display"] = ", ".join(c["email"] for c in g["email_chips"])
        return result

    @staticmethod
    def email_exists(alert_type: str, contract: str, email: str) -> bool:
        rows = sb_select(
            _TABLE_EMAIL,
            filters={"module": _module_name(alert_type), "contract": contract, "email": email.lower().strip()},
        ) or []
        return len(rows) > 0

    @staticmethod
    def contract_has_subscription(alert_type: str, contract: str) -> bool:
        rows = sb_select(
            _TABLE_EMAIL,
            filters={"module": _module_name(alert_type), "contract": contract},
        ) or []
        return len(rows) > 0

    @staticmethod
    def add_email_subscription(
        alert_type: str, contract: str, email: str, created_by: str = "admin"
    ) -> Tuple[bool, str]:
        """
        Adds an email recipient for an alert+contract pair.
        Returns (success, message).
        """
        email = email.strip().lower()
        contract = contract.strip()

        if not email or "@" not in email or "." not in email:
            return False, "E-mail inválido."
        if not alert_type or alert_type not in ALERT_TYPES:
            return False, "Tipo de alerta inválido."
        if not contract:
            return False, "Contrato é obrigatório."
        if AlertService.email_exists(alert_type, contract, email):
            return False, f"'{email}' já está cadastrado para este alerta neste contrato."

        existing = AlertService.contract_has_subscription(alert_type, contract)
        try:
            sb_insert(_TABLE_EMAIL, {
                "contract": contract,
                "email": email,
                "module": _module_name(alert_type),
                "created_by": created_by,
                "updated_date": datetime.now().isoformat(),
            })
            if existing:
                return True, f"E-mail adicionado ao grupo de '{ALERT_TYPES[alert_type]['label']}' — {contract}."
            return True, f"Novo alerta configurado: '{ALERT_TYPES[alert_type]['label']}' para {contract}."
        except Exception as exc:
            logger.error(f"[AlertService.add_email_subscription] {exc}")
            return False, "Erro ao salvar. Tente novamente."

    @staticmethod
    def delete_email_subscription(row_id: str) -> bool:
        """Delete a single email subscription row by its ID."""
        return sb_delete(_TABLE_EMAIL, {"id": row_id})

    @staticmethod
    def get_recipients(alert_type: str, contract: str) -> List[str]:
        """Return list of recipient emails for a given alert_type + contract."""
        rows = sb_select(
            _TABLE_EMAIL,
            filters={"module": _module_name(alert_type), "contract": contract},
        ) or []
        return [str(r.get("email", "")).strip() for r in rows if r.get("email")]

    # ────────────────────────────────────────────────────────────────────────
    # Alert History
    # ────────────────────────────────────────────────────────────────────────

    @staticmethod
    def get_history(limit: int = 50) -> List[Dict]:
        return sb_select(_TABLE_HIST, order="timestamp.desc", limit=limit) or []

    @staticmethod
    def _log_history(contract: str, alert_type: str, message: str) -> None:
        # project_code has FK to contratos — leave NULL, contract info is in message
        try:
            sb_insert(_TABLE_HIST, {
                "alert_type": alert_type,
                "message": f"[{contract}] {message}"[:500],
                "is_read": False,
            })
        except Exception as exc:
            logger.warning(f"[AlertService._log_history] {exc}")

    # ────────────────────────────────────────────────────────────────────────
    # Sweep logic
    # ────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _get_obras_map() -> Dict[str, Dict]:
        """Build contract_code → obra dict. Handles both capitalized GSheets and snake_case columns."""
        obras = sb_select("obras", limit=500) or []
        result: Dict[str, Dict] = {}
        for obra in obras:
            cid = str(
                obra.get("Contrato") or obra.get("contrato") or
                obra.get("ID") or obra.get("id") or ""
            ).strip()
            if cid:
                result[cid] = obra
        return result

    @staticmethod
    def _build_message(contract: str, obra: Dict, alert_type: str) -> str:
        meta = ALERT_TYPES.get(alert_type, {})
        label = meta.get("label", alert_type)
        avanco = (obra.get("Realizado (%)") or obra.get("avanco_fisico") or
                  obra.get("avanço_fisico") or "—")
        risco = obra.get("risco_geral_score") or "—"
        budget_p = obra.get("budget_planejado") or "—"
        budget_r = obra.get("budget_realizado") or "—"
        projeto = obra.get("Projeto") or obra.get("projeto") or "—"
        return (
            f"[{label}] {contract} | {projeto} | "
            f"Avanço: {avanco}% | Risco: {risco} | Exec: {budget_r}/{budget_p}"
        )

    @staticmethod
    def run_sweep(alert_type: str) -> Dict[str, int]:
        """
        Execute a sweep for the given alert_type.
        - Checks global toggle in alert_subscriptions.
        - Fetches recipients from email_sender.
        - Applies reactive conditions (risk_high, budget_overage).
        - Sends emails and logs to alert_history.
        Returns {"sent": n, "errors": n, "skipped": n}.
        """
        from bomtempo.core.email_service import EmailService

        # Check global toggle
        toggle_states = AlertService.get_toggle_states()
        if not toggle_states.get(alert_type, True):
            logger.info(f"[AlertService.sweep] '{alert_type}' is globally disabled — skip.")
            return {"sent": 0, "errors": 0, "skipped": 1}

        # Get all subscriptions for this alert_type
        all_rows = sb_select(_TABLE_EMAIL, filters={"module": _module_name(alert_type)}) or []
        if not all_rows:
            logger.info(f"[AlertService.sweep] No subscribers for '{alert_type}'.")
            return {"sent": 0, "errors": 0, "skipped": 0}

        # Group by contract
        contract_emails: Dict[str, List[str]] = {}
        for row in all_rows:
            ct = str(row.get("contract", "")).strip()
            em = str(row.get("email", "")).strip()
            if ct and em:
                contract_emails.setdefault(ct, []).append(em)

        obras_map = AlertService._get_obras_map()
        sent = errors = skipped = 0

        for contract, emails in contract_emails.items():
            obra = obras_map.get(contract, {})

            # Reactive filters — only send if condition is met
            if alert_type == "risk_high":
                try:
                    score = float(obra.get("risco_geral_score") or 0)
                    if score < 70:
                        skipped += 1
                        continue
                except (ValueError, TypeError):
                    skipped += 1
                    continue
            elif alert_type == "budget_overage":
                try:
                    bp = float(obra.get("budget_planejado") or 0)
                    br = float(obra.get("budget_realizado") or 0)
                    if bp <= 0 or br <= bp * 1.05:
                        skipped += 1
                        continue
                except (ValueError, TypeError):
                    skipped += 1
                    continue
            elif alert_type == "rdo_pending":
                # Fire only if no RDO was submitted for this contract in the last 48h
                from datetime import timedelta
                rdo_rows = sb_select(
                    "rdo_cabecalho",
                    filters={"Contrato": contract},
                    order="Data.desc",
                    limit=1,
                ) or []
                if rdo_rows:
                    last_date_str = str(rdo_rows[0].get("Data", ""))
                    try:
                        last_dt = datetime.strptime(last_date_str[:10], "%Y-%m-%d")
                        if datetime.now() - last_dt < timedelta(hours=48):
                            skipped += 1
                            continue
                    except (ValueError, TypeError):
                        pass  # can't parse date — send the alert anyway

            msg = AlertService._build_message(contract, obra, alert_type)
            try:
                EmailService.send_alert_email(
                    recipients=emails,
                    contract=contract,
                    alert_label=ALERT_TYPES[alert_type]["label"],
                    alert_color=ALERT_TYPES[alert_type]["color"],
                    obra_data=obra,
                )
                AlertService._log_history(contract, alert_type, msg)
                sent += 1
            except Exception as exc:
                logger.error(f"[AlertService.sweep] {alert_type}/{contract}: {exc}")
                errors += 1

        logger.info(f"[AlertService] Sweep '{alert_type}': sent={sent}, errors={errors}, skipped={skipped}")
        return {"sent": sent, "errors": errors, "skipped": skipped}


# ── Background Scheduler ───────────────────────────────────────────────────────

_scheduler_started = False
_scheduler_lock = threading.Lock()
_last_daily: Any = None
_last_weekly: Any = None
_last_monthly: Any = None


def _scheduler_loop() -> None:
    global _last_daily, _last_weekly, _last_monthly
    logger.info("[AlertScheduler] Background scheduler started — checking every 60s.")
    while True:
        try:
            now = datetime.now()
            today = now.date()
            this_week = now.isocalendar()[1]

            # Daily at 18h — includes reactive checks
            if now.hour == 18 and now.minute < 5 and _last_daily != today:
                logger.info("[AlertScheduler] Firing daily+reactive sweeps.")
                for at in ("daily", "risk_high", "budget_overage", "rdo_pending"):
                    AlertService.run_sweep(at)
                _last_daily = today

            # Weekly on Monday at 8h
            if now.weekday() == 0 and now.hour == 8 and now.minute < 5 and _last_weekly != this_week:
                logger.info("[AlertScheduler] Firing weekly sweep.")
                AlertService.run_sweep("weekly")
                _last_weekly = this_week

            # Monthly on day 25 at 9h
            if now.day == 25 and now.hour == 9 and now.minute < 5:
                month_key = (now.year, now.month)
                if _last_monthly != month_key:
                    logger.info("[AlertScheduler] Firing monthly sweep.")
                    AlertService.run_sweep("monthly")
                    _last_monthly = month_key

        except Exception as exc:
            logger.error(f"[AlertScheduler] Loop error: {exc}")
        time.sleep(60)


def start_alert_scheduler() -> None:
    """Start the background scheduler thread (idempotent)."""
    global _scheduler_started
    with _scheduler_lock:
        if not _scheduler_started:
            t = threading.Thread(target=_scheduler_loop, daemon=True, name="alert-scheduler")
            t.start()
            _scheduler_started = True
            logger.info("[AlertScheduler] Thread launched.")
