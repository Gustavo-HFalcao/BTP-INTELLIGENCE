import sys

filepath = r'c:\Users\Gustavo\bomtempo-dashboard\bomtempo\state\global_state.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

out = []
for i, line in enumerate(lines):
    out.append(line)
    if 'Eficiência de Entrega": f"{self.analytics_conclusao_rate}%",' in line:
        out.append(lines[i+1]) # the }
        out.append('         elif "rdo" in path:\n')
        out.append('              page_name = "Dashboard RDO Analytics"\n')
        out.append('              try:\n')
        out.append('                  from bomtempo.core.rdo_service import RDOService\n')
        out.append('                  from bomtempo.core.supabase_client import sb_select\n')
        out.append('                  rdos = RDOService.get_all_rdos(limit=200)\n')
        out.append('                  mo = sb_select("rdo_mao_obra", limit=1000) or []\n')
        out.append('                  eq = sb_select("rdo_equipamentos", limit=1000) or []\n')
        out.append('                  data = {\n')
        out.append('                      "Total de RDOs Emitidos": len(rdos),\n')
        out.append('                      "Obras Operando": len(set(r.get("Contrato") for r in rdos if r.get("Contrato"))),\n')
        out.append('                      "Profissionais em Campo": sum(int(r.get("Quantidade", 0) or 0) for r in mo),\n')
        out.append('                      "Registros de Equipamentos": len(eq),\n')
        out.append('                  }\n')
        out.append('              except Exception as e:\n')
        out.append('                  logger.warning(f"Erro KPI RDO: {e}")\n')
        out.append('                  data = {"Seção": "RDO Analytics", "Status": "Carregando RDOs..."}\n')
        
        # We copied i+1, so we should skip it on the next iteration
        lines[i+1] = ""

with open(filepath, 'w', encoding='utf-8') as f:
    for line in out:
        f.write(line)
print("PATCH_APPLIED")
