"""
End-to-end PDF test: HTML generation -> Playwright render -> Supabase upload.
Run with: python test_pdf_e2e.py
"""
# -*- coding: utf-8 -*-
import sys
import io

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from pathlib import Path

# ── Mock data ─────────────────────────────────────────────────────────────────

RDO_DATA = {
    "contrato": "TEST-HTML-001",
    "data": "2026-02-24",
    "projeto": "Usina Solar Norte",
    "cliente": "Energia Brasil S.A.",
    "localizacao": "Recife, PE",
    "clima": "Parcialmente nublado",
    "turno": "Manha",
    "hora_inicio": "07:00",
    "hora_termino": "12:00",
    "houve_interrupcao": True,
    "motivo_interrupcao": "Chuva moderada na primeira hora do turno",
    "observacoes": (
        "Servicos externos suspensos por 45 min. Equipe realocada para montagem interna.\n"
        "Retomada as 07:45 com normalizacao climatica."
    ),
    "mao_obra": [
        {"funcao": "Eletricista Senior", "quantidade": 3, "obs": "Instalacao paineis Bloco A"},
        {"funcao": "Auxiliar de Obra", "quantidade": 6, "obs": "Suporte geral"},
        {"funcao": "Encarregado", "quantidade": 1, "obs": "Supervisao turno manha"},
    ],
    "equipamentos": [
        {"descricao": "Guindaste Tadano 50t", "quantidade": 1},
        {"descricao": "Plataforma Elevatoria 12m", "quantidade": 2},
        {"descricao": "Gerador 150kVA", "quantidade": 1},
    ],
    "atividades": [
        {"atividade": "Instalacao paineis fotovoltaicos - Bloco A (linhas 1-4)", "percentual": 65},
        {"atividade": "Cabeamento DC string box -> inversor", "percentual": 40},
        {"atividade": "Fixacao estrutura suporte aluminio", "percentual": 80},
    ],
    "materiais": [
        {"descricao": "Painel Solar 550W", "quantidade": 48, "unidade": "un"},
        {"descricao": "Cabo DC 6mm2", "quantidade": 200, "unidade": "m"},
        {"descricao": "Parafuso inox M8", "quantidade": 400, "unidade": "un"},
    ],
}

FUEL_DATA = {
    "submitted_by": "gustavo",
    "combustivel": "Gasolina",
    "litros": 45.5,
    "valor_litro": 5.89,
    "valor_total": 267.995,
    "km_inicial": 123456,
    "km_final": 123876,
    "km_driven": 420.0,
    "km_per_liter": 9.23,
    "cost_per_km": 0.638,
    "rota": "Recife (PE) -> Caruaru (PE) -> Recife (PE)",
    "finalidade": "Visita tecnica obra Caruaru",
    "cidade": "Recife",
    "estado": "PE",
    "data_abastecimento": "2026-02-24",
    "ai_insight_text": (
        "Nota fiscal valida. Total R$267,99 consistente com 45,5L x R$5,89. "
        "Eficiencia de 9,23 km/L dentro da media da frota. Sem irregularidades detectadas."
    ),
    "ai_verified": True,
}


def sep(title=""):
    print(f"\n{'=' * 60}")
    if title:
        print(f"  {title}")
        print("=" * 60)


def ok(msg):
    print(f"[OK] {msg}")


def info(msg):
    print(f"     {msg}")


# ─────────────────────────────────────────────────────────────────────────────
# RDO FLOW
# ─────────────────────────────────────────────────────────────────────────────
sep("FLUXO RDO")

from bomtempo.core.rdo_service import RDOService

# 1. Preview PDF
print("\nSTEP 1 -- Gerando PDF PREVIEW (HTML -> Playwright/Edge)")
pdf_path_prev, _ = RDOService.generate_pdf(RDO_DATA, is_preview=True)
assert pdf_path_prev and Path(pdf_path_prev).exists(), f"PDF preview nao gerado: {pdf_path_prev}"
kb = Path(pdf_path_prev).stat().st_size // 1024
ok(f"PDF PREVIEW: {Path(pdf_path_prev).name}  ({kb} KB)")

# 2. Save to DB
print("\nSTEP 2 -- Salvando no Supabase (rdo_cabecalho + sub-tabelas)")
id_rdo = RDOService.save_to_database(RDO_DATA, submitted_by="gustavo")
assert id_rdo, "save_to_database retornou None"
ok(f"DB salvo: {id_rdo}")

# 3. Final PDF with ID
print("\nSTEP 3 -- Gerando PDF FINAL com id_rdo")
pdf_path_final, local_url = RDOService.generate_pdf(RDO_DATA, is_preview=False, id_rdo=id_rdo)
assert pdf_path_final and Path(pdf_path_final).exists()
kb = Path(pdf_path_final).stat().st_size // 1024
ok(f"PDF FINAL: {Path(pdf_path_final).name}  ({kb} KB)")
info(f"local url: {local_url}")

# 4. Upload to Storage
print("\nSTEP 4 -- Upload para Storage (bucket: rdo-pdfs)")
storage_url = RDOService.upload_pdf_to_storage(pdf_path_final, id_rdo)
assert storage_url, "upload retornou URL vazia"
ok(f"Uploaded!")
info(f"url: {storage_url}")

# 5. Update DB
print("\nSTEP 5 -- Atualizando pdf_path no rdo_cabecalho")
updated = RDOService.update_pdf_info(id_rdo, storage_url)
assert updated, "update_pdf_info retornou False"
ok(f"pdf_path atualizado")

sep("RDO COMPLETO")
print(f"  ID:  {id_rdo}")
print(f"  URL: {storage_url}")

# ─────────────────────────────────────────────────────────────────────────────
# FUEL REIMBURSEMENT FLOW
# ─────────────────────────────────────────────────────────────────────────────
sep("FLUXO REEMBOLSO")

from bomtempo.core.fuel_service import FuelService

# 1. Save to DB (get id_fr first — same order as reembolso_state)
print("\nSTEP 1 -- Salvando no Supabase (fuel_reimbursements)")
id_fr = FuelService.save_to_database(FUEL_DATA, submitted_by="gustavo")
assert id_fr, "save_to_database retornou None"
ok(f"DB salvo: id_fr = {id_fr}")

# 2. Generate PDF
print("\nSTEP 2 -- Gerando PDF (HTML -> Playwright/Edge)")
pdf_path_fr, _ = FuelService.generate_pdf(FUEL_DATA, id_fr=id_fr)
assert pdf_path_fr and Path(pdf_path_fr).exists(), f"PDF FR nao gerado: {pdf_path_fr}"
kb = Path(pdf_path_fr).stat().st_size // 1024
ok(f"PDF: {Path(pdf_path_fr).name}  ({kb} KB)")

# 3. Upload PDF to Storage
print("\nSTEP 3 -- Upload para Storage (bucket: reembolso-docs)")
fr_pdf_url = FuelService.upload_pdf_to_storage(pdf_path_fr, id_fr)
assert fr_pdf_url, "upload PDF FR retornou URL vazia"
ok(f"PDF uploaded!")
info(f"url: {fr_pdf_url}")

sep("REEMBOLSO COMPLETO")
print(f"  ID:  {id_fr}")
print(f"  URL: {fr_pdf_url}")

sep("TODOS OS TESTES PASSARAM")
print("  RDO + Reembolso -- HTML/Playwright PDF + Supabase upload funcionando")
print("=" * 60)
