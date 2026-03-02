import os
from dotenv import load_dotenv
from bomtempo.core.data_loader import DataLoader
from bomtempo.core.ai_context import AIContext
from bomtempo.core.ai_client import AIClient

load_dotenv()

def test_ai():
    loader = DataLoader()
    data = loader.load_all()

    context_str = AIContext.get_dashboard_context(data)
    
    print("\n--- AI CONTEXT STRING ---")
    print(context_str[:1500] + "...\n" + context_str[-1000:] if len(context_str) > 2500 else context_str)
    
    print("\n--- QUERYING KIMI AI ---")
    client = AIClient()
    
    prompt = f"""
Contexto do Dashboard:
{context_str}

Por favor, faça uma análise crítica dos 3 contratos atuais (supondo que você seja um diretor executivo) 
e conte uma história focada em Gestão de Riscos, Clima e Financeiro. Seja direto. Aja como um consultor sênior.
"""
    
    messages = [
        {"role": "system", "content": "Você é um consultor executivo sênior."},
        {"role": "user", "content": prompt}
    ]
    
    response = client.query(messages)
    print("\n--- AI RESPONSE GENERATED ---")
    with open("ai_insight.md", "w", encoding="utf-8") as f:
        f.write(response)
    print("Saved to ai_insight.md")

if __name__ == "__main__":
    test_ai()
