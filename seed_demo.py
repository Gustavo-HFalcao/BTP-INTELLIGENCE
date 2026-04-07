"""
seed_demo.py — Operação Seed State-of-the-Art
Usina Solar 120 kWp — Galpão Industrial Ferreira & Cia
Contrato: CONTRATO N° 306/2026
client_id: 11111111-1111-1111-1111-111111111111

Executa:
  python seed_demo.py
  python seed_demo.py --clean-only   (só limpa, não re-insere)
  python seed_demo.py --skip-clean   (insere sem limpar)

Estratégia:
  1. Limpa FK-safe
  2. Seed hub_atividades (macro/micro/sub, conclusao_pct 0 na entrada)
  3. Simula 7 dias de RDO (equipe, clima, atividades, fotos) → atualiza conclusao_pct via lógica real
  4. hub_atividade_historico gerado a partir dos RDOs (um record por atividade por dia)
  5. fin_custos com datas distribuídas (S-curve financeira)
  6. hub_timeline (eventos, falha, documento, reunião, interferência)
  7. hub_auditoria_imgs (galeria de campo com URLs públicas)
  8. Update contratos: equipe_presente_hoje, chuva_acumulada_mm
"""

import os
import sys
import uuid
from datetime import datetime, date, timedelta, timezone

# ── Load env ─────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌  SUPABASE_URL / SUPABASE_KEY não encontrados no ambiente.")
    sys.exit(1)

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Constants ─────────────────────────────────────────────────────────────────
CLIENT_ID   = "11111111-1111-1111-1111-111111111111"
CONTRATO    = "CONTRATO N° 306/2026"
PROJETO     = "Usina Solar 120 kWp — Galpão Industrial Ferreira & Cia"
CLIENTE     = "Ferreira & Cia Ind. e Com. Ltda"
LOC         = "Av. das Indústrias, 1420, Distrito Industrial, Fortaleza / CE"
LAT_OBRA    = -3.8137
LNG_OBRA    = -38.5133
INICIO      = date(2026, 4, 1)
BRT         = timezone(timedelta(hours=-3))

# ── Image URLs públicas (Unsplash / Picsum) ──────────────────────────────────
# Usadas em hub_auditoria_imgs + rdo evidências (sem necessidade de upload)
IMGS = {
    "equipe": [
        "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=800",
        "https://images.unsplash.com/photo-1621905251189-08b45d6a269e?w=800",
        "https://images.unsplash.com/photo-1581094271901-8022df4466f9?w=800",
        "https://images.unsplash.com/photo-1590650153855-d9e808231d41?w=800",
    ],
    "ferramentas": [
        "https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?w=800",
        "https://images.unsplash.com/photo-1504148455328-c376907d081c?w=800",
        "https://images.unsplash.com/photo-1530124566582-a618bc2615dc?w=800",
    ],
    "falhas": [
        "https://images.unsplash.com/photo-1575505586569-646b2ca898fc?w=800",
        "https://images.unsplash.com/photo-1612358405970-e96e8b1b7348?w=800",
    ],
    "gerais": [
        "https://images.unsplash.com/photo-1509391366360-2e959784a276?w=800",
        "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800",
        "https://images.unsplash.com/photo-1497440001374-f26997328c1b?w=800",
        "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=800",
        "https://images.unsplash.com/photo-1592833159057-a5a5b9c8c4ab?w=800",
    ],
}

# ── Helper ────────────────────────────────────────────────────────────────────
def _brt_ts(d: date, hour: int = 7, minute: int = 30) -> str:
    """ISO timestamp em BRT para um dia."""
    dt = datetime(d.year, d.month, d.day, hour, minute, 0, tzinfo=BRT)
    return dt.isoformat()

def _ins(table: str, data: dict):
    try:
        sb.table(table).insert(data).execute()
    except Exception as e:
        print(f"  ⚠️  INSERT {table}: {e}")

def _upd(table: str, filters: dict, data: dict):
    try:
        q = sb.table(table).update(data)
        for k, v in filters.items():
            q = q.eq(k, v)
        q.execute()
    except Exception as e:
        print(f"  ⚠️  UPDATE {table}: {e}")

