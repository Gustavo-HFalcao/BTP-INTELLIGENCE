---
title: Fuel Reimbursement Module Implementation Plan
author: Bomtempo Assistant
date: 2026-02-23
---

# Fuel Reimbursement Module Implementation Plan

This document outlines the architecture, database schema, and components required to implement the new Fuel Reimbursement Module. It is designed to be read and executed in a single shot by the development agent.

## User Review Required

*(No user review required at this stage)*

## Proposed Changes

### Database Layer

#### [MODIFY] Supabase Table: `fuel_reimbursements` (Verification Only)
The table `fuel_reimbursements` **already exists**. The implementation must **verify** if all fields from the specification are present and correct them if necessary, rather than creating the table from scratch. 

Required RLS (Row Level Security) Policies to verify/create:
- Users with the role `solicitacao_reembolso` must only be able to view and insert their own reimbursements.
- Managers/Admins can view all reimbursements.

```sql
-- Example verification/update for RLS
alter table fuel_reimbursements enable row level security;

create policy "Users can insert their own reimbursements"
  on fuel_reimbursements for insert
  with check (auth.uid() = user_id);

create policy "Users can view their own reimbursements"
  on fuel_reimbursements for select
  using (auth.uid() = user_id);
-- Note: Add policy for managers to see everything based on role
```

#### Storage Buckets (Verification Only)
The following buckets **already exist** in Supabase Storage. Verify they are accessible and configured correctly:
- `fuel_reimbursements_nf` 
- `fuel_reimbursements_pdfs`

---

### Backend Logic (Core)

#### [MODIFY] `bomtempo/core/ai_client.py`
Add support for vision API calls using the provided OpenAI API key.
- The environment configuration must use the provided key: `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`
- Add `analyze_image(image_url: str, prompt: str) -> dict` function.
- Configure prompt specific for fuel receipt extraction (returning JSON).

#### [NEW] `bomtempo/core/fuel_service.py`
Centralized service for fuel reimbursement logic (similar to `rdo_service.py`).
- `process_reimbursement(data, image_file)`: Main entry point.
- `_upload_receipt(image_file)`: Handle image upload to Supabase.
- `_analyze_receipt_ai(image_url)`: Call OpenAI Vision API.
- `_validate_data(user_data, ai_data)`: Implement the ±R$0.50 validation and internal consistency (liters * price == total).
- `_calculate_metrics(data)`: Calculate `km_per_liter`, `cost_per_km`, deviations.
- `generate_pdf(data)`: Generate professional PDF using ReportLab or an HTML-to-PDF library, matching the provided template structure.
- `_upload_pdf(pdf_path)`: Handle PDF upload to Supabase.
- `save_to_database(data)`: Final save to `fuel_reimbursements` table.

#### [MODIFY] `bomtempo/core/ai_context.py`
Update context generation to include fuel KPIs for the AI Chat.
- Fetch summary metrics from `fuel_reimbursements` (e.g., total spent, average km/l, flagged outliers).
- Append to the `get_dashboard_context` output.

---

### User Interface (Pages)

#### [NEW] `bomtempo/pages/reembolso_form.py`
Mobile-first form for users to request reimbursement.
- **Access Control:** Restricted to users with the `solicitacao_reembolso` role.
- **Data Filtering:** Users can only see and edit their own reimbursement requests (Benchmark this against the existing RDO module logic).
- Inputs: Placa, Tipo (select), Finalidade (select + text), Combustível (select), Litros, Valor/L, Valor Total, Data, Local.
- Inputs: KM Inicial, KM Final, Rota.
- Component: File upload for receipt image (camera/gallery).
- Flow: Submit -> `fuel_service.process_reimbursement` -> Show validation errors -> Success State (PDF generated).

#### [NEW] `bomtempo/pages/reembolso_dashboard.py`
Desktop-focused C-Level dashboard.
- **Financial KPIs**: Total reimbursed (period), avg ticket, avg cost/KM, projection, % outliers.
- **Operational KPIs**: Fleet avg KM/L, efficiency timeline chart, heatmap/ranking of stations & prices.
- **Anomalies Table/Alerts**: 
  - 🔴 KM/L < 30% fleet avg
  - 🟡 Suspicious frequency (2 fill-ups < 6h)
  - 🟠 High price alerts (+15% regional avg)
  - Reliability score per user.
- **List View**: Table of requests with status, quick PDF view button, and AI insight badge.

#### [MODIFY] `bomtempo/bomtempo.py` or Routing logic
Add new routes `/reembolso` (form) and `/reembolso-dash` (dashboard).

#### [MODIFY] `bomtempo/components/sidebar.py` (or navigation equivalent)
Add links to the new Fuel Reimbursement pages.

---

## Verification Plan

### Automated Tests
*   Ensure Supabase connection can write to the new table and buckets.
*   Unit test the AI validation logic (e.g., simulating a value mismatch of R$0.60 vs R$0.49 to test the tolerance).
*   Unit test the metric calculations (KM/L, Cost/KM).

### Manual Verification
1.  **Form Submission:** Go to the `/reembolso` page on a mobile device (or simulated mobile view). Fill out valid data, upload a test fuel receipt image. Verify AI reads it, validates it, generates the PDF, and saves it to the database.
2.  **Validation Rejection:** Upload an unreadable image or submit data that directly conflicts with the image (e.g., type R$ 1000 but receipt says R$ 100). Verify appropriate error messages appear as specified.
3.  **Dashboard View:** Go to `/reembolso-dash`. Verify KPIs calculate correctly based on the dummy/test data inserted. Check that anomaly alerts trigger correctly for outliers.
4.  **PDF Review:** Open the generated PDF from the storage bucket and verify it matches the structural layout requested (Company Logo, Indicators, AI Insight box, attached image).
