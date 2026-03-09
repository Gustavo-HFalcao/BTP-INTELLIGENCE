-- ========================================================================================
-- BOMTEMPO INTELLIGENCE: TEXT-TO-SQL AGENT DB SETUP
-- Criação das Remote Procedure Calls (RPCs) para operação segura da IA.
-- ATENÇÃO: Execute este script no SQL Editor do seu Supabase.
-- ========================================================================================

-- 1. FUNÇÃO: LER O ESQUEMA DO BANCO (GET SCHEMA CONTEXT)
-- Finalidade: Retorna a estrutura (tabelas e colunas) apenas das tabelas de negócio,
-- escondendo tabelas de autenticação ou logística de frota desnecessárias.
-- Isso restringe severamente a "janela de alucinação" do LLM no prompt.
CREATE OR REPLACE FUNCTION public.get_schema_context()
RETURNS TABLE(table_name text, column_name text, data_type text) 
LANGUAGE plpgsql
SECURITY DEFINER -- Roda com privilégios do criador da função (bypassa RLS de forma controlada apenas para estrutura)
SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    c.table_name::text, 
    c.column_name::text, 
    c.data_type::text
  FROM information_schema.columns c
  WHERE c.table_schema = 'public'
    -- Filtramos rigidamente apenas as tabelas que importam para o negócio da diretoria
    AND c.table_name IN (
        'contratos', 
        'financeiro', 
        'om', 
        'projetos', 
        'rdo_cabecalho', 
        'rdo_mao_obra', 
        'rdo_equipamentos', 
        'rdo_materiais', 
        'rdo_atividades'
    )
  ORDER BY c.table_name, c.ordinal_position;
END;
$$;


-- 2. FUNÇÃO: EXECUTAR QUERY DINÂMICA SEGURA (EXECUTE SAFE QUERY)
-- Finalidade: Isola a execução das consultas dinâmicas (SELECTs) geradas pela IA.
-- Tem uma camada primitiva de bloqueio contra DML/DDL (que também suportada 
-- pela camada de sqlparse em Python no backend).
CREATE OR REPLACE FUNCTION public.execute_safe_query(query_string text)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  result json;
BEGIN
  -- Defesa Básica em nível DB contra injeção destrutiva
  -- (O backend Reflex já fará a validação primária usando sqlparse)
  IF query_string ILIKE '%DROP %' 
  OR query_string ILIKE '%DELETE %' 
  OR query_string ILIKE '%UPDATE %' 
  OR query_string ILIKE '%INSERT %' 
  OR query_string ILIKE '%TRUNCATE %' 
  OR query_string ILIKE '%ALTER %' 
  OR query_string ILIKE '%GRANT %' THEN
    RAISE EXCEPTION 'Operação não permitida ("%"). O robô de IA possui acesso estritamente de Leitura (SELECT).', query_string;
  END IF;

  -- Impede consultas manipuladas terminadas com ponto e vírgula contendo comandos maliciosos engatados
  IF query_string LIKE '%;%' THEN
     RAISE EXCEPTION 'Operação rejeitada: Múltiplas instruções SQL ou terminador não permitido.';
  END IF;

  -- Executa o comando repassado e encapsula as linhas num Array JSON
  EXECUTE format('SELECT json_agg(t) FROM (%s) t', query_string) INTO result;
  
  -- Padroniza a ausência de dados como JSON array vazio
  IF result IS NULL THEN
    RETURN '[]'::json;
  END IF;
  
  RETURN result;
END;
$$;

-- Dá permissão aos perfis autenticados para chamar as funções livremente pela API
GRANT EXECUTE ON FUNCTION public.get_schema_context() TO authenticated;
GRANT EXECUTE ON FUNCTION public.execute_safe_query(text) TO authenticated;
