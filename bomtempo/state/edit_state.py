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
from bomtempo.core.supabase_client import sb_select, sb_upsert, sb_update, sb_insert, sb_delete
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

    # Dialog Variables para o Upload
    show_preview_dialog: bool = False
    preview_data: List[Dict[str, Any]] = []
    preview_stats: str = ""

    page: int = 1
    limit: int = 100
    toast_msg: str = ""
    
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

                yield rx.toast(
                    f"Tabela '{selected_tabela}' carregada. ({len(data)} registros)",
                    position="bottom-right",
                )

    async def on_cell_edited(self, pos: Tuple[int, int], new_value: Dict[str, Any]):
        try:
            col_idx, row_idx = pos
            if not self.raw_data or row_idx >= len(self.raw_data):
                return
            
            keys = list(self.raw_data[0].keys())
            if col_idx >= len(keys):
                return
                
            col_name = keys[col_idx]
            row_id = self.raw_data[row_idx].get("ID")
            
            # Extract string from GridCell dict
            val_str = str(new_value.get("data", ""))
            
            if row_id:
                # Otimista local com mutação explícita pontual
                new_data = [dict(row) for row in self.raw_data]
                new_data[row_idx][col_name] = val_str
                self.raw_data = new_data
                
                # Update no BD
                casted_val = EditState._cast_value(val_str)
                try:
                    sb_update(self.selected_tabela, {"ID": row_id}, {col_name: casted_val})
                    yield rx.toast(f"{col_name} atualizado!", position="bottom-right")
                except Exception as ex:
                    yield rx.toast(f"Erro BD: {str(ex)[:100]}", position="bottom-right", color_scheme="red")
                    # Force reload over optimistic cache to reflect true DB state
                    yield EditState.load_table
        except Exception as e:
            logger.error(f"Erro on_cell_edited: {e}")

    def on_cell_clicked(self, pos: Tuple[int, int]):
        """Rastreia a linha selecionada para habilitar o delete."""
        _col_idx, row_idx = pos
        self.selected_row_idx = row_idx

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
        try:
            new_row = {}
            if self.selected_contrato:
                new_row["Contrato"] = self.selected_contrato
            
            try:
                sb_insert(self.selected_tabela, new_row)
                yield rx.toast("Linha criada com sucesso!", position="bottom-right")
                yield EditState.load_table
            except Exception as ex:
                yield rx.toast(f"Erro BD ao criar: {str(ex)[:100]}", position="bottom-right", color_scheme="red")
        except Exception as e:
            logger.error(f"Erro add_row: {e}")

    def delete_row(self, row_idx: int):
        # A simple action since rx.data_editor doesn't have native multi-select delete easily accessible
        if 0 <= row_idx < len(self.raw_data):
            row_id = self.raw_data[row_idx].get("ID")
            if row_id:
                try:
                    sb_delete(self.selected_tabela, {"ID": row_id})
                    yield rx.toast(f"Registro deletado.", position="bottom-right")
                    yield EditState.load_table
                except Exception as ex:
                    yield rx.toast(f"Erro Delete: {str(ex)[:100]}", position="bottom-right", color_scheme="red")

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
            else:
                unknown_cols = set()

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
        self.raw_data = self.preview_data
        self.show_preview_dialog = False
        self.preview_data = []
        return rx.toast("Preview absorvido. Lembre-se de clicar em 'Gravar BD' para efetivar.", position="bottom-right")
        
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

        async with self:
            self.is_saving = False
            if result["errors"]:
                logger.error(f"PostgreSQL Rejection(s): {result['errors']}")
                # Mostra erros mas também reporta o que foi salvo
                saved = result["upserted"] + result["inserted"]
                err_summary = "\n".join(result["errors"][:5])  # máx 5 erros na tela
                yield rx.window_alert(
                    f"Salvo parcialmente: {saved} registro(s) gravado(s).\n\n"
                    f"ERROS ({len(result['errors'])}):\n{err_summary}\n\n"
                    "Ajuste os campos com conflito de tipo e tente gravar novamente."
                )
                # Recarrega mesmo assim para refletir o que foi salvo
                yield EditState.load_table
            else:
                yield rx.toast(
                    f"Sucesso: {result['upserted']} gravados (upsert), {result['inserted']} criados sem ID.",
                    position="bottom-right"
                )
                yield EditState.load_table
