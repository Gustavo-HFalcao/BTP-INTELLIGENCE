"""
AlertasState — Bomtempo Intelligence
State management for the Proactive Alerts module.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta

import reflex as rx

from bomtempo.core.alert_service import ALERT_TYPES, AlertService
from bomtempo.core.logging_utils import get_logger
from bomtempo.core.audit_logger import audit_log, AuditCategory

logger = get_logger(__name__)


# ── Typed models (required for rx.foreach over nested lists) ──────────────────

class EmailChip(rx.Base):
    email: str = ""
    id: str = ""


class SubscriptionGroup(rx.Base):
    alert_type: str = ""
    alert_label: str = ""
    alert_color: str = "#C98B2A"
    contract: str = ""
    is_active: bool = True
    key: str = ""
    email_chips: list[EmailChip] = []
    emails_display: str = ""
    count: str = "0"


_BRT = timezone(timedelta(hours=-3))  # Brasília Time (UTC-3)


def _utc_to_brt(ts: str) -> str:
    """Convert UTC ISO timestamp to BRT display string 'DD/MM HH:MM'."""
    if not ts or ts in ("—", ""):
        return ts
    try:
        ts_norm = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts_norm[:32])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(_BRT).strftime("%d/%m %H:%M")
    except Exception:
        return ts[:16].replace("T", " ") if len(ts) >= 16 else ts


# ── Normalizers ───────────────────────────────────────────────────────────────

def _norm_group(g: dict) -> SubscriptionGroup:
    chips = [EmailChip(email=str(c["email"]), id=str(c["id"])) for c in g.get("email_chips", [])]
    return SubscriptionGroup(
        alert_type=str(g.get("alert_type", "")),
        alert_label=str(g.get("alert_label", "")),
        alert_color=str(g.get("alert_color", "#C98B2A")),
        contract=str(g.get("contract", "")),
        is_active=bool(g.get("is_active", True)),
        key=str(g.get("key", "")),
        email_chips=chips,
        emails_display=str(g.get("emails_display", "")),
        count=str(g.get("count", "0")),
    )


def _norm_hist(h: dict) -> dict:
    at = str(h.get("alert_type", "—"))
    ts = str(h.get("timestamp") or h.get("created_at") or "—")
    msg = str(h.get("message", "—"))
    # Contract is embedded in message as "[CT-XXX] ..." by _log_history
    contract = "—"
    if msg.startswith("[") and "]" in msg:
        contract = msg[1:msg.index("]")]
        msg = msg[msg.index("]") + 2:]
    return {
        "id": str(h.get("id", "")),
        "contract": contract,
        "alert_type": at,
        "alert_label": ALERT_TYPES.get(at, {}).get("label", at),
        "alert_color": ALERT_TYPES.get(at, {}).get("color", "#C98B2A"),
        "message": msg[:140],
        "is_read": bool(h.get("is_read", False)),
        "timestamp": _utc_to_brt(ts),
    }


class AlertasState(rx.State):
    # Data
    subscriptions: list[SubscriptionGroup] = []
    history: list[dict] = []
    subscription_counts: dict = {}  # {alert_type: n}

    # Form — add subscription
    new_alert_type: str = "daily"
    new_contract: str = ""
    new_email: str = ""

    # UI feedback
    is_loading: bool = True
    is_adding: bool = False
    form_message: str = ""
    form_is_error: bool = False

    # Per-alert-type sweep results {alert_type: str}
    sweep_results: dict = {}
    sweep_running: bool = False
    sweep_running_type: str = ""   # which alert_type is currently running

    # Confirmation dialog
    confirm_sweep_type: str = ""   # non-empty = dialog open
    confirm_sweep_label: str = ""  # PT-BR label shown in the dialog

    # History pagination
    history_page: int = 1
    history_total: int = 0
    history_per_page: int = 30

    # ── Explicit setters ──────────────────────────────────────────────────────

    def set_new_alert_type(self, val: str):
        self.new_alert_type = val

    def set_new_contract(self, val: str):
        self.new_contract = val

    def set_new_email(self, val: str):
        self.new_email = val

    # ── History pagination computed vars ──────────────────────────────────────

    @rx.var
    def history_total_pages(self) -> int:
        if self.history_total == 0:
            return 1
        return max(1, (self.history_total + self.history_per_page - 1) // self.history_per_page)

    @rx.var
    def history_has_prev(self) -> bool:
        return self.history_page > 1

    @rx.var
    def history_has_next(self) -> bool:
        return self.history_page < self.history_total_pages

    @rx.var
    def history_page_info(self) -> str:
        if self.history_total == 0:
            return "Nenhum disparo"
        start = (self.history_page - 1) * self.history_per_page + 1
        end = min(self.history_page * self.history_per_page, self.history_total)
        return f"{start}–{end} de {self.history_total}"

    def clear_type_sweep_result(self, alert_type: str):
        new_r = {**self.sweep_results}
        new_r.pop(alert_type, None)
        self.sweep_results = new_r

    # ── Confirmation dialog ───────────────────────────────────────────────────

    def open_confirm_sweep(self, alert_type: str):
        self.confirm_sweep_type = alert_type
        from bomtempo.core.alert_service import ALERT_TYPES as _AT
        self.confirm_sweep_label = _AT.get(alert_type, {}).get("label", alert_type)

    def cancel_confirm_sweep(self):
        self.confirm_sweep_type = ""
        self.confirm_sweep_label = ""

    # ── Load ─────────────────────────────────────────────────────────────────

    @rx.event(background=True)
    async def load_page(self):
        async with self:
            self.is_loading = True
            self.form_message = ""
            self.sweep_results = {}
            self.history_page = 1

        loop = asyncio.get_running_loop()
        try:
            raw = await loop.run_in_executor(None, AlertService.get_email_subscriptions)

            counts: dict = {k: 0 for k in ALERT_TYPES}
            for g in raw:
                at = g.get("alert_type", "")
                if at in counts:
                    counts[at] += len(g.get("email_chips", []))

            rows, total = await loop.run_in_executor(
                None, lambda: AlertService.get_history(page=1, per_page=30)
            )

            async with self:
                self.subscriptions = [_norm_group(g) for g in raw]
                self.subscription_counts = counts
                self.history = [_norm_hist(h) for h in rows]
                self.history_total = total
                self.is_loading = False

        except Exception as exc:
            logger.error(f"[AlertasState.load_page] {exc}")
            async with self:
                self.is_loading = False

    # ── History pagination ────────────────────────────────────────────────────

    @rx.event(background=True)
    async def history_prev(self):
        async with self:
            if self.history_page <= 1:
                return
            self.history_page -= 1
            page = self.history_page
        loop = asyncio.get_running_loop()
        rows, total = await loop.run_in_executor(
            None, lambda: AlertService.get_history(page=page, per_page=30)
        )
        async with self:
            self.history = [_norm_hist(h) for h in rows]
            self.history_total = total

    @rx.event(background=True)
    async def history_next(self):
        async with self:
            if self.history_page >= self.history_total_pages:
                return
            self.history_page += 1
            page = self.history_page
        loop = asyncio.get_running_loop()
        rows, total = await loop.run_in_executor(
            None, lambda: AlertService.get_history(page=page, per_page=30)
        )
        async with self:
            self.history = [_norm_hist(h) for h in rows]
            self.history_total = total

    # ── Add subscription (async background) ──────────────────────────────────

    @rx.event(background=True)
    async def add_subscription(self):
        async with self:
            self.is_adding = True
            self.form_message = ""
            self.form_is_error = False
            # Snapshot form values before releasing the lock
            alert_type = self.new_alert_type
            contract = self.new_contract.strip()
            email = self.new_email.strip()

        loop = asyncio.get_running_loop()
        ok, msg = await loop.run_in_executor(
            None,
            lambda: AlertService.add_email_subscription(
                alert_type=alert_type,
                contract=contract,
                email=email,
                created_by="admin",
            ),
        )

        if ok:
            audit_log(
                category=AuditCategory.ALERT_CONFIG,
                action=f"Assinatura de alerta '{alert_type}' adicionada — email '{email}' contrato '{contract}'",
                metadata={"alert_type": alert_type, "email": email, "contract": contract},
                status="success",
            )

        async with self:
            self.form_message = msg
            self.form_is_error = not ok
            if ok:
                self.new_email = ""
                raw = AlertService.get_email_subscriptions()
                self.subscriptions = [_norm_group(g) for g in raw]
                counts: dict = {k: 0 for k in ALERT_TYPES}
                for g in raw:
                    at = g.get("alert_type", "")
                    if at in counts:
                        counts[at] += len(g.get("email_chips", []))
                self.subscription_counts = counts
            self.is_adding = False

    # ── Delete email chip ─────────────────────────────────────────────────────

    def delete_email_chip(self, row_id: str):
        AlertService.delete_email_subscription(row_id)
        audit_log(
            category=AuditCategory.ALERT_CONFIG,
            action=f"Assinatura de alerta removida — id '{row_id}'",
            entity_type="alert_subscriptions",
            entity_id=row_id,
            status="success",
        )
        raw = AlertService.get_email_subscriptions()
        self.subscriptions = [_norm_group(g) for g in raw]
        counts: dict = {k: 0 for k in ALERT_TYPES}
        for g in raw:
            at = g.get("alert_type", "")
            if at in counts:
                counts[at] += len(g.get("email_chips", []))
        self.subscription_counts = counts

    # ── Manual sweep trigger ──────────────────────────────────────────────────

    @rx.event(background=True)
    async def confirm_and_sweep(self):
        """Called when user confirms the sweep dialog."""
        async with self:
            alert_type = self.confirm_sweep_type
            self.confirm_sweep_type = ""   # close dialog
            self.confirm_sweep_label = ""
            if not alert_type:
                return
            self.sweep_running = True
            self.sweep_running_type = alert_type
            new_r = {**self.sweep_results}
            new_r.pop(alert_type, None)
            self.sweep_results = new_r

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, lambda: AlertService.run_sweep(alert_type))

        async with self:
            sent = result.get("sent", 0)
            errors = result.get("errors", 0)
            skipped = result.get("skipped", 0)
            if errors:
                msg = f"{sent} enviados, {errors} com erro, {skipped} sem gatilho."
            elif sent == 0 and skipped > 0:
                msg = f"Nenhum contrato ativou o gatilho ({skipped} verificados)."
            elif sent == 0:
                msg = f"Nenhum destinatário cadastrado para este alerta."
            else:
                msg = f"{sent} email(s) enviado(s) com sucesso."

            self.sweep_results = {**self.sweep_results, alert_type: msg}
            audit_log(
                category=AuditCategory.ALERT_TRIGGER,
                action=f"Alerta '{alert_type}' disparado manualmente — {msg}",
                entity_type="alert_history",
                metadata={"alert_type": alert_type, "sent": sent, "errors": errors, "skipped": skipped},
                status="success" if not errors else "warning",
            )
            self.history_page = 1
            self.sweep_running = False
            self.sweep_running_type = ""

        # Reload history after releasing state lock
        rows, total = await loop.run_in_executor(
            None, lambda: AlertService.get_history(page=1, per_page=30)
        )
        async with self:
            self.history = [_norm_hist(h) for h in rows]
            self.history_total = total
