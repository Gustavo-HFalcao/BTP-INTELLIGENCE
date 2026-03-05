"""
Test script — calls Kimi API with all 7 report prompts and captures full output.
Run from project root: python test_reports.py
"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MOCK_DATA = {
    "contrato": "CT-2025-002",
    "cliente": "Petrobras Distribuidora S.A.",
    "gerado_por": "gustavo",
    "fmt": {
        "budget_planejado_fmt": "R$ 5.2M",
        "budget_realizado_fmt": "R$ 2.8M",
        "budget_variacao_fmt": "53.8% do orcamento executado",
        "budget_over": False,
        "budget_bar_pct": 54,
        "budget_exec_rate_fmt": "53.8%",
        "avanco_fmt": "48.5%",
        "risco_val": "35",
        "risco_label": "MODERADO",
        "equipe_val": "42 / 55",
        "equipe_sub": "76% do efetivo",
        "disc_val": "2 / 5",
        "disc_sub": "2 com atraso",
    },
    "obra": {
        "localizacao": "Rio de Janeiro, RJ",
        "status": "Em Andamento",
        "inicio": "2025-01-15",
        "termino": "2025-12-30",
    },
    "disciplinas": [
        {"categoria": "Civil",                  "previsto_pct": 60, "realizado_pct": 58},
        {"categoria": "Estrutura Metalica",     "previsto_pct": 50, "realizado_pct": 35},
        {"categoria": "Fundacoes",              "previsto_pct": 45, "realizado_pct": 37},
        {"categoria": "Instalacoes Eletricas",  "previsto_pct": 30, "realizado_pct": 32},
        {"categoria": "Hidraulica",             "previsto_pct": 25, "realizado_pct": 28},
    ],
}

PORTFOLIO_DATA = {
    "contrato": "Geral / Portfolio",
    "cliente": "Multiplos Clientes",
    "gerado_por": "gustavo",
    "fmt": {
        "budget_planejado_fmt": "R$ 18.7M",
        "budget_realizado_fmt": "R$ 9.4M",
        "budget_variacao_fmt": "50.3% do orcamento executado",
        "budget_over": False,
        "budget_bar_pct": 50,
        "budget_exec_rate_fmt": "50.3%",
        "avanco_fmt": "44.2%",
        "risco_val": "42",
        "risco_label": "MODERADO",
        "equipe_val": "187 / 240",
        "equipe_sub": "78% do efetivo",
        "disc_val": "4 / 6",
        "disc_sub": "4 com atraso",
    },
    "obra": {
        "localizacao": "RJ, SP, MG",
        "status": "Em Andamento",
        "inicio": "2025-01-01",
        "termino": "2025-12-31",
    },
    "disciplinas": [
        {"categoria": "Civil",                  "previsto_pct": 55, "realizado_pct": 52},
        {"categoria": "Estrutura Metalica",     "previsto_pct": 48, "realizado_pct": 32},
        {"categoria": "Fundacoes",              "previsto_pct": 40, "realizado_pct": 35},
        {"categoria": "Instalacoes Eletricas",  "previsto_pct": 35, "realizado_pct": 37},
        {"categoria": "Hidraulica",             "previsto_pct": 28, "realizado_pct": 30},
        {"categoria": "Acabamentos",            "previsto_pct": 15, "realizado_pct": 8},
    ],
}

SEP = "=" * 80

def run_test(label, approach, data, custom_instruction=""):
    from bomtempo.core.report_service import ReportService
    from bomtempo.core.ai_client import ai_client

    print(f"\n{SEP}")
    print(f"TESTE: {label}")
    print(SEP)

    messages = ReportService.build_ai_prompt(approach, data, custom_instruction=custom_instruction)

    sys_preview = messages[0]["content"][:500]
    user_preview = messages[1]["content"][:800]
    print(f"\n[SYSTEM — 500 chars]:\n{sys_preview}\n")
    print(f"[USER — 800 chars]:\n{user_preview}\n")
    print("-" * 60)
    print("Gerando resposta da IA...\n")

    t0 = time.time()
    try:
        response = ai_client.query(messages, model="kimi-k2-turbo-preview")
        elapsed = time.time() - t0
        print(f"OK — {elapsed:.1f}s — {len(response)} chars\n")
        print(response)
        return response
    except Exception as e:
        elapsed = time.time() - t0
        print(f"ERRO apos {elapsed:.1f}s: {e}")
        return None

if __name__ == "__main__":
    print(f"\n{SEP}")
    print("BOMTEMPO INTELLIGENCE — TESTE REAL (7 relatorios via Kimi API)")
    print(SEP)

    results = {}

    results["1_estrategica"] = run_test(
        "1/7 - IA ESTRATEGICA (CT-2025-002)", "estrategica", MOCK_DATA)

    results["2_analitica"] = run_test(
        "2/7 - IA ANALITICA (CT-2025-002)", "analitica", MOCK_DATA)

    results["3_descritiva"] = run_test(
        "3/7 - IA DESCRITIVA / AUDITORIA (CT-2025-002)", "descritiva", MOCK_DATA)

    results["4_operacional"] = run_test(
        "4/7 - IA OPERACIONAL / CAMPO (CT-2025-002)", "operacional", MOCK_DATA)

    results["5_custom_banco"] = run_test(
        "5/7 - CUSTOM: banco financiador", "custom", MOCK_DATA,
        custom_instruction=(
            "Preciso de um relatorio focado nos riscos financeiros e operacionais "
            "para apresentar ao banco financiador do projeto. O banco quer entender "
            "se a execucao esta dentro do esperado e quais sao os principais riscos "
            "que podem comprometer o prazo e o orcamento. Tom formal e objetivo."
        ),
    )

    results["6_custom_campo"] = run_test(
        "6/7 - CUSTOM: briefing equipe de campo", "custom", MOCK_DATA,
        custom_instruction=(
            "Preciso de um briefing curto e direto para a reuniao de alinhamento "
            "da equipe de campo amanha de manha. Quero destacar as disciplinas "
            "com atraso e o plano de acao para esta semana. Tom direto, pratico, "
            "sem enrolacao — os operarios precisam entender."
        ),
    )

    results["7_portfolio"] = run_test(
        "7/7 - IA ESTRATEGICA — PORTFOLIO GERAL", "estrategica", PORTFOLIO_DATA)

    print(f"\n{SEP}")
    print("RESUMO")
    print(SEP)
    for key, result in results.items():
        status = f"OK ({len(result)} chars)" if result else "FALHOU"
        print(f"  {key:25s} -> {status}")
    print()
