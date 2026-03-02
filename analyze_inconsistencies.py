
import asyncio
import os
import sys
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(os.getcwd())

from bomtempo.core.data_loader import DataLoader

def analyze_data_quality():
    print("--- ANALISE PROFUNDA DE DADOS ---")
    loader = DataLoader()
    data = loader.load_all()
    
    df_contratos = data.get("contratos", pd.DataFrame())
    df_obras = data.get("obras", pd.DataFrame())
    df_financeiro = data.get("financeiro", pd.DataFrame())
    df_om = data.get("om", pd.DataFrame())
    df_projeto = data.get("projeto", pd.DataFrame())
    
    issues = []
    
    # 1. ANÁLISE GEOGRÁFICA
    print("\n1. GEOGRAFIA")
    if not df_contratos.empty and "localizacao" in df_contratos.columns:
        states = df_contratos["localizacao"].apply(lambda x: x.split(",")[-1].strip() if "," in str(x) else "N/A").unique()
        print(f"Estados presentes: {states}")
        if len(states) < 3:
            issues.append(f"[PROBLEMA] Baixa diversidade geográfica: Apenas {len(states)} estados encontrados ({', '.join(states)}). Ideal para demo nacional seria 5+.")
            
    # 2. ANÁLISE FINANCEIRA (Contratado vs Executado)
    print("\n2. COERÊNCIA FINANCEIRA")
    if not df_financeiro.empty and not df_contratos.empty:
        # Sum financeiro by contract
        fin_stats = df_financeiro.groupby("contrato")[["servico_realizado", "material_realizado"]].sum().sum(axis=1)
        
        for idx, row in df_contratos.iterrows():
            contrato = row.get("contrato")
            valor_contratado = float(row.get("valor_contratado", 0))
            
            valor_executado = fin_stats.get(contrato, 0)
            
            if valor_contratado > 0:
                pct_exec_fin = (valor_executado / valor_contratado) * 100
                status = row.get("status", "")
                
                # Check specifics
                if status == "Concluído" and pct_exec_fin < 90:
                     issues.append(f"[ALERTA] Contrato {contrato} está 'Concluído' mas só tem {pct_exec_fin:.1f}% de valor realizado no financeiro.")
                
                if status == "Em Execução" and pct_exec_fin > 100:
                     issues.append(f"[ALERTA] Contrato {contrato} gastou {pct_exec_fin:.1f}% do valor contratado (Estouro de orçamento?).")
    else:
        issues.append("[PROBLEMA] Tabela Financeira vazia ou sem vínculos claros.")

    # 3. ANÁLISE DE CRONOGRAMA (Físico vs Datas)
    print("\n3. CRONOGRAMA FÍSICO")
    if not df_obras.empty:
        # Check for stalled projects (no logs in last 60 days)
        last_date = pd.to_datetime(df_obras["data"], errors="coerce").max()
        if pd.notna(last_date):
            active_contracts = df_obras[df_obras["realizado_pct"] < 100]["contrato"].unique()
            for c in active_contracts:
                c_logs = df_obras[df_obras["contrato"] == c]
                c_last_date = pd.to_datetime(c_logs["data"], errors="coerce").max()
                
                days_diff = (last_date - c_last_date).days
                if days_diff > 60:
                    issues.append(f"[ALERTA] Contrato {c} 'Em Execução' não tem logs há {days_diff} dias (Obra parada?).")

    # 4. ORPHAN RECORDS
    print("\n4. INTEGRIDADE REFERENCIAL")
    ids_obras = set(df_obras["contrato"].unique()) if not df_obras.empty else set()
    ids_contratos = set(df_contratos["contrato"].unique()) if not df_contratos.empty else set()
    
    missing_in_obras = ids_contratos - ids_obras
    if missing_in_obras:
         issues.append(f"[ALERTA] {len(missing_in_obras)} Contratos sem nenhum registro de obra (Ex: {list(missing_in_obras)[:3]}...).")

    # 5. ORPHAN FINANCIAL RECORDS
    print("\n5. ORFAOS FINANCEIROS")
    ids_fin = set(df_financeiro["contrato"].unique()) if not df_financeiro.empty else set()
    missing_fin_in_contratos = ids_fin - ids_contratos
    if missing_fin_in_contratos:
        issues.append(f"[PROBLEMA] {len(missing_fin_in_contratos)} Registros financeiros sem Contrato valido (Ex: {list(missing_fin_in_contratos)[:3]}...).")

    # 6. DUPLICIDADE DE LOGS
    print("\n6. DUPLICIDADE")
    if not df_obras.empty:
        dupes = df_obras.duplicated(subset=["contrato", "data"], keep=False)
        if dupes.any():
            n_dupes = dupes.sum()
            issues.append(f"[ALERTA] {n_dupes} Logs de obra duplicados (mesmo contrato e data).")

    # 7. DATAS FUTURAS EM REALIZADO
    print("\n7. CONSISTENCIA TEMPORAL")
    now = pd.Timestamp.now()
    if not df_obras.empty:
        future_logs = df_obras[(pd.to_datetime(df_obras["data"], errors="coerce") > now) & (df_obras["realizado_pct"] > 0)]
        if not future_logs.empty:
             issues.append(f"[PROBLEMA] {len(future_logs)} registros de obra com data futura porem com progresso realizado.")

    # 8. PROGRESSO NAO MONOTONICO (Regressao)
    print("\n8. PROGRESSO FISICO (Monotonicidade)")
    if not df_obras.empty:
        # Sort by contract and date
        df_obras_sorted = df_obras.sort_values(by=["contrato", "data"])
        for contrato, group in df_obras_sorted.groupby("contrato"):
            # Check if realized_pct decreases
            pcts = group["realizado_pct"].fillna(0).tolist()
            if not all(x <= y for x, y in zip(pcts, pcts[1:])):
                 # Ignore small drops? No, strict check.
                 issues.append(f"[ALERTA] Contrato {contrato} tem regresso no % realizado (o progresso diminuiu em algum mes).")

    print("\n--- RESUMO DAS INCONSISTÊNCIAS ENCONTRADAS ---")
    
    # 9. ANALISE O&M
    print("\n9. ANALISE O&M (Operacao e Manutencao)")
    if not df_om.empty:
        # Orphans
        ids_om = set(df_om["contrato"].unique())
        orphans_om = ids_om - ids_contratos
        if orphans_om:
             issues.append(f"[PROBLEMA] {len(orphans_om)} Registros de O&M sem contrato valido.")
             
        # Generation before completion?
        # This is tricky without exact completion dates, but let's check if "Em Planejamento" contracts have O&M
        if not df_contratos.empty:
            planning_contracts = df_contratos[df_contratos["status"] == "Em Planejamento"]["contrato"].unique()
            bad_om = [c for c in planning_contracts if c in ids_om]
            if bad_om:
                issues.append(f"[PROBLEMA] Contratos 'Em Planejamento' possuem dados de geracao de energia (Ex: {bad_om[:3]}).")

    # 10. ANALISE PROJETOS (Cronograma)
    print("\n10. ANALISE PROJETOS")
    if not df_projeto.empty:
        # Orphans
        ids_proj = set(df_projeto["contrato"].unique())
        orphans_proj = ids_proj - ids_contratos
        if orphans_proj:
             issues.append(f"[PROBLEMA] {len(orphans_proj)} Projetos sem contrato valido.")
             
        # Date Logic
        if "inicio_previsto" in df_projeto.columns and "termino_previsto" in df_projeto.columns:
            invalid_dates = df_projeto[pd.to_datetime(df_projeto["inicio_previsto"], errors="coerce") > pd.to_datetime(df_projeto["termino_previsto"], errors="coerce")]
            if not invalid_dates.empty:
                issues.append(f"[ERRO] {len(invalid_dates)} Atividades de projeto com Data Inicio > Data Termino.")

    # Final Summary Print
    print("\n--- RESUMO FINAL ---")
    if issues:
        for i in issues:
            print(i)
    else:
        print("[OK] Nenhuma inconsistência grave detectada.")

if __name__ == "__main__":
    analyze_data_quality()
