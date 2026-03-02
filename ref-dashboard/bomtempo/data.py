
# Dados mockados para a aplicação

contracts = [
    {"projetoInicio": '2024-09-01', "contrato": 'BOM010-24', "cliente": 'Escola A', "terceirizado": 'Empresa C', "localizacao": 'Recife, PE', "value": 2500000, "status": 'Em Execução', "progress": 45, "prazoContratual": '120 dias', "ordemServico": 'OS-1092', "potencia": '100 kWp', "terminoEstimado": '2025-01-15'},
    {"projetoInicio": '2024-10-15', "contrato": 'BOM011-24', "cliente": 'Hospital B', "terceirizado": 'Empresa D', "localizacao": 'Salvador, BA', "value": 4800000, "status": 'Em Execução', "progress": 12, "prazoContratual": '200 dias', "ordemServico": 'OS-2044', "potencia": '350 kWp', "terminoEstimado": '2025-05-30'},
    {"projetoInicio": '2024-11-01', "contrato": 'BOM012-24', "cliente": 'Shopping C', "terceirizado": 'Empresa E', "localizacao": 'Fortaleza, CE', "value": 1200000, "status": 'Suspenso', "progress": 5, "prazoContratual": '90 dias', "ordemServico": 'OS-3011', "potencia": '75 kWp', "terminoEstimado": '2025-02-28'}
]

activities = [
    {"id": i, "fase": f, "atividade": f"Etapa Técnica {i+1}", "critico": i % 3 == 0, "conclusao": 100 if i < 3 else (50 if i == 3 else 0)}
    for i, f in enumerate(['Planejamento', 'Civil', 'Estrutura', 'Elétrica', 'Montagem', 'Comissionamento', 'Homologação', 'Entrega'])
]

financials = [
    {"data": '2024-09-01', "cockpit": 'Contrato', "marco": 'Entrada', "categoria": 'Equipamentos', "servicoContratado": 10000, "materialContratado": 150000, "servicoRealizado": 10000, "materialRealizado": 150000},
    {"data": '2024-09-15', "cockpit": 'Terceirizado', "marco": 'Medição 1', "categoria": 'Civil', "servicoContratado": 50000, "materialContratado": 20000, "servicoRealizado": 25000, "materialRealizado": 10000},
    {"data": '2024-10-01', "cockpit": 'Operação', "marco": 'Manutenção', "categoria": 'O&M', "servicoContratado": 5000, "materialContratado": 0, "servicoRealizado": 0, "materialRealizado": 0}
]

construction_records = [
    {"categoria": 'Civil', "previsto": 1.0, "realizado": 1.0, "comentario": 'Concluído'},
    {"categoria": 'Estrutura Metálica', "previsto": 0.8, "realizado": 0.8, "comentario": 'Avançado'},
    {"categoria": 'Módulo Solar', "previsto": 0.6, "realizado": 0.4, "comentario": 'Atraso na entrega'},
    {"categoria": 'Elétrica CC', "previsto": 0.4, "realizado": 0.2, "comentario": ''},
    {"categoria": 'Inversor', "previsto": 0.2, "realizado": 0.0, "comentario": ''},
    {"categoria": 'Elétrica CA', "previsto": 0.1, "realizado": 0.0, "comentario": ''},
]

om_records = [
    {
        "data": f"2024-{i+1:02d}-01",
        "geracaoPrevista": 10000 + (i * 100),
        "energiaInjetada": 9500 + (i * 120) if i < 9 else 0,
        "kwhAcumulado": 1500 * (i + 1) if i < 9 else 0,
        "fatLiquido": 1100 + (i * 50) if i < 9 else 0,
        "mes": ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"][i]
    } for i in range(12)
]
