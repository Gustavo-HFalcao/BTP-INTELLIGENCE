import os
from datetime import datetime, timedelta
from bomtempo.core.supabase_client import sb_insert, sb_select, sb_update

def seed_rich_data():
    print("--- SEEDING RICH MOCK DATA ---")
    
    # 1. Update Contratos
    print("Fetching contratos...")
    contratos = sb_select("contratos")
    c_map = {c.get("Contrato", c.get("contrato")): c for c in contratos}
    
    alpha = c_map.get("CT-2024-001")
    beta = c_map.get("CT-2025-002")
    gamma = c_map.get("CT-2025-003")
    
    if beta:
        sb_update("contratos", {"ID": beta["ID"]}, {"Status": "Atrasado"})
    if gamma:
        sb_update("contratos", {"ID": gamma["ID"]}, {"Status": "Atraso Crítico"})
        
    print("Updated contratos status.")

    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    yesterday_str = (today - timedelta(days=1)).strftime("%Y-%m-%d")

    # 2. Obras (Progress, delays)
    print("Seeding Obras...")
    if beta:
        sb_insert("obras", {
            "Data": date_str,
            "Contrato": "CT-2025-002",
            "Projeto": "Usina Solar Beta",
            "Cliente": beta.get("Cliente", "Minas Power"),
            "Previsto (%)": 18,
            "Realizado (%)": 15,
            "Comentario": "Atraso LP (Licença Prévia) - 21 dias. Fundações paradas.",
            "Categoria": "Usina Solo",
            "Tipo": "Solo"
        })
    
    if gamma:
        sb_insert("obras", {
            "Data": date_str,
            "Contrato": "CT-2025-003",
            "Projeto": "Usina Solar Gamma",
            "Cliente": gamma.get("Cliente", "Rio Renováveis"),
            "Previsto (%)": 80,
            "Realizado (%)": 68,
            "Comentario": "Inversores retidos no porto. Chuvas prejudicam escavação.",
            "Categoria": "Usina Solo",
            "Tipo": "Solo"
        })

    # 3. Financeiro (Fines, Budgets)
    print("Seeding Financeiro...")
    if beta:
        sb_insert("financeiro", {
            "Data": date_str,
            "Contrato": "CT-2025-002",
            "Projeto": "Usina Solar Beta",
            "Cliente": beta.get("Cliente", "Minas Power"),
            "Cockpit": "Medição",
            "Servico Contratado": "630000",
            "Multa": "12000",
            "Justificativa": "Multa de Take or Pay aplicada devido a atraso na Licença Prévia",
            "Categoria": "Serviço"
        })
    if gamma:
        sb_insert("financeiro", {
            "Data": date_str,
            "Contrato": "CT-2025-003",
            "Projeto": "Usina Solar Gamma",
            "Cliente": gamma.get("Cliente", "Rio Renováveis"),
            "Material Contratado": "1330000",
            "Material Realizado": "1450000", # Estouro de custo
            "Justificativa": "Aumento no custo de aço + aluguel extra de guindaste",
            "Categoria": "Material"
        })
        
    # 4. O&M (Performance Drop for Alpha)
    print("Seeding O&M...")
    if alpha:
        sb_insert("om", {
            "Data": date_str,
            "Contrato": "CT-2024-001",
            "Projeto": "Usina Solar Alpha",
            "Localiza\u00e7\u00e3o": alpha.get("Localiza\u00e7\u00e3o", alpha.get("Localiza\ufffdo", "São Paulo, SP")),
            "Geracao Prevista (kWh)": "200000",
            "Energia Injetada (kWh)": "190800", # 4.6% less
            "Valor Faturado": "148200",
            "Faturamento Liquido": "112000"
        })

    # 5. RDO (Weather and Port issues)
    print("Seeding RDO...")
    if gamma:
        import uuid
        sb_insert("rdo_cabecalho", {
            "ID_RDO": f"RDO-GAMMA-{yesterday_str}-{str(uuid.uuid4())[:6]}",
            "Data": yesterday_str,
            "Contrato": "CT-2025-003",
            "Projeto": "Usina Solar Gamma",
            "Turno": "Integral",
            "Condicao_Climatica": "Chuva Forte",
            "Houve_Interrupcao": "Sim",
            "Motivo_Interrupcao": "Chuva alagou área de fundação. Equipamentos parados.",
            "Houve_Acidente": "Não",
            "Observacoes": "Inversores continuam bloqueados na Receita Federal (Salvador)."
        })
        
    print("--- SEEDING COMPLETE ---")

if __name__ == "__main__":
    seed_rich_data()
