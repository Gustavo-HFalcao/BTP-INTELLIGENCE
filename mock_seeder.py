import os
from supabase import create_client

def main():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        from dotenv import load_dotenv
        load_dotenv()
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
    if not url or not key:
        print("Missing SUPABASE credentials")
        return

    supabase = create_client(url, key)

    projects = supabase.table("projects").select("id, status").execute()
    for p in projects.data:
        # Mocking world-class AI summary and premium image
        supabase.table("projects").update({
            "status": "Em Andamento" if p.get("status") in ["Ativo", None] else p.get("status"),
            "ai_daily_summary": "Análise da IA: O ritmo de evolução estrutural encontra-se 5% acima do baseline do cronograma. Condições meteorológicas favoráveis autorizam a continuidade do plano de concretagem da fundação. Recomendação: Manter o efetivo atual sem alterações.",
            "foto_destaque_url": "https://images.unsplash.com/photo-1541888086225-f674ce88ec30?q=80&w=800&auto=format&fit=crop"
        }).eq("id", p["id"]).execute()

    print(f"Updated {len(projects.data)} projects with mock data.")

    # Insert Project Records
    if len(projects.data) > 0:
        proj_id = projects.data[0]["id"]
        users = supabase.table("login").select("id").limit(1).execute()
        if users.data:
            user_id = users.data[0]["id"]
            
            # Check if records already exist to prevent dupes
            existing = supabase.table("project_records").select("id").eq("project_id", proj_id).execute()
            if len(existing.data) == 0:
                supabase.table("project_records").insert([
                    {
                        "project_id": proj_id, 
                        "author_id": user_id, 
                        "content": "Reunião executiva de alinhamento com a diretoria técnica concluída. Escopo da fase 2 aprovado sem ressalvas.", 
                        "category": "meeting"
                    },
                    {
                        "project_id": proj_id, 
                        "author_id": user_id, 
                        "content": "Detecção de Risco [EPI]: Identificada ausência de capacete por colaborador terceirizado na Zona Sul. Orientação realizada e repassada à coordenação.", 
                        "category": "issue"
                    }
                ]).execute()
                print("Inserted mock project records for social feed.")

if __name__ == "__main__":
    main()
