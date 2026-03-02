"""
Popula a coluna 'fase_macro' na tabela projetos do Supabase.

Pré-requisito: rodar no Supabase SQL Editor:
    ALTER TABLE projetos ADD COLUMN IF NOT EXISTS fase_macro TEXT;

Então rodar: python scripts/populate_fase_macro.py
"""

from bomtempo.core.supabase_client import sb_select, sb_update

FASE_MACRO_MAP = {
    "1": "Projeto Básico",
    "2": "Licenciamento",
    "3": "Aprovações",
    "4": "Infraestrutura",
    "5": "Montagem Estrutural",
    "6": "Instalação Elétrica",
    "7": "Comissionamento",
    "8": "Conexão",
}


def main():
    print("Carregando projetos do Supabase...")
    rows = sb_select("projetos", limit=1000)
    if not rows:
        print("Nenhuma linha encontrada.")
        return

    print(f"{len(rows)} linhas encontradas.")
    ok = 0
    skip = 0

    for r in rows:
        row_id = r.get("ID")
        fase = str(r.get("Fase", "")).strip()

        try:
            prefix = str(int(float(fase)))
        except (ValueError, TypeError):
            print(f"  SKIP id={row_id} fase={fase!r} (não numérico)")
            skip += 1
            continue

        macro = FASE_MACRO_MAP.get(prefix)
        if not macro:
            print(f"  SKIP id={row_id} fase={fase!r} (prefix={prefix!r} sem mapeamento)")
            skip += 1
            continue

        success = sb_update("projetos", {"ID": row_id}, {"fase_macro": macro})
        if success:
            print(f"  ✅ id={row_id:4}  Fase {fase:4} → {macro}")
            ok += 1
        else:
            print(f"  ❌ id={row_id:4}  Fase {fase:4} → UPDATE FALHOU")
            skip += 1

    print(f"\nConcluído: {ok} atualizados, {skip} ignorados.")


if __name__ == "__main__":
    main()
