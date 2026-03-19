import json
from bomtempo.core.supabase_client import sb_rpc
from bomtempo.core.logging_utils import get_logger

logger = get_logger(__name__)

# --- Tool Definitions for OpenAI API ---

AI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_sql",
            "strict": True,
            "description": (
                "Executa uma consulta SQL SELECT no banco de dados Supabase. "
                "Use para buscar dados reais de contratos, financeiro, obras, RDO, OM, etc. "
                "NUNCA use sem antes chamar get_schema_info para conhecer as colunas disponíveis."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Query SQL SELECT válida. Ex: SELECT contrato, valor_total FROM financeiro LIMIT 20"
                    }
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_schema_info",
            "strict": True,
            "description": (
                "Retorna as tabelas e colunas disponíveis no banco de dados. "
                "Sempre chame antes de usar execute_sql para conhecer os nomes exatos de tabelas e colunas."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_chart_data",
            "strict": True,
            "description": (
                "Renderiza um gráfico visual interativo inline no chat. "
                "Use SEMPRE que o usuário pedir gráfico, comparação visual, chart ou visualização. "
                "Fluxo obrigatório: 1) get_schema_info → 2) execute_sql → 3) generate_chart_data. "
                "chart_type: 'bar' para comparações entre categorias, "
                "'area' para evolução temporal (séries mensais/semanais), "
                "'pie' para distribuição proporcional (% por categoria)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "enum": ["area", "bar", "pie"],
                        "description": "Tipo do gráfico.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Título descritivo. Ex: 'Faturamento por Contrato — 1º Sem 2025'",
                    },
                    "data": {
                        "type": "array",
                        "description": "Pontos do gráfico. Cada item deve ter 'name' (string) e 'value' (número).",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Label do ponto (eixo X ou fatia da pizza).",
                                },
                                "value": {
                                    "type": "number",
                                    "description": "Valor numérico do ponto.",
                                },
                            },
                            "required": ["name", "value"],
                            "additionalProperties": False,
                        },
                    },
                    "value_prefix": {
                        "type": "string",
                        "description": "Prefixo para o tooltip. Use 'R$' para moeda, '%' para percentual, '' para número puro.",
                    },
                },
                "required": ["chart_type", "title", "data", "value_prefix"],
                "additionalProperties": False,
            },
        },
    },
]

# --- Tool Execution Logic ---

_BLOCKED_KEYWORDS = {"drop", "delete", "update", "insert", "truncate", "alter", "grant", "revoke", "create"}


def execute_tool(name: str, args: dict):
    """Executes the tool logic based on the tool name and arguments."""
    try:
        if name == "execute_sql":
            query = args.get("query", "").strip()
            if not query:
                return json.dumps({"error": "Query não fornecida."})
            # Guard Python-side antes de chegar no Supabase
            first_word = query.split()[0].lower()
            if first_word in _BLOCKED_KEYWORDS:
                return json.dumps({"error": f"Operação '{first_word.upper()}' não permitida. Apenas SELECT."})
            logger.info(f"🛠️ Tool: execute_sql → {query[:120]}")
            result = sb_rpc("execute_safe_query", {"query_string": query})
            return json.dumps(result or [])
        
        elif name == "get_schema_info":
            logger.info("🛠️ Tool: get_schema_info")
            result = sb_rpc("get_schema_context")
            return json.dumps(result or [])
            
        elif name == "generate_chart_data":
            chart_type = args.get("chart_type", "bar")
            data = args.get("data", [])
            title = args.get("title", "")
            value_prefix = args.get("value_prefix", "")
            # Retorna JSON com marcador especial que o loop agêntico detecta e injeta na mensagem
            return json.dumps({
                "__chart__": True,
                "chart_type": chart_type,
                "title": title,
                "value_prefix": value_prefix,
                "data": data,
            })
            
        return f"Ferramenta {name} não encontrada."
    except Exception as e:
        logger.error(f"Erro ao executar tool {name}: {e}")
        return f"Erro na execução da ferramenta: {str(e)}"
