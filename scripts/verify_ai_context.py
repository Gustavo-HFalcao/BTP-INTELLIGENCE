
import os
import sys
import pandas as pd
from typing import Dict, Any

# Set path to project root
sys.path.append(os.getcwd())

from bomtempo.core.data_loader import DataLoader
from bomtempo.core.ai_context import AIContext
from bomtempo.core.ai_client import ai_client

def run_verification():
    print("=== STARTING AI CONTEXT VERIFICATION ===")
    
    # 1. Load Real Data from Sheets
    loader = DataLoader()
    data = loader.load_all() # This uses Config.SHEET_URLS
    
    # 2. Generate Context
    context = AIContext.get_dashboard_context(data)
    system_prompt = AIContext.get_system_prompt(is_mobile=False)
    
    # 3. Define Test Prompts
    prompts = [
        "Qual é o status físico atual (realizado %) de todos os projetos ativos no painel?",
        "Liste os 5 contratos de maior valor e seus respectivos status.",
        "Com base nos dados de O&M, qual projeto teve a maior energia injetada nos últimos registros?",
        "Identifique 3 projetos onde o realizado (%) está abaixo do previsto (%).",
        "Quais são os próximos milestones (atividades) para o projeto 'Indústria de Papel'?",
        "Qual o total de faturamento líquido registrado na aba de O&M?",
        "Quais projetos estão atualmente em status de 'Planejamento'?",
        "No financeiro, quais contratos já ultrapassaram o valor contratado de material (material_realizado > material_contratado)?",
        "Fazendo uma média geral, qual o percentual médio de conclusão (conclusao_pct) dos projetos listados no cronograma?",
        "Resuma a saúde financeira e física do contrato BOM-029 (PapelParaná).",
        "Quais são as atividades com maior atraso ou menor percentual de conclusão no cronograma macro?",
        "Existe alguma obra onde o comentário indique risco ou alerta crítico?"
    ]
    
    results = []
    
    print(f"Running {len(prompts)} prompts against AI...")
    
    for i, p in enumerate(prompts):
        print(f"\n[Prompt {i+1}/12]: {p}")
        messages = [
            {"role": "system", "content": f"{system_prompt}\n\n{context}"},
            {"role": "user", "content": p}
        ]
        
        try:
            response = ai_client.query(messages)
            # Safe print for Windows console
            safe_resp = response[:100].encode('ascii', 'ignore').decode('ascii')
            print(f"[Response Header]: {safe_resp}...")
            results.append({
                "id": i + 1,
                "prompt": p,
                "response": response
            })
        except Exception as e:
            print(f"Error on prompt {i+1}: {e}")
            results.append({"id": i + 1, "prompt": p, "response": f"ERROR: {e}"})

    # 4. Save results for analysis
    output_df = pd.DataFrame(results)
    # Force UTF-8 encoding for CSV
    output_df.to_csv("ai_verification_results.csv", index=False, encoding='utf-8-sig')
    print("\n=== VERIFICATION FINISHED. Results saved to ai_verification_results.csv ===")

    # 5. Quick Internal check of the data
    print("\n--- GROUND TRUTH SNIPPETS ---")
    for key, df in data.items():
        print(f"\n{key.upper()} Columns: {list(df.columns)}")

    if "obras" in data:
        print("\nObras (Latest Phys):")
        df_obras = data["obras"].copy()
        if "data" in df_obras.columns:
            df_obras["data"] = pd.to_datetime(df_obras["data"], errors="coerce")
            latest = df_obras.sort_values("data").groupby("projeto").last().reset_index()
            print(latest[["projeto", "realizado_pct", "previsto_pct"]].head(10).to_string())

    if "contratos" in data:
        print("\nContratos (Top 5):")
    if "projeto" in data["contratos"].columns:
        print(data["contratos"].sort_values("valor_contratado", ascending=False).head(5)[["contrato", "projeto", "valor_contratado"]].to_string())
    else:
        print(data["contratos"].sort_values("valor_contratado", ascending=False).head(5)[["contrato", "valor_contratado"]].to_string())

if __name__ == "__main__":
    run_verification()