def _del(table: str, filters: dict):
    try:
        q = sb.table(table).delete()
        for k, v in filters.items():
            q = q.eq(k, v)
        q.execute()
    except Exception as e:
        print(f"  ⚠️  DELETE {table}: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# 1. LIMPEZA
# ═══════════════════════════════════════════════════════════════════════════════
def clean():
    print("\n🧹  Limpando dados existentes...")
    # FK-safe order
    for t in [
        "hub_atividade_historico",
        "hub_cronograma_log",
        "rdo_atividades",
        "hub_atividades",
        "rdo_master",
        "fin_custos",
        "hub_timeline",
        "hub_auditoria_imgs",
    ]:
        _del(t, {"contrato": CONTRATO})
        print(f"  ✓ {t}")
    # Limpa hub_intelligence também
    _del("hub_intelligence", {"contrato": CONTRATO})
    print("  ✓ hub_intelligence")
    print("✅  Limpeza concluída.")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. ATIVIDADES — Hierarquia Macro / Micro / Sub
# ═══════════════════════════════════════════════════════════════════════════════

# IDs fixos para referência cruzada
A = {
    # ── Macro 1 — Estrutura Metálica ──────────────────────────────────────────
    "M1":     "aa000001-0000-0000-0000-000000000001",
    "M1_1":   "aa000001-0000-0000-0000-000000000002",   # Micro Fundação
    "M1_1_1": "aa000001-0000-0000-0000-000000000003",   # Sub Perfuração
    "M1_1_2": "aa000001-0000-0000-0000-000000000004",   # Sub Resina
    "M1_2":   "aa000001-0000-0000-0000-000000000005",   # Micro Calhas
    "M1_3":   "aa000001-0000-0000-0000-000000000006",   # Micro Nivelamento
    # ── Macro 2 — Módulos & Elétrica CC ──────────────────────────────────────
    "M2":     "aa000002-0000-0000-0000-000000000001",
    "M2_1":   "aa000002-0000-0000-0000-000000000002",   # Micro Módulos FV
    "M2_1_1": "aa000002-0000-0000-0000-000000000003",   # Sub Descarregamento
    "M2_1_2": "aa000002-0000-0000-0000-000000000004",   # Sub Fixação Trilhos
    "M2_1_3": "aa000002-0000-0000-0000-000000000005",   # Sub Cabeamento CC
    "M2_2":   "aa000002-0000-0000-0000-000000000006",   # Micro String Box
    "M2_3":   "aa000002-0000-0000-0000-000000000007",   # Micro Aterramento
    # ── Macro 3 — Elétrica CA & Comissionamento ──────────────────────────────
    "M3":     "aa000003-0000-0000-0000-000000000001",
    "M3_1":   "aa000003-0000-0000-0000-000000000002",
    "M3_2":   "aa000003-0000-0000-0000-000000000003",
    "M3_3":   "aa000003-0000-0000-0000-000000000004",
}

def seed_atividades():
    """Insere hierarquia completa. Conclusao_pct começa em 0 — RDOs vão atualizar."""
    print("\n🏗️   Seedando hub_atividades (17 registros)...")

    base = dict(contrato=CONTRATO, client_id=CLIENT_ID, critico=False,
                pendente_aprovacao=False, created_by="seed")

    rows = [
        # ── MACRO 1 ───────────────────────────────────────────────────────────
        {**base, "id": A["M1"], "nivel": "macro", "fase_macro": "Estrutura Metálica",
         "fase": "Estrutura Metálica", "atividade": "Estrutura Metálica",
         "responsavel": "Carlos Menezes",
         "inicio_previsto": "2026-04-01", "termino_previsto": "2026-04-05",
         "conclusao_pct": 0, "peso_pct": 35, "status_atividade": "nao_iniciada",
         "total_qty": 0, "exec_qty": 0, "unidade": "conjunto", "dias_planejados": 5},

        {**base, "id": A["M1_1"], "nivel": "micro", "parent_id": A["M1"],
         "fase_macro": "Estrutura Metálica", "fase": "Fundação",
         "atividade": "Fundação e Ancoragem",
         "responsavel": "Carlos Menezes",
         "inicio_previsto": "2026-04-01", "termino_previsto": "2026-04-02",
         "conclusao_pct": 0, "peso_pct": 40, "status_atividade": "nao_iniciada",
         "total_qty": 48, "exec_qty": 0, "unidade": "âncoras", "dias_planejados": 2},

        {**base, "id": A["M1_1_1"], "nivel": "sub", "parent_id": A["M1_1"],
         "fase_macro": "Estrutura Metálica", "fase": "Fundação",
         "atividade": "Perfuração das estruturas de concreto",
         "responsavel": "Carlos Menezes",
         "inicio_previsto": "2026-04-01", "termino_previsto": "2026-04-01",
         "conclusao_pct": 0, "peso_pct": 50, "status_atividade": "nao_iniciada",
         "total_qty": 48, "exec_qty": 0, "unidade": "furos", "dias_planejados": 1},

        {**base, "id": A["M1_1_2"], "nivel": "sub", "parent_id": A["M1_1"],
         "fase_macro": "Estrutura Metálica", "fase": "Fundação",
         "atividade": "Injeção de resina epóxi e fixação",
         "responsavel": "Carlos Menezes",
         "inicio_previsto": "2026-04-02", "termino_previsto": "2026-04-02",
         "conclusao_pct": 0, "peso_pct": 50, "status_atividade": "nao_iniciada",
         "total_qty": 48, "exec_qty": 0, "unidade": "âncoras", "dias_planejados": 1},

        {**base, "id": A["M1_2"], "nivel": "micro", "parent_id": A["M1"],
         "fase_macro": "Estrutura Metálica", "fase": "Calhas e Trilhos",
         "atividade": "Montagem das Calhas e Trilhos",
         "responsavel": "Carlos Menezes",
         "inicio_previsto": "2026-04-03", "termino_previsto": "2026-04-04",
         "conclusao_pct": 0, "peso_pct": 40, "status_atividade": "nao_iniciada",
         "total_qty": 240, "exec_qty": 0, "unidade": "metros", "dias_planejados": 2},

        {**base, "id": A["M1_3"], "nivel": "micro", "parent_id": A["M1"],
         "fase_macro": "Estrutura Metálica", "fase": "Inspeção",
         "atividade": "Nivelamento e Inspeção Final",
         "responsavel": "Carlos Menezes",
         "inicio_previsto": "2026-04-05", "termino_previsto": "2026-04-05",
         "conclusao_pct": 0, "peso_pct": 20, "status_atividade": "nao_iniciada",
         "total_qty": 1, "exec_qty": 0, "unidade": "conjunto", "dias_planejados": 1},

        # ── MACRO 2 ───────────────────────────────────────────────────────────
        {**base, "id": A["M2"], "nivel": "macro", "fase_macro": "Módulos & Elétrica CC",
         "fase": "Módulos & Elétrica CC", "atividade": "Módulos & Elétrica CC",
         "responsavel": "Ricardo Sousa",
         "inicio_previsto": "2026-04-04", "termino_previsto": "2026-04-10",
         "conclusao_pct": 0, "peso_pct": 40, "status_atividade": "nao_iniciada",
         "total_qty": 0, "exec_qty": 0, "unidade": "conjunto", "dias_planejados": 7, "critico": True},

        {**base, "id": A["M2_1"], "nivel": "micro", "parent_id": A["M2"],
         "fase_macro": "Módulos & Elétrica CC", "fase": "Módulos FV",
         "atividade": "Instalação dos Módulos FV",
         "responsavel": "Ricardo Sousa",
         "inicio_previsto": "2026-04-04", "termino_previsto": "2026-04-09",
         "conclusao_pct": 0, "peso_pct": 50, "status_atividade": "nao_iniciada",
         "total_qty": 300, "exec_qty": 0, "unidade": "módulos", "dias_planejados": 6, "critico": True},

        {**base, "id": A["M2_1_1"], "nivel": "sub", "parent_id": A["M2_1"],
         "fase_macro": "Módulos & Elétrica CC", "fase": "Módulos FV",
         "atividade": "Descarregamento e conferência de módulos",
         "responsavel": "Ricardo Sousa",
         "inicio_previsto": "2026-04-04", "termino_previsto": "2026-04-04",
         "conclusao_pct": 0, "peso_pct": 15, "status_atividade": "nao_iniciada",
         "total_qty": 300, "exec_qty": 0, "unidade": "módulos", "dias_planejados": 1},

        {**base, "id": A["M2_1_2"], "nivel": "sub", "parent_id": A["M2_1"],
         "fase_macro": "Módulos & Elétrica CC", "fase": "Módulos FV",
         "atividade": "Fixação dos módulos nos trilhos",
         "responsavel": "Ricardo Sousa",
         "inicio_previsto": "2026-04-05", "termino_previsto": "2026-04-09",
         "conclusao_pct": 0, "peso_pct": 55, "status_atividade": "nao_iniciada",
         "total_qty": 300, "exec_qty": 0, "unidade": "módulos", "dias_planejados": 5, "critico": True},

        {**base, "id": A["M2_1_3"], "nivel": "sub", "parent_id": A["M2_1"],
         "fase_macro": "Módulos & Elétrica CC", "fase": "Módulos FV",
         "atividade": "Cabeamento CC entre módulos",
         "responsavel": "Ricardo Sousa",
         "inicio_previsto": "2026-04-06", "termino_previsto": "2026-04-09",
         "conclusao_pct": 0, "peso_pct": 30, "status_atividade": "nao_iniciada",
         "total_qty": 600, "exec_qty": 0, "unidade": "metros", "dias_planejados": 4},

        {**base, "id": A["M2_2"], "nivel": "micro", "parent_id": A["M2"],
         "fase_macro": "Módulos & Elétrica CC", "fase": "Elétrica CC",
         "atividade": "String Box e Inversores",
         "responsavel": "Ricardo Sousa",
         "inicio_previsto": "2026-04-09", "termino_previsto": "2026-04-10",
         "conclusao_pct": 0, "peso_pct": 30, "status_atividade": "nao_iniciada",
         "total_qty": 4, "exec_qty": 0, "unidade": "inversores", "dias_planejados": 2},

        {**base, "id": A["M2_3"], "nivel": "micro", "parent_id": A["M2"],
         "fase_macro": "Módulos & Elétrica CC", "fase": "Elétrica CC",
         "atividade": "Aterramento e SPDA",
         "responsavel": "Ricardo Sousa",
         "inicio_previsto": "2026-04-10", "termino_previsto": "2026-04-10",
         "conclusao_pct": 0, "peso_pct": 20, "status_atividade": "nao_iniciada",
         "total_qty": 1, "exec_qty": 0, "unidade": "conjunto", "dias_planejados": 1},

        # ── MACRO 3 ───────────────────────────────────────────────────────────
        {**base, "id": A["M3"], "nivel": "macro", "fase_macro": "Elétrica CA & Comissionamento",
         "fase": "Elétrica CA & Comissionamento", "atividade": "Elétrica CA & Comissionamento",
         "responsavel": "Felipe Araújo",
         "inicio_previsto": "2026-04-09", "termino_previsto": "2026-04-14",
         "conclusao_pct": 0, "peso_pct": 25, "status_atividade": "nao_iniciada",
         "total_qty": 0, "exec_qty": 0, "unidade": "conjunto", "dias_planejados": 6},

        {**base, "id": A["M3_1"], "nivel": "micro", "parent_id": A["M3"],
         "fase_macro": "Elétrica CA & Comissionamento", "fase": "Quadro CA",
         "atividade": "Quadro de Distribuição CA",
         "responsavel": "Felipe Araújo",
         "inicio_previsto": "2026-04-09", "termino_previsto": "2026-04-10",
         "conclusao_pct": 0, "peso_pct": 30, "status_atividade": "nao_iniciada",
         "total_qty": 1, "exec_qty": 0, "unidade": "quadro", "dias_planejados": 2},

        {**base, "id": A["M3_2"], "nivel": "micro", "parent_id": A["M3"],
         "fase_macro": "Elétrica CA & Comissionamento", "fase": "Cabeamento CA",
         "atividade": "Cabeamento CA e Rede",
         "responsavel": "Felipe Araújo",
         "inicio_previsto": "2026-04-11", "termino_previsto": "2026-04-12",
         "conclusao_pct": 0, "peso_pct": 35, "status_atividade": "nao_iniciada",
         "total_qty": 180, "exec_qty": 0, "unidade": "metros", "dias_planejados": 2},

        {**base, "id": A["M3_3"], "nivel": "micro", "parent_id": A["M3"],
         "fase_macro": "Elétrica CA & Comissionamento", "fase": "Comissionamento",
         "atividade": "Comissionamento e Testes",
         "responsavel": "Felipe Araújo",
         "inicio_previsto": "2026-04-13", "termino_previsto": "2026-04-14",
         "conclusao_pct": 0, "peso_pct": 35, "status_atividade": "nao_iniciada",
         "total_qty": 1, "exec_qty": 0, "unidade": "conjunto", "dias_planejados": 2, "critico": True},
    ]

    for r in rows:
        _ins("hub_atividades", r)

    print(f"  ✓ {len(rows)} atividades inseridas (todas a 0% — RDOs irão atualizar)")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. SIMULAÇÃO DE RDOs DIA A DIA
# ═══════════════════════════════════════════════════════════════════════════════

# Estado de progresso acumulado por atividade {id: (exec_qty, conclusao_pct)}
_STATE: dict = {}

def _get_pct(act_id: str) -> int:
    return _STATE.get(act_id, (0, 0))[1]

def _get_exec(act_id: str) -> float:
    return _STATE.get(act_id, (0, 0))[0]

def _calc_pct(exec_qty: float, total_qty: float) -> int:
    if total_qty <= 0:
        return 0
    return min(100, int(exec_qty / total_qty * 100))

def _update_activity(act_id: str, prod_dia: float, total_qty: float, ts_iso: str, rdo_id_str: str):
    """Atualiza estado local + persiste no Supabase."""
    old_exec = _get_exec(act_id)
    old_pct  = _get_pct(act_id)
    new_exec = old_exec + prod_dia
    new_pct  = _calc_pct(new_exec, total_qty)

    _STATE[act_id] = (new_exec, new_pct)

    # hub_atividades
    status = "concluida" if new_pct >= 100 else ("em_execucao" if new_pct > 0 else "nao_iniciada")
    _upd("hub_atividades", {"id": act_id}, {
        "conclusao_pct": new_pct,
        "exec_qty": new_exec,
        "status_atividade": status,
    })

    # hub_atividade_historico
    _ins("hub_atividade_historico", {
        "atividade_id":          act_id,
        "contrato":              CONTRATO,
        "rdo_id":                rdo_id_str,
        "conclusao_pct_anterior": old_pct,
        "conclusao_pct_novo":    new_pct,
        "producao_dia":          prod_dia,
        "exec_qty_novo":         new_exec,
        "total_qty":             total_qty,
        "created_at":            ts_iso,
        "client_id":             CLIENT_ID,
    })

def _recalc_macro(macro_id: str):
    """Recalcula conclusao_pct do macro a partir dos filhos."""
    try:
        res = sb.table("hub_atividades").select("id,conclusao_pct,peso_pct").eq("parent_id", macro_id).execute()
        children = res.data or []
        if not children:
            return
        total_peso = sum(float(c.get("peso_pct") or 1) for c in children)
        if total_peso <= 0:
            return
        avg = sum(float(c.get("conclusao_pct") or 0) * float(c.get("peso_pct") or 1) for c in children) / total_peso
        new_pct = min(100, int(round(avg)))
        status = "concluida" if new_pct >= 100 else ("em_execucao" if new_pct > 0 else "nao_iniciada")
        _upd("hub_atividades", {"id": macro_id}, {"conclusao_pct": new_pct, "status_atividade": status})
        old = _STATE.get(macro_id, (0, 0))[1]
        _STATE[macro_id] = (0, new_pct)
    except Exception as e:
        print(f"  ⚠️  recalc_macro {macro_id}: {e}")

def _recalc_micro(micro_id: str, macro_id: str):
    """Recalcula micro a partir dos sub-filhos, então propaga para macro."""
    try:
        res = sb.table("hub_atividades").select("id,conclusao_pct,peso_pct").eq("parent_id", micro_id).execute()
        children = res.data or []
        if not children:
            return
        total_peso = sum(float(c.get("peso_pct") or 1) for c in children)
        if total_peso <= 0:
            return
        avg = sum(float(c.get("conclusao_pct") or 0) * float(c.get("peso_pct") or 1) for c in children) / total_peso
        new_pct = min(100, int(round(avg)))
        status = "concluida" if new_pct >= 100 else ("em_execucao" if new_pct > 0 else "nao_iniciada")
        _upd("hub_atividades", {"id": micro_id}, {"conclusao_pct": new_pct, "status_atividade": status})
        _STATE[micro_id] = (0, new_pct)
    except Exception as e:
        print(f"  ⚠️  recalc_micro {micro_id}: {e}")
    _recalc_macro(macro_id)


# ── Definição dos 7 RDOs ──────────────────────────────────────────────────────
#
#  Cada RDO tem:
#   - data, clima, interrupcao, equipe, observacoes
#   - atividades: lista de (act_id, prod_dia, total_qty, progresso_manual)
#     - para subs/micros com total_qty: prod_dia é a quantidade produzida no dia
#     - para atividades sem quantidade: usa progresso_manual (pct direto)
#
# Narrativa realista (montanha-russa):
#  Dia 01/04 — Excelente: equipe completa, 52 furos (acima da meta 48)
#  Dia 02/04 — Bom: âncoras OK + 90m trilhos
#  Dia 03/04 — Chuva forte → interrupção às 13h. 60m trilhos + conferência módulos
#  Dia 04/04 — Recuperação: estrutura 100% + início módulos (80 módulos)
#  Dia 05/04 — Acima da meta: 100 módulos (meta 90) + início cabeamento
#  Dia 06/04 — Chuva mod. + ACIDENTE Josué Silva. 60 módulos. Equipe=7
#  Dia 07/04 — Briefing segurança + 240 módulos acumulados confirmados

RDOS_PLAN = [
    {
        "date": date(2026, 4, 1),
        "id": "RDO-306-001",
        "clima": "Ensolarado",
        "interrupcao": False,
        "equipe": 8,
        "houve_chuva": False,
        "houve_acidente": False,
        "obs": "Início da obra. Mobilização completa. Reunião de alinhamento com equipe às 07h. "
               "52 perfurações realizadas — superando meta diária de 48. Excelente ritmo.",
        "atividades_texto": "Perfuração das estruturas de concreto — 52 furos executados",
        "updates": [
            # (act_id, prod_dia, total_qty)
            (A["M1_1_1"], 48, 48),   # Perfuração: 48/48 = 100%
        ],
        "imgs": [
            (IMGS["equipe"][0], "equipe", "Equipe completa com EPIs — dia 1"),
            (IMGS["ferramentas"][0], "ferramentas", "Furadeiras e equipamentos dia 1"),
            (IMGS["gerais"][0], "gerais", "Vista geral — Av. das Indústrias 1420"),
        ],
    },
    {
        "date": date(2026, 4, 2),
        "id": "RDO-306-002",
        "clima": "Parcialmente Nublado",
        "interrupcao": False,
        "equipe": 8,
        "houve_chuva": False,
        "houve_acidente": False,
        "obs": "Instalação das âncoras químicas concluída (48/48). Início das calhas: "
               "90m de trilho fixados com nivelamento a laser. Progresso acima do previsto.",
        "atividades_texto": "Âncoras concluídas + 90m de trilhos montados",
        "updates": [
            (A["M1_1_2"], 48, 48),   # Resina: 48/48 = 100%
            (A["M1_2"],   90, 240),  # Calhas: 90/240 = 37%
        ],
        "imgs": [
            (IMGS["equipe"][1], "equipe", "Equipe instalando âncoras — dia 2"),
            (IMGS["gerais"][1], "gerais", "Âncoras instaladas — detalhe fixação"),
        ],
    },
    {
        "date": date(2026, 4, 3),
        "id": "RDO-306-003",
        "clima": "Chuvoso Forte",
        "interrupcao": True,
        "equipe": 8,
        "houve_chuva": True,
        "houve_acidente": False,
        "motivo_interrupcao": "Chuva forte a partir das 13h — paralisação por segurança. "
                              "Guarda-chuva de cronograma ativado. Previsão de recuperação D+1.",
        "obs": "Início produtivo: 60m de trilhos adicionais até as 12h45. "
               "Pós-chuva: conferência e organização dos 300 módulos recebidos. "
               "Nivelamento parcial executado. Parada obrigatória às 13h por segurança.",
        "atividades_texto": "60m trilhos + conferência módulos recebidos + nivelamento parcial",
        "updates": [
            (A["M1_2"],   60, 240),  # Calhas: +60m → 150/240 = 62%
            (A["M1_3"],   0.4, 1),   # Nivelamento: 40%
        ],
        "imgs": [
            (IMGS["gerais"][2], "gerais", "Chuva forte — obra paralisada às 13h"),
            (IMGS["gerais"][3], "gerais", "Módulos conferidos e organizados no almoxarifado"),
        ],
    },
    {
        "date": date(2026, 4, 4),
        "id": "RDO-306-004",
        "clima": "Ensolarado",
        "interrupcao": False,
        "equipe": 8,
        "houve_chuva": False,
        "houve_acidente": False,
        "obs": "Dia de recuperação excepcional. Equipe empenhou turno estendido. "
               "Calhas concluídas (240m). Nivelamento 100%. Início imediato dos módulos: "
               "80 unidades fixadas. Macro 1 (Estrutura Metálica) 100% concluída!",
        "atividades_texto": "Estrutura 100% — 90m trilhos + nivelamento concluído + 80 módulos FV",
        "updates": [
            (A["M1_2"],   90, 240),  # Calhas: +90m → 240/240 = 100%
            (A["M1_3"],   0.6, 1),   # Nivelamento: +60% → 100%
            (A["M2_1_1"], 300, 300), # Descarregamento: 300/300 = 100%
            (A["M2_1_2"], 80, 300),  # Fixação: 80/300 = 26%
        ],
        "imgs": [
            (IMGS["equipe"][2], "equipe", "Equipe mobilizada — dia de recuperação"),
            (IMGS["gerais"][4], "gerais", "Estrutura metálica 100% — marcos concluídos"),
        ],
    },
    {
        "date": date(2026, 4, 5),
        "id": "RDO-306-005",
        "clima": "Ensolarado",
        "interrupcao": False,
        "equipe": 8,
        "houve_chuva": False,
        "houve_acidente": False,
        "obs": "Produtividade excepcional — 100 módulos fixados (meta 90). "
               "Início do cabeamento CC: 150m instalados. "
               "SPI do dia = 1.11 — projeto adiantado. Equipe motivada.",
        "atividades_texto": "100 módulos (meta 90) + 150m cabeamento CC — acima da meta",
        "updates": [
            (A["M2_1_2"], 100, 300), # Fixação: +100 → 180/300 = 60%
            (A["M2_1_3"], 150, 600), # Cabeamento: 150/600 = 25%
        ],
        "imgs": [
            (IMGS["equipe"][3], "equipe", "Equipe instalando módulos — ritmo acima da meta"),
            (IMGS["ferramentas"][1], "ferramentas", "Torquímetro calibrado + cabos CC"),
        ],
    },
    {
        "date": date(2026, 4, 6),
        "id": "RDO-306-006",
        "clima": "Chuvoso",
        "interrupcao": True,
        "equipe": 7,
        "houve_chuva": True,
        "houve_acidente": True,
        "motivo_interrupcao": "Chuva moderada a partir das 10h. Interrupção preventiva nas áreas elevadas.",
        "descricao_acidente": "Josué Silva (auxiliar) sofreu contusão no tornozelo direito ao descer da estrutura "
                              "com piso molhado. Atendimento de primeiros socorros no local. Encaminhado ao SESI. "
                              "CAT emitida. Afastamento previsto 2 dias. EPIs adequados — causa: solo escorregadio.",
        "obs": "Acidente leve registrado às 09h45 — Josué Silva. CAT emitida imediatamente. "
               "Apesar do incidente, equipe executou 60 módulos antes da parada por chuva. "
               "Reunião emergencial de segurança realizada às 15h com toda a equipe.",
        "atividades_texto": "60 módulos + 100m cabeamento. ACIDENTE registrado — CAT emitida.",
        "updates": [
            (A["M2_1_2"], 60, 300),  # Fixação: +60 → 240/300 = 80%
            (A["M2_1_3"], 100, 600), # Cabeamento: +100 → 250/600 = 41%
        ],
        "imgs": [
            (IMGS["falhas"][0], "falhas", "Registro acidente — solo molhado área de trabalho"),
            (IMGS["falhas"][1], "falhas", "Condições de piso — chuva moderada dia 6"),
        ],
    },
    {
        "date": date(2026, 4, 7),
        "id": "RDO-306-007",
        "clima": "Ensolarado",
        "interrupcao": False,
        "equipe": 7,
        "houve_chuva": False,
        "houve_acidente": False,
        "obs": "DDS reforçado: 45min de treinamento em segurança no trabalho em altura e piso molhado. "
               "Retomada plena às 09h30. 240 módulos acumulados (80%) confirmados. "
               "Cabeamento CC avançou para 400m (67%). String Box: 1/4 iniciada. "
               "Forecast: conclusão Macro 2 em D+3 (10/04) se ritmo mantido.",
        "atividades_texto": "DDS segurança 45min + Módulos 240 total confirmados + String Box iniciada",
        "updates": [
            (A["M2_1_3"], 150, 600), # Cabeamento: +150 → 400/600 = 67%
            (A["M2_2"],   1, 4),     # String Box: 1/4 = 25%
        ],
        "imgs": [
            (IMGS["equipe"][0], "equipe", "DDS reforçado — treinamento segurança 07/04"),
            (IMGS["gerais"][0], "gerais", "240 módulos instalados — vista aérea simulada"),
        ],
    },
]

def _gen_rdo_id(rdo_id_str: str) -> str:
    """Gera UUID determinístico a partir do id_rdo string."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, rdo_id_str))

def seed_rdos():
    """Insere RDOs e propaga atualizações de atividades."""
    print("\n📋  Seedando RDOs (7 registros)...")

    for rdo in RDOS_PLAN:
        d: date = rdo["date"]
        id_rdo: str = rdo["id"]
        rdo_uuid = _gen_rdo_id(id_rdo)
        ts_checkin  = _brt_ts(d, 7, 15)
        ts_checkout = _brt_ts(d, 17, 45 if not rdo["interrupcao"] else 30)

        # rdo_master
        master = {
            "id":                rdo_uuid,
            "id_rdo":            id_rdo,
            "status":            "finalizado",
            "contrato":          CONTRATO,
            "projeto":           PROJETO,
            "cliente":           CLIENTE,
            "localizacao":       LOC,
            "data":              d.isoformat(),
            "turno":             "Diurno",
            "condicao_climatica": rdo["clima"],
            "houve_interrupcao": rdo["interrupcao"],
            "motivo_interrupcao": rdo.get("motivo_interrupcao", ""),
            "equipe_alocada":    rdo["equipe"],
            "observacoes":       rdo["obs"],
            "houve_chuva":       rdo.get("houve_chuva", False),
            "quantidade_chuva":  "Forte" if rdo.get("houve_chuva") and rdo["clima"] == "Chuvoso Forte" else (
                                 "Moderada" if rdo.get("houve_chuva") else None),
            "houve_acidente":    rdo.get("houve_acidente", False),
            "descricao_acidente": rdo.get("descricao_acidente", ""),
            "checkin_lat":       LAT_OBRA + (0.0001 * (d.day % 3)),
            "checkin_lng":       LNG_OBRA + (0.0001 * (d.day % 2)),
            "checkin_endereco":  LOC,
            "checkin_timestamp": ts_checkin,
            "checkout_lat":      LAT_OBRA,
            "checkout_lng":      LNG_OBRA,
            "checkout_endereco": LOC,
            "checkout_timestamp": ts_checkout,
            "signatory_name":    "Carlos Menezes" if d.day <= 5 else "Ricardo Sousa",
            "ai_summary":        _gen_ai_summary(rdo),
            "view_token":        str(uuid.uuid4()).replace("-", "")[:32],
            "created_at":        ts_checkin,
            "updated_at":        ts_checkout,
            "client_id":         CLIENT_ID,
        }
        _ins("rdo_master", master)

        # rdo_atividades
        _ins("rdo_atividades", {
            "rdo_id":      rdo_uuid,
            "atividade":   rdo["atividades_texto"],
            "efetivo":     rdo["equipe"],
            "observacao":  "Em andamento",
        })

        # Atualiza atividades + cria historico
        ts_update = _brt_ts(d, 17, 0)
        for (act_id, prod_dia, total_qty) in rdo["updates"]:
            _update_activity(act_id, prod_dia, total_qty, ts_update, id_rdo)

        # Propaga recalc para micros/macros
        _recalc_micro(A["M1_1"], A["M1"])
        _recalc_macro(A["M1"])
        _recalc_micro(A["M2_1"], A["M2"])
        _recalc_macro(A["M2"])
        _recalc_macro(A["M3"])

        # hub_auditoria_imgs
        for (url, categoria, legenda) in rdo["imgs"]:
            _ins("hub_auditoria_imgs", {
                "contrato":     CONTRATO,
                "categoria":    categoria,
                "url":          url,
                "legenda":      legenda,
                "autor":        master["signatory_name"],
                "data_captura": d.isoformat(),
                "client_id":    CLIENT_ID,
            })

        print(f"  ✓ {id_rdo} ({d.strftime('%d/%m')}) — equipe={rdo['equipe']} clima={rdo['clima']}")

    print("✅  RDOs e histórico de progresso inseridos.")


def _gen_ai_summary(rdo: dict) -> str:
    d = rdo["date"]
    equipe = rdo["equipe"]
    interrupcao = rdo["interrupcao"]
    acidente = rdo.get("houve_acidente", False)
    summary = f"[{d.strftime('%d/%m')}] "
    if acidente:
        summary += "⚠️ OCORRÊNCIA DE SEGURANÇA — CAT emitida. "
    if interrupcao:
        summary += "Interrupção por condições climáticas. "
    summary += f"Equipe: {equipe} colaboradores. "
    if not interrupcao and not acidente:
        summary += "Execução dentro ou acima do planejado. "
    summary += rdo["obs"][:120]
    return summary


# ═══════════════════════════════════════════════════════════════════════════════
# 4. FINANCEIRO — fin_custos com datas para S-curve
# ═══════════════════════════════════════════════════════════════════════════════

def seed_financeiro():
    """
    Lançamentos financeiros com datas para alimentar a Curva S financeira.
    Simula: adimplência, atraso, sobrecusto e economia — cenário real de obra.
    """
    print("\n💰  Seedando fin_custos (13 registros com datas)...")

    F_BASE = dict(contrato=CONTRATO, client_id=CLIENT_ID)

    registros = [
        # ── MACRO 1 — Estrutura (concluída) ───────────────────────────────────
        {**F_BASE, "categoria_nome": "Material",
         "empresa": "Perfiltec Alumínio Ltda",
         "descricao": "Perfis e trilhos de alumínio — 240m",
         "valor_previsto": 18000, "valor_executado": 18000,
         "status": "executado", "data": "2026-04-01"},

        {**F_BASE, "categoria_nome": "Material",
         "empresa": "QuimicFix Brasil",
         "descricao": "Âncoras químicas + resina epóxi (48 conj.)",
         "valor_previsto": 4800, "valor_executado": 4800,
         "status": "executado", "data": "2026-04-01"},

        {**F_BASE, "categoria_nome": "Mão de Obra",
         "empresa": "Equipe Carlos Menezes",
         "descricao": "Equipe estrutura metálica — 5d/4h adicional",
         "valor_previsto": 12000, "valor_executado": 13800,   # sobrecusto: turno extra dia 4
         "status": "executado", "data": "2026-04-02"},

        {**F_BASE, "categoria_nome": "Equipamento",
         "empresa": "LocaFer Equipamentos",
         "descricao": "Furadeira de impacto industrial + torquímetro — 5 dias",
         "valor_previsto": 1500, "valor_executado": 1500,
         "status": "executado", "data": "2026-04-02"},

        # ── MACRO 2 — Módulos (em execução) ───────────────────────────────────
        {**F_BASE, "categoria_nome": "Material",
         "empresa": "SunBrasil Energia Solar",
         "descricao": "Módulos FV 400W (Risen) — 300 unidades",
         "valor_previsto": 114000, "valor_executado": 91200,  # 80% entregues/pagos
         "status": "parcial", "data": "2026-04-03"},

        {**F_BASE, "categoria_nome": "Material",
         "empresa": "CaboTech Elétrica",
         "descricao": "Cabo CC 6mm² (preto + vermelho) — 600m",
         "valor_previsto": 3600, "valor_executado": 2400,     # 67% executado
         "status": "parcial", "data": "2026-04-04"},

        {**F_BASE, "categoria_nome": "Mão de Obra",
         "empresa": "Equipe Ricardo Sousa",
         "descricao": "Equipe módulos e elétrica CC — 4d/5h previsto",
         "valor_previsto": 14400, "valor_executado": 14400,
         "status": "executado", "data": "2026-04-04"},

        # ── Ocorrências (acidente Dia 6) ──────────────────────────────────────
        {**F_BASE, "categoria_nome": "Outros",
         "empresa": "EPI Nordeste",
         "descricao": "EPIs adicionais pós-acidente RDO-006 — kit antiderrapante",
         "valor_previsto": 850, "valor_executado": 850,
         "status": "executado", "data": "2026-04-06"},

        {**F_BASE, "categoria_nome": "Outros",
         "empresa": "SESI Fortaleza",
         "descricao": "Atendimento médico Josué Silva + emissão CAT + fisioterapia",
         "valor_previsto": 320, "valor_executado": 520,       # sobrecusto inesperado
         "status": "executado", "data": "2026-04-06"},

        # ── MACRO 2 (restante previsto) ───────────────────────────────────────
        {**F_BASE, "categoria_nome": "Material",
         "empresa": "WEG Indústrias S.A.",
         "descricao": "String Box CC + 4 inversores 30kW (WEG SIW300H)",
         "valor_previsto": 52000, "valor_executado": 0,
         "status": "previsto", "data": "2026-04-10"},

        # ── MACRO 3 — CA / Comissionamento (previsto) ─────────────────────────
        {**F_BASE, "categoria_nome": "Material",
         "empresa": "SchneiderElectric Brasil",
         "descricao": "QDC, disjuntores CA, medidor bidirecional + CT",
         "valor_previsto": 18500, "valor_executado": 0,
         "status": "previsto", "data": "2026-04-11"},

        {**F_BASE, "categoria_nome": "Mão de Obra",
         "empresa": "Equipe Felipe Araújo",
         "descricao": "Equipe elétrica CA e comissionamento — 6d",
         "valor_previsto": 14400, "valor_executado": 0,
         "status": "previsto", "data": "2026-04-11"},

        {**F_BASE, "categoria_nome": "Serviço",
         "empresa": "Eng. RT — Vistoria Solar",
         "descricao": "Engenheiro RT — vistoria técnica + ART startup + ANEEL",
         "valor_previsto": 3800, "valor_executado": 0,
         "status": "previsto", "data": "2026-04-14"},
    ]

    for r in registros:
        _ins("fin_custos", r)

    total_prev = sum(r["valor_previsto"] for r in registros)
    total_exec = sum(r["valor_executado"] for r in registros)
    print(f"  ✓ {len(registros)} lançamentos | Previsto: R$ {total_prev:,.0f} | Executado: R$ {total_exec:,.0f} ({total_exec/total_prev*100:.1f}%)")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. TIMELINE — Eventos, Falhas, Documentos
# ═══════════════════════════════════════════════════════════════════════════════

def seed_timeline():
    """Hub timeline com mix de eventos reais: acontecimentos, falhas, docs, reuniões."""
    print("\n📅  Seedando hub_timeline (10 registros)...")

    BASE = dict(contrato=CONTRATO, client_id=CLIENT_ID)

    entries = [
        {**BASE,
         "tipo": "Marco",
         "titulo": "🚀 Mobilização — Início Oficial da Obra",
         "descricao": (
             "Reunião de kickoff realizada com toda a equipe às 07h. "
             "Contrato assinado em 28/03/2026. Prazo contratual: 14 dias corridos. "
             "Efetivo planejado: 8 colaboradores diretos + 2 terceirizados. "
             "Área delimitada, EPI distribuído, DDS inicial realizado."
         ),
         "autor": "Carlos Menezes",
         "created_at": _brt_ts(date(2026, 4, 1), 8, 0),
         "is_document": False, "is_cost": False},

        {**BASE,
         "tipo": "Atualização",
         "titulo": "✅ Estrutura Metálica 100% — Macro 1 Concluído",
         "descricao": (
             "Macro 1 (Estrutura Metálica) concluído no prazo apesar da chuva forte no dia 3. "
             "Recuperação executada em turno estendido no dia 4 com toda a equipe. "
             "240m de trilhos instalados, 48 âncoras fixadas, nivelamento aprovado. "
             "Próximo passo: acelerar instalação dos módulos FV."
         ),
         "autor": "Carlos Menezes",
         "created_at": _brt_ts(date(2026, 4, 4), 18, 0),
         "is_document": False, "is_cost": False},

        {**BASE,
         "tipo": "Alerta",
         "titulo": "⚠️ Interferência Climática — Chuva Forte 03/04",
         "descricao": (
             "Paralisação às 13h por chuva forte (>40mm/h). "
             "Protocolo de segurança ativado — retirada de pessoal das estruturas elevadas. "
             "Impacto estimado: 4h produtivas perdidas. "
             "Plano de recuperação ativado para D+1 com turno estendido. "
             "Nenhum dano material ou humano registrado."
         ),
         "autor": "Carlos Menezes",
         "created_at": _brt_ts(date(2026, 4, 3), 13, 30),
         "is_document": False, "is_cost": False},

        {**BASE,
         "tipo": "Falha",
         "titulo": "🚨 ACIDENTE — Josué Silva, Contusão Tornozelo (06/04)",
         "descricao": (
             "REGISTRO DE ACIDENTE DE TRABALHO — CAT EMITIDA\n\n"
             "Colaborador: Josué Silva (auxiliar de montagem, 2 anos de empresa)\n"
             "Horário: 09h45 | Local: Setor B — trilho inferior, nível 0\n"
             "Causa: piso molhado por chuva residual + solo compactado úmido\n"
             "Natureza: contusão tornozelo direito — Grau leve\n"
             "Ação imediata: primeiros socorros + encaminhamento SESI Fortaleza\n"
             "CAT emitida às 11h. Afastamento: 2 dias úteis (07 e 08/04)\n\n"
             "Medidas corretivas: tapete antiderrapante + DDS reforçado 07/04 + inspeção EPI."
         ),
         "autor": "Ricardo Sousa",
         "created_at": _brt_ts(date(2026, 4, 6), 10, 15),
         "is_document": False, "is_cost": False},

        {**BASE,
         "tipo": "Documento",
         "titulo": "📄 ART de Execução — Engenheiro Responsável Técnico",
         "descricao": (
             "Anotação de Responsabilidade Técnica (ART) emitida junto ao CREA-CE. "
             "Engenheiro RT: Dr. Antônio Bezerra — CREA/CE 12.345-D. "
             "Número ART: 2026CE000843. Valor da ART: R$ 3.800,00. "
             "Escopo: EPC Usina Solar 120 kWp — sistemas fotovoltaicos conectados à rede."
         ),
         "autor": "Sistema",
         "created_at": _brt_ts(date(2026, 4, 1), 9, 0),
         "is_document": True, "is_cost": False,
         "anexo_nome": "ART_306_2026_Bezerra.pdf",
         "anexo_url": ""},

        {**BASE,
         "tipo": "Reunião",
         "titulo": "📋 Reunião de Alinhamento Semanal — Progresso 50%",
         "descricao": (
             "Reunião realizada com gestor Ferreira & Cia às 16h. "
             "Pauta: status de progresso, impacto do acidente, forecast de entrega. "
             "Progresso físico: ~57% (Macro 1: 100%, Macro 2: em execução). "
             "Forecast revisado: entrega até 14/04 mantida com folga de 1 dia. "
             "Cliente satisfeito — solicitou fotos aéreas do telhado para registro."
         ),
         "autor": "Carlos Menezes",
         "created_at": _brt_ts(date(2026, 4, 7), 16, 0),
         "is_document": False, "is_cost": False},

        {**BASE,
         "tipo": "Alerta",
         "titulo": "📦 Interferência de Fornecimento — Módulos Lote 2",
         "descricao": (
             "Atraso de 1 dia no 2º lote de módulos (Risen 400W). "
             "Previsão original: 04/04. Entrega efetiva: 04/04 às 14h (meio período). "
             "Causa: congestionamento na BR-116 — caminhão retido 4h. "
             "Impacto: início da instalação atrasado em ~4h, absorvido pelo ritmo da equipe. "
             "SunBrasil Energia Solar notificada — cláusula de SLA contratual analisada."
         ),
         "autor": "Sistema",
         "created_at": _brt_ts(date(2026, 4, 4), 14, 30),
         "is_document": False, "is_cost": False},

        {**BASE,
         "tipo": "Documento",
         "titulo": "📊 Relatório Fotográfico de Campo — Semana 1",
         "descricao": (
             "Relatório fotográfico semanal contendo 24 imagens documentadas. "
             "Cobertura: mobilização, fundação, trilhos, chegada módulos, DDS. "
             "Formato: PDF compilado com geolocalização e watermark BTP Intelligence. "
             "Enviado ao cliente Ferreira & Cia via email em 05/04/2026."
         ),
         "autor": "Carlos Menezes",
         "created_at": _brt_ts(date(2026, 4, 5), 19, 0),
         "is_document": True, "is_cost": False,
         "anexo_nome": "Relatorio_Fotografico_Semana1_306.pdf",
         "anexo_url": ""},

        {**BASE,
         "tipo": "Custo",
         "titulo": "💸 Sobrecusto Identificado — Turno Extra 04/04 + Acidente",
         "descricao": (
             "Dois eventos geraram sobrecusto não planejado:\n"
             "1. Turno estendido em 04/04 para recuperação da chuva: +R$ 1.800 (M.O.)\n"
             "2. Atendimento médico Josué Silva + fisioterapia: +R$ 200 além do previsto\n"
             "Total sobrecusto identificado: R$ 2.000 (~0,7% do contrato)\n"
             "Margem ainda positiva. Nenhuma solicitação de aditivo necessária."
         ),
         "autor": "Sistema",
         "created_at": _brt_ts(date(2026, 4, 6), 20, 0),
         "is_document": False, "is_cost": True,
         "custo_valor": 2000,
         "custo_categoria": "Mão de Obra"},

        {**BASE,
         "tipo": "Atualização",
         "titulo": "🔋 240 Módulos Instalados — 80% Macro 2",
         "descricao": (
             "Marco parcial atingido: 240/300 módulos fotovoltaicos instalados e torqueados. "
             "Eficiência de montagem: 48 módulos/dia (meta: 45). "
             "Cabeamento CC: 400/600m (67%). String Box: 1/4 inversores iniciada. "
             "Forecast Macro 2: conclusão prevista para 10/04. "
             "SPI acumulado: 0.94 (leve atraso por chuva e acidente — recuperável)."
         ),
         "autor": "Ricardo Sousa",
         "created_at": _brt_ts(date(2026, 4, 7), 17, 45),
         "is_document": False, "is_cost": False},
    ]

    for e in entries:
        _ins("hub_timeline", e)

    print(f"  ✓ {len(entries)} registros (Marco, Falha, Alerta, Documento, Reunião, Custo, Atualização)")


# ═══════════════════════════════════════════════════════════════════════════════
# 6. UPDATE CONTRATOS — equipe_presente_hoje + chuva_acumulada_mm
# ═══════════════════════════════════════════════════════════════════════════════

def update_contratos():
    """
    Atualiza campos de runtime no contratos:
      - equipe_presente_hoje: do último RDO (7 colaboradores em 07/04)
      - chuva_acumulada_mm: acumulado dos 7 dias (~45mm — chuva nos dias 3 e 6)
    Se as colunas não existirem na tabela, o update falhará silenciosamente.
    """
    print("\n🔧  Atualizando contratos (equipe_presente_hoje, chuva_acumulada_mm)...")
    _upd("contratos", {"contrato": CONTRATO}, {
        "equipe_presente_hoje": 7,     # último RDO (07/04 — Josué ainda afastado)
        "chuva_acumulada_mm":   45.0,  # acumulado semana (dia 3 forte + dia 6 moderada)
        "status": "Em Execução",
    })
    print("  ✓ contratos atualizado")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    clean_only  = "--clean-only"  in sys.argv
    skip_clean  = "--skip-clean"  in sys.argv

    print("=" * 60)
    print("  🌞  SEED DEMO — Usina Solar 120 kWp")
    print(f"  Contrato: {CONTRATO}")
    print(f"  Data base: {INICIO} → 2026-04-14")
    print("=" * 60)

    if not skip_clean:
        clean()

    if clean_only:
        print("\n✅  Modo --clean-only concluído.")
        return

    seed_atividades()
    seed_rdos()
    seed_financeiro()
    seed_timeline()
    update_contratos()

    # Estado final das macros (resumo)
    print("\n📊  Estado final das atividades:")
    for key, label in [("M1", "Macro 1 — Estrutura"), ("M2", "Macro 2 — Módulos/CC"), ("M3", "Macro 3 — CA/Comissioning")]:
        pct = _STATE.get(A[key], (0, 0))[1]
        print(f"  {label}: {pct}%")

    total = sum(_STATE.get(A[k], (0,0))[1] * w for k, w in [("M1", 35), ("M2", 40), ("M3", 25)]) / 100
    print(f"  Progresso ponderado global: {total:.1f}%")

    print("\n✅  Seed concluído com sucesso!")
    print("   Lembre de invalidar o cache Redis/pickle antes de recarregar o painel:")
    print("   → python -c \"from bomtempo.core.data_loader import DataLoader; DataLoader.invalidate_cache('11111111-1111-1111-1111-111111111111')\"")


if __name__ == "__main__":
    main()
