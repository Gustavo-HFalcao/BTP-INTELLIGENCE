import asyncio
import re
import reflex as rx
import pandas as pd
import io
from typing import Dict, List, Any, Tuple

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)
from bomtempo.core.supabase_client import sb_select, sb_upsert, sb_insert, sb_delete
from bomtempo.core.logging_utils import get_logger

logger = get_logger(__name__)

class EditState(rx.State):
    projetos: List[str] = []
    contratos: List[str] = []
    tabelas: List[str] = ["contratos", "projetos", "obras", "financeiro", "om"]

    selected_projeto: str = ""
    selected_contrato: str = ""
    selected_tabela: str = "contratos"

    raw_data: List[Dict[str, Any]] = []

    # Loading / UX states
    is_loading_table: bool = False
    is_saving: bool = False
    selected_row_idx: int = -1

    # Unsaved changes tracking
    has_unsaved_changes: bool = False
    undo_count: int = 0

    # Dialog Variables para o Upload
    show_preview_dialog: bool = False
    preview_data: List[Dict[str, Any]] = []
    preview_stats: str = ""

    # ── Inline Cell Edit Modal (production workaround for GDG overlay bug) ────
    edit_modal_open: bool = False
    edit_modal_row: int = -1
    edit_modal_col: int = -1
    edit_modal_col_name: str = ""
    edit_modal_value: str = ""
    _last_click_time: float = 0.0
    _last_click_row: int = -1
    _last_click_col: int = -1

    page: int = 1
    limit: int = 100
    toast_msg: str = ""

    # ── Undo stack (raw Python instance var — bypasses Reflex's __setattr__).
    #
    #    Reflex rejects `self.foo = x` for any name not declared as a class-level
    #    state var. To store transient data without adding it to the serialized
    #    state (and sending large payloads over the WebSocket), we use
    #    object.__setattr__ / object.__getattribute__ which write directly to the
    #    underlying CPython instance dict, invisible to Reflex.
    # ────────────────────────────────────────────────────────────────────────

    def _undo_get_stack(self) -> list:
        """Return the raw undo stack, creating it if it doesn't exist yet."""
        try:
            return object.__getattribute__(self, "_undo_stack")
        except AttributeError:
            stack: list = []
            object.__setattr__(self, "_undo_stack", stack)
            return stack

    def _undo_push(self):
        """Save a snapshot of raw_data before a mutation (max 15 levels)."""
        stack = self._undo_get_stack()
        # undo_count=0 mas stack não-vazia → reset depois de save (stack stale).
        # Limpa antes de empurrar novo snapshot para evitar undo incorreto.
        if self.undo_count == 0 and stack:
            stack.clear()
        stack.append([dict(r) for r in self.raw_data])
        if len(stack) > 15:
            stack.pop(0)
        self.undo_count = len(stack)

    def _undo_reset(self):
        """Clear the undo stack.

        ONLY call from regular (sync/async) event handlers — NOT from inside
        `async with self:` blocks in background events. In those contexts `self`
        is a StateProxy and object.__setattr__ raises TypeError.
        Use _undo_reset_vars() + yield EditState._clear_undo_stack_sync instead.
        """
        object.__setattr__(self, "_undo_stack", [])
        self.undo_count = 0
        self.has_unsaved_changes = False

    def _undo_reset_vars(self):
        """Reset only the Reflex state vars (safe inside async with self: / StateProxy)."""
        self.undo_count = 0
        self.has_unsaved_changes = False

    def set_selected_projeto(self, val: str):
        self.selected_projeto = val
        self.selected_contrato = ""  # cascata

        if self.raw_data:
            # Filtro cascata a partir dos dados já carregados — sem round-trip ao BD
            rows = self.raw_data
            if val:
                rows = [r for r in rows if str(r.get("Projeto", "")) == val]
            if rows and "Contrato" in rows[0]:
                self.contratos = sorted(list(set(
                    str(r["Contrato"]) for r in rows if r.get("Contrato")
                )))
        else:
            # Pré-load: consulta BD para montar o dropdown
            yield EditState.load_contratos

    def set_selected_contrato(self, val: str):
        self.selected_contrato = val

    def set_selected_tabela(self, val: str):
        """Trocar tabela zera filtros e dados — cada tabela tem seu próprio schema."""
        self.selected_tabela = val
        self.selected_projeto = ""
        self.selected_contrato = ""
        self.raw_data = []
        self.selected_row_idx = -1
        self._undo_reset()

    def clear_filters(self):
        """Limpa filtros de projeto e contrato sem trocar de tabela."""
        self.selected_projeto = ""
        self.selected_contrato = ""
        
    @staticmethod
    def _cast_value(val_str: str) -> Any:
        # Tenta cast pra float/int
        if not isinstance(val_str, str):
            return val_str
        val = val_str.strip()
        if not val:
            return None

        try:
            if ',' in val:
                # Formato BR: "1.000,50" → pontos são separadores de milhar, vírgula é decimal
                clean_f = val.replace('.', '').replace(',', '.')
                return float(clean_f)
            elif '.' in val:
                return float(val)
            else:
                return int(val)
        except ValueError:
            return val
            
    @rx.var
    def editor_columns(self) -> List[Dict[str, str]]:
        if not self.raw_data:
            return [{"title": "id", "type": "str"}]
        keys = list(self.raw_data[0].keys())
        return [{"title": k, "type": "str"} for k in keys]
        
    @rx.var
    def editor_data(self) -> List[List[str]]:
        if not self.raw_data:
            return []
        keys = list(self.raw_data[0].keys())
        # Converter tudo para string para o rx.data_editor suportar nativamente
        return [[str(row.get(k) if row.get(k) is not None else "") for k in keys] for row in self.raw_data]

    async def load_projetos(self):
        try:
            # Projetos agora é carregado dos metadados ativos na tabela de mestre contratos
            res = sb_select("contratos", limit=500) or []
            self.projetos = sorted(list(set([str(r.get("Projeto", "")) for r in res if r.get("Projeto")])))
        except Exception as e:
            logger.error(f"Erro load_projetos: {e}")

    async def load_contratos(self):
        try:
            filters = {}
            if self.selected_projeto:
                filters["Projeto"] = self.selected_projeto
            res = sb_select("contratos", filters=filters, limit=500) or []
            self.contratos = sorted(list(set([str(r.get("Contrato", "")) for r in res if r.get("Contrato")])))
        except Exception as e:
            logger.error(f"Erro load_contratos: {e}")

    @rx.event(background=True)
    async def load_table(self):
        loop = asyncio.get_running_loop()

        async with self:
            self.is_loading_table = True
            selected_tabela = self.selected_tabela
            selected_contrato = self.selected_contrato
            selected_projeto = self.selected_projeto
            limit = self.limit

        result: Dict[str, Any] = {"data": [], "error": ""}

        def _fetch():
            try:
                # Descobre colunas reais da tabela antes de filtrar.
                # Evita HTTP 400 do PostgREST quando a coluna não existe
                # (ex: tabela "projetos" não tem coluna "Projeto").
                schema_sample = sb_select(selected_tabela, limit=1) or []
                existing_cols: set = set(schema_sample[0].keys()) if schema_sample else set()

                filters: Dict[str, Any] = {}
                if selected_contrato and "Contrato" in existing_cols:
                    filters["Contrato"] = selected_contrato
                if selected_projeto and "Projeto" in existing_cols:
                    filters["Projeto"] = selected_projeto

                result["data"] = sb_select(
                    selected_tabela, filters=filters, limit=limit, order="ID.desc"
                ) or []
            except Exception as e:
                result["error"] = str(e)

        await loop.run_in_executor(None, _fetch)

        async with self:
            self.is_loading_table = False
            if result["error"]:
                logger.error(f"Erro load_table: {result['error']}")
                yield rx.toast(f"Erro ao carregar tabela: {result['error']}", position="bottom-right")
            else:
                data = result["data"]
                self.raw_data = data
                self.selected_row_idx = -1

                # Repopula filtros dinamicamente a partir dos dados carregados.
                # Cada tabela pode ter colunas diferentes — os dropdowns refletem
                # os valores reais existentes nela, não a master table fixa.
                if data:
                    first = data[0]
                    if "Projeto" in first:
                        self.projetos = sorted(list(set(
                            str(r["Projeto"]) for r in data if r.get("Projeto")
                        )))
                    if "Contrato" in first:
                        self.contratos = sorted(list(set(
                            str(r["Contrato"]) for r in data if r.get("Contrato")
                        )))

                self._undo_reset_vars()
                yield rx.toast(
                    f"Tabela '{selected_tabela}' carregada. ({len(data)} registros)",
                    position="bottom-right",
                )

    def on_cell_edited(self, pos: Tuple[int, int], new_value: Dict[str, Any]):
        """Atualiza o grid localmente (sem I/O). Persistir via 'Salvar no Banco'.

        Manter este handler síncrono e sem chamadas de rede é CRÍTICO para que o
        GDG (Glide Data Grid) responda ao duplo-clique imediatamente — chamadas
        httpx bloqueantes congelavam o event loop em produção e impediam novas
        interações até a resposta do banco chegar.
        """
        try:
            col_idx, row_idx = pos
            if not self.raw_data or row_idx >= len(self.raw_data):
                return

            keys = list(self.raw_data[0].keys())
            if col_idx >= len(keys):
                return

            col_name = keys[col_idx]
            val_str = str(new_value.get("data", ""))

            # Push undo snapshot ANTES de mutar
            self._undo_push()

            new_data = [dict(row) for row in self.raw_data]
            new_data[row_idx][col_name] = val_str
            self.raw_data = new_data
            self.has_unsaved_changes = True

        except Exception as e:
            logger.error(f"Erro on_cell_edited: {e}")

    def on_cell_clicked(self, pos: Tuple[int, int]):
        """Click handler com detecção manual de duplo-clique.

        Single click: seleciona linha.
        Double click (<500ms, mesma célula): abre modal de edição.
        NÃO usa on_cell_activated para evitar o overlay fantasma do GDG.
        """
        import time
        col_idx, row_idx = pos
        self.selected_row_idx = row_idx

        now = time.time()
        is_double = (
            (now - self._last_click_time) < 0.8
            and self._last_click_row == row_idx
            and self._last_click_col == col_idx
        )
        self._last_click_time = now
        self._last_click_row = row_idx
        self._last_click_col = col_idx

        if is_double and self.raw_data and row_idx < len(self.raw_data):
            keys = list(self.raw_data[0].keys())
            if col_idx < len(keys):
                col_name = keys[col_idx]
                current_val = self.raw_data[row_idx].get(col_name)
                self.edit_modal_row = row_idx
                self.edit_modal_col = col_idx
                self.edit_modal_col_name = col_name
                self.edit_modal_value = str(current_val) if current_val is not None else ""
                self.edit_modal_open = True

    def on_cell_activated(self, pos: Tuple[int, int]):
        """Stub — mantém compatibilidade com frontend em cache.
        A edição real usa duplo-clique via on_cell_clicked.
        """
        pass

    def set_edit_modal_value(self, val: str):
        """Atualiza o valor no modal de edição inline."""
        self.edit_modal_value = val

    def cancel_edit_modal(self):
        """Fecha o modal sem salvar."""
        self.edit_modal_open = False
        self.edit_modal_row = -1
        self.edit_modal_col = -1
        self.edit_modal_col_name = ""
        self.edit_modal_value = ""

    def confirm_edit_modal(self):
        """Aplica a edição do modal no raw_data (mesma lógica de on_cell_edited)."""
        row_idx = self.edit_modal_row
        col_idx = self.edit_modal_col
        col_name = self.edit_modal_col_name
        val_str = self.edit_modal_value

        if row_idx < 0 or row_idx >= len(self.raw_data):
            self.cancel_edit_modal()
            return

        # Verifica se realmente mudou — evita undo fantasma
        old_val = str(self.raw_data[row_idx].get(col_name, ""))
        if val_str == old_val:
            self.cancel_edit_modal()
            return

        # Push undo snapshot ANTES de mutar
        self._undo_push()

        new_data = [dict(row) for row in self.raw_data]
        new_data[row_idx][col_name] = val_str
        self.raw_data = new_data
        self.has_unsaved_changes = True

        # Fecha modal
        self.edit_modal_open = False
        self.edit_modal_row = -1
        self.edit_modal_col = -1
        self.edit_modal_col_name = ""
        self.edit_modal_value = ""

        yield rx.toast(f"'{col_name}' atualizado.", position="bottom-right")

    def handle_edit_key_down(self, key: str):
        """Keyboard shortcuts no modal: Enter=salvar, Escape=cancelar."""
        if key == "Enter":
            # Inline a lógica de confirm_edit_modal (que é generator com yield)
            row_idx = self.edit_modal_row
            col_name = self.edit_modal_col_name
            val_str = self.edit_modal_value

            if row_idx < 0 or row_idx >= len(self.raw_data):
                self.cancel_edit_modal()
                return

            old_val = str(self.raw_data[row_idx].get(col_name, ""))
            if val_str == old_val:
                self.cancel_edit_modal()
                return

            self._undo_push()
            new_data = [dict(row) for row in self.raw_data]
            new_data[row_idx][col_name] = val_str
            self.raw_data = new_data
            self.has_unsaved_changes = True

            self.edit_modal_open = False
            self.edit_modal_row = -1
            self.edit_modal_col = -1
            self.edit_modal_col_name = ""
            self.edit_modal_value = ""

            yield rx.toast(f"'{col_name}' atualizado.", position="bottom-right")

        elif key == "Escape":
            self.cancel_edit_modal()

    def undo_last(self):
        """Desfaz a última edição de célula ou adição de linha."""
        stack = self._undo_get_stack()
        if not stack:
            yield rx.toast("Nada para desfazer.", position="bottom-right")
            return
        self.raw_data = stack.pop()
        self.undo_count = len(stack)
        # Stack vazia = revertido ao estado do último carregamento = sem pendências
        self.has_unsaved_changes = bool(stack)
        yield rx.toast("Ação desfeita.", position="bottom-right")

    def delete_selected_row(self):
        """Deleta a linha atualmente selecionada (clicada) no grid."""
        idx = self.selected_row_idx
        if idx < 0 or idx >= len(self.raw_data):
            yield rx.toast("Clique em uma célula para selecionar a linha antes de deletar.", position="top-right")
            return
        row_id = self.raw_data[idx].get("ID")
        label = self.raw_data[idx].get("Projeto") or self.raw_data[idx].get("Contrato") or f"linha {idx + 1}"
        if row_id:
            try:
                sb_delete(self.selected_tabela, {"ID": row_id})
                new_data = [r for i, r in enumerate(self.raw_data) if i != idx]
                self.raw_data = new_data
                self.selected_row_idx = -1
                yield rx.toast(f"'{label}' deletado.", position="bottom-right")
            except Exception as ex:
                yield rx.toast(f"Erro ao deletar: {str(ex)[:100]}", position="bottom-right")
        else:
            # Linha local sem ID — apenas remove do grid (nunca foi salva no banco)
            new_data = [r for i, r in enumerate(self.raw_data) if i != idx]
            self.raw_data = new_data
            self.selected_row_idx = -1
            yield rx.toast("Linha removida do grid (não estava no banco).", position="bottom-right")

    def add_row(self):
        """Adiciona linha em branco ao grid localmente. Persiste via 'Salvar no Banco'."""
        try:
            if not self.selected_tabela:
                yield rx.toast("Selecione uma tabela antes de adicionar linhas.", position="top-right")
                return

            if not self.raw_data:
                # Sem schema local: avisa o usuário para carregar primeiro
                yield rx.toast(
                    "Carregue a tabela antes de adicionar linhas — o schema de colunas é necessário.",
                    position="top-right",
                    duration=5000,
                )
                return

            self._undo_push()
            # Espelha as colunas do primeiro registro com valores None
            new_row: Dict[str, Any] = {key: None for key in self.raw_data[0].keys()}
            if self.selected_contrato:
                new_row["Contrato"] = self.selected_contrato

            # Linha nova no topo — mais fácil de localizar e preencher
            self.raw_data = [new_row] + list(self.raw_data)
            self.has_unsaved_changes = True
            yield rx.toast("Linha adicionada. Preencha e clique em Salvar no Banco.", position="bottom-right")
        except Exception as e:
            logger.error(f"Erro add_row: {e}")

    def download_excel(self):
        if not self.raw_data:
            return rx.toast("Não há dados para exportar.", position="bottom-right")
        try:
            df = pd.DataFrame(self.raw_data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name=self.selected_tabela.capitalize())
            output.seek(0)
            excel_data = output.read()
            return rx.download(data=excel_data, filename=f"{self.selected_tabela}_{self.selected_projeto}.xlsx")
        except Exception as e:
            logger.error(f"Erro ao gerar Excel: {e}")
            return rx.toast(f"Erro na exportação: {e}", position="bottom-right")

    async def handle_csv_upload(self, files: list[rx.UploadFile]):
        """Lê o arquivo, valida schema e joga na tela para PREVIEW (não salva no banco)."""
        if not files:
            return

        # Trava 1: tabela destino obrigatória
        if not self.selected_tabela:
            yield rx.toast("Selecione a Tabela Alvo antes de fazer upload.", position="top-right")
            return

        file = files[0]
        try:
            content = await file.read()
            bytes_io = io.BytesIO(content)
            filename = file.filename.lower()

            if filename.endswith('.xlsx'):
                df = pd.read_excel(bytes_io, dtype=str)
            else:
                try:
                    df = pd.read_csv(bytes_io, sep=';', dtype=str)
                    if len(df.columns) <= 1:
                        bytes_io.seek(0)
                        df = pd.read_csv(bytes_io, sep=None, engine='python', dtype=str)
                except Exception:
                    bytes_io.seek(0)
                    df = pd.read_csv(bytes_io, sep=None, engine='python', dtype=str)

            upload_cols = set(df.columns.tolist())

            # Trava 2: schema guard — busca colunas reais da tabela destino
            db_schema = sb_select(self.selected_tabela, limit=1) or []
            db_cols = set(db_schema[0].keys()) if db_schema else set()

            if db_cols:
                known_cols = upload_cols & db_cols
                unknown_cols = upload_cols - db_cols

                # Rejeita se nenhuma coluna do arquivo bate com a tabela — arquivo errado
                if len(known_cols) == 0:
                    yield rx.toast(
                        f"Arquivo incompatível com '{self.selected_tabela}': nenhuma coluna reconhecida. "
                        "Verifique se baixou a tabela correta.",
                        position="top-right",
                        duration=6000,
                    )
                    return

                # Rejeita se menos de 30% das colunas do banco estão no arquivo
                match_ratio = len(known_cols) / len(db_cols) if db_cols else 1.0
                if match_ratio < 0.3:
                    yield rx.toast(
                        f"Arquivo suspeito: apenas {len(known_cols)}/{len(db_cols)} colunas "
                        f"reconhecidas ({match_ratio:.0%}). Verifique se é a planilha correta.",
                        position="top-right",
                        duration=6000,
                    )
                    return
            else:
                unknown_cols = set()

            # Trava: rejeita arquivo vazio (só cabeçalho, sem dados)
            if df.empty or len(df) == 0:
                yield rx.toast(
                    "Arquivo vazio — contém apenas cabeçalho, sem linhas de dados.",
                    position="top-right",
                    duration=5000,
                )
                return

            # Limpa registros
            records = df.to_dict('records')
            clean_records = []
            for rec in records:
                clean_rec = {}
                for k, v in rec.items():
                    if pd.isna(v) or str(v).strip().lower() in ["nan", "none", "nat", "<na>", ""]:
                        clean_rec[k] = None
                    else:
                        clean_rec[k] = EditState._cast_value(str(v))
                clean_records.append(clean_rec)

            # Trava 3 (aviso): IDs duplicados dentro do próprio arquivo
            ids = [str(r.get("ID")) for r in clean_records if r.get("ID")]
            dup_count = len(ids) - len(set(ids))

            # Monta stats enriquecido para o dialog de preview
            stats_lines = [
                f"Arquivo: {file.filename}",
                f"Linhas prontas: {len(clean_records)}",
                f"Colunas reconhecidas: {len(known_cols) if db_cols else len(upload_cols)}",
            ]
            if unknown_cols:
                stats_lines.append(f"Colunas ignoradas ({len(unknown_cols)}): {', '.join(sorted(unknown_cols))}")
            if dup_count > 0:
                stats_lines.append(f"⚠️  {dup_count} ID(s) duplicado(s) no arquivo — o último valor sobrescreve os anteriores.")

            self.preview_data = clean_records
            self.preview_stats = "\n".join(stats_lines)
            self.show_preview_dialog = True

        except Exception as e:
            logger.error(f"Erro CSV upload: {e}")
            yield rx.toast(f"Erro ao ler arquivo: {e}", position="top-right")

    def confirm_preview_upload(self):
        self._undo_reset()
        self.raw_data = self.preview_data
        self.show_preview_dialog = False
        self.has_unsaved_changes = True

        # Repopula filtros de Projeto/Contrato a partir dos dados do arquivo
        # (equivalente ao que load_table faz após um carregamento do BD)
        data = self.preview_data
        self.preview_data = []
        if data:
            first = data[0]
            if "Projeto" in first:
                self.projetos = sorted(list(set(
                    str(r["Projeto"]) for r in data if r.get("Projeto")
                )))
            if "Contrato" in first:
                self.contratos = sorted(list(set(
                    str(r["Contrato"]) for r in data if r.get("Contrato")
                )))

        return rx.toast("Arquivo absorvido no grid. Clique em 'Salvar no Banco' para efetivar.", position="bottom-right")
        
    def cancel_preview_upload(self):
        self.show_preview_dialog = False
        self.preview_data = []

    @rx.event(background=True)
    async def commit_csv_upload(self):
        """Salva a visualização atual. Opera como UPSERT (Update via ID, Insert para novos).

        Usa background=True + run_in_executor para não bloquear o event loop com
        as chamadas httpx síncronas de sb_update/sb_insert — garantindo que os
        rx.toast / rx.window_alert cheguem ao browser.
        """
        loop = asyncio.get_running_loop()

        async with self:
            if not self.raw_data:
                yield rx.toast("Nenhum dado no grid para salvar.", position="bottom-right")
                return
            raw_data = list(self.raw_data)
            selected_tabela = self.selected_tabela
            self.is_saving = True

        result: Dict[str, Any] = {"upserted": 0, "inserted": 0, "errors": []}

        # Descobre colunas válidas da tabela uma única vez (evita rejeição por coluna inexistente)
        def _get_valid_columns() -> set:
            try:
                sample = sb_select(selected_tabela, limit=1) or []
                return set(sample[0].keys()) if sample else set()
            except Exception:
                return set()

        def _do_upsert():
            valid_cols = _get_valid_columns()

            for rec in raw_data:
                row_id = rec.get("ID")
                label = rec.get('Projeto') or rec.get('Contrato') or str(row_id or '?')

                # Filtra colunas que não existem na tabela (evita 400 por schema mismatch)
                if valid_cols:
                    rec = {k: v for k, v in rec.items() if k in valid_cols}

                try:
                    # Só vai para upsert se o ID for um UUID válido
                    # Placeholders como "NOVO", "1", "linha X" → insert puro (banco gera UUID)
                    if row_id and _UUID_RE.match(str(row_id).strip()):
                        sb_upsert(selected_tabela, rec, on_conflict="ID")
                        result["upserted"] += 1
                    else:
                        # Sem ID ou ID inválido: insert puro, banco gera UUID
                        clean_rec = {k: v for k, v in rec.items() if k != "ID"}
                        sb_insert(selected_tabela, clean_rec)
                        result["inserted"] += 1
                except Exception as ex:
                    result["errors"].append(f"Linha '{label}': {str(ex)[:120]}")

        try:
            await loop.run_in_executor(None, _do_upsert)
        except Exception as e:
            logger.error(f"Erro crítico no executor: {e}")
            async with self:
                yield rx.toast(f"Erro crítico no salvamento: {e}", position="top-right")
            return

        # ── Prepara refresh do GlobalState ANTES de adquirir o lock ──────────
        # Faz todo o I/O pesado FORA do state lock para não bloquear
        fresh_data = None
        needs_global_refresh = selected_tabela in ("contratos", "projetos", "obras", "financeiro", "om")
        if needs_global_refresh:
            try:
                import os
                from bomtempo.core.data_loader import CACHE_FILE
                if os.path.exists(CACHE_FILE):
                    os.remove(CACHE_FILE)
                    logger.info("🗑️ Cache invalidado após commit no editor")

                from bomtempo.core.data_loader import DataLoader
                fresh_data = await loop.run_in_executor(None, DataLoader().load_all)
                logger.info("📦 Dados frescos carregados para refresh")
            except Exception as e:
                logger.warning(f"⚠️ Falha ao carregar dados frescos: {e}")
                fresh_data = None

        # ── UMA ÚNICA transição de estado por lock — evita deadlocks ─────────
        events = []
        
        # 1. Limpa o EditState local
        async with self:
            self.is_saving = False
            if result["errors"]:
                logger.error(f"PostgreSQL Rejection(s): {result['errors']}")
                saved = result["upserted"] + result["inserted"]
                err_summary = "\n".join(result["errors"][:5])
                events.append(rx.window_alert(
                    f"Salvo parcialmente: {saved} registro(s) gravado(s).\n\n"
                    f"ERROS ({len(result['errors'])}):\n{err_summary}\n\n"
                    "Ajuste os campos com conflito de tipo e tente gravar novamente."
                ))
            else:
                self.has_unsaved_changes = False
                self.undo_count = 0
                events.append(rx.toast(
                    f"Salvo: {result['upserted']} atualizados, {result['inserted']} criados.",
                    position="bottom-right"
                ))
            
            events.append(EditState.load_table)

            # 2. Aplica dados frescos no GlobalState (NO MESMO LOCK PROXY)
            if fresh_data is not None:
                try:
                    from bomtempo.state.global_state import GlobalState
                    gs = await self.get_state(GlobalState)
                    gs._data = fresh_data
                    gs.contratos_list = []
                    gs.projetos_list = []
                    gs.obras_list = []
                    gs.financeiro_list = []
                    gs.om_list = []
                    for table_key, attr_name in [
                        ("contratos", "contratos_list"),
                        ("projeto", "projetos_list"),
                        ("obras", "obras_list"),
                        ("financeiro", "financeiro_list"),
                        ("om", "om_list"),
                    ]:
                        if table_key in fresh_data:
                            df = fresh_data[table_key]
                            if hasattr(df, 'empty') and not df.empty:
                                import pandas as _pd
                                for col in df.columns:
                                    if _pd.api.types.is_datetime64_any_dtype(df[col]):
                                        df[col] = df[col].astype(str)
                                for col in df.columns:
                                    if _pd.api.types.is_numeric_dtype(df[col]):
                                        df[col] = df[col].fillna(0)
                                    else:
                                        df[col] = df[col].fillna("")
                                setattr(gs, attr_name, df.to_dict("records"))

                    if "contratos" in fresh_data:
                        df = fresh_data["contratos"]
                        if hasattr(df, 'empty') and not df.empty:
                            gs.total_contratos = len(df)
                            gs.valor_tcv = (
                                float(df["valor_contratado"].sum())
                                if "valor_contratado" in df.columns
                                else 0.0
                            )
                            gs.contratos_ativos = (
                                len(df[df["status"] == "Em Execução"]) if "status" in df.columns else 0
                            )

                    gs.is_loading = False
                    logger.info("✅ GlobalState re-sincronizado após commit no editor")
                except Exception as e:
                    logger.warning(f"⚠️ Falha ao re-sincronizar GlobalState: {e}")

        # 3. Dispara os eventos de UI para o frontend em sequência
        for event in events:
            yield event


