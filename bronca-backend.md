Audit de Performance — Backend Bomtempo
CRÍTICO — Travamento visível / spinner que nunca limpa
#	Onde	Problema
C-1	rdo_state.py ~1489	N+1 no execute_submit: loop sobre cada atividade extra dispara 3 chamadas HTTP sequenciais (SELECT + UPDATE + INSERT). Com 5 atividades extras = 15 round-trips antes de liberar o "Enviando…"
C-2	hub_state.py ~1067	N+1 no recalculate_cron_dates: 1 UPDATE por atividade em loop sequencial. Com 50 atividades = 50 HTTP calls bloqueando o bg event inteiro
C-3	global_state.py ~490	send_reset_link não é background=True — faz sb_select + sb_insert + SMTP bloqueando o state lock. Todo WebSocket fica parado até o e-mail enviar
C-4	usuarios_state.py ~178	load_users/load_roles são sync — chamam httpx blocking direto no event loop, travando todos os usuários conectados
C-5	usuarios_state.py ~352	save_user não é background=True — httpx blocking + load_users() imediatamente depois = dois DB calls bloqueando o event loop
ALTO — Lentidão perceptível
#	Onde	Problema
H-1	global_state.py ~240	sb_select + _extract_document_text (download HTTP + parse PDF) rodando dentro do state lock no stream_chat_bg — bloqueia o lock enquanto baixa documentos
H-2	global_state.py ~1668	force_refresh_data é def sync — chama DataLoader.load_all() bloqueando o event loop por 1-2s
H-3	fuel_service.py ~343	Dois SELECT limit=500 completos em toda tabela para calcular média de desvio — por submit. À medida que a tabela cresce, fica progressivamente mais lento, e vai silenciosamente cortar em 500 linhas
H-4	edit_state.py ~713	CSV upload: 1 HTTP call por linha sequencialmente. 200 linhas × 50ms = 10s de spinner
H-5	hub_state.py ~476	5+ @rx.var com loops O(n²) re-executados a cada render (qualquer mudança de estado). gantt_rows, cron_display_rows, cron_forecast_rows, cron_kpi_dashboard
H-6	rdo_state.py ~727	asyncio.sleep(1.2) hardcoded antes de cada upload de foto — 3 fotos = 3.6s extras desnecessários
MÉDIO — Ineficiências
#	Onde	Problema
M-1	supabase_client.py ~165	SELECT * em tudo — sem suporte a selecionar colunas. Payload desnecessariamente grande
M-2	global_state.py ~230	get_schema_context RPC chamada em todo chat message — poderia cachear por 5 min
M-3	hub_state.py ~200	_log_schedule_diff_async: 1 INSERT por campo alterado — poderia ser 1 bulk insert
M-4	reembolso_state.py ~590	check_duplicate_hash (httpx blocking) direto em async def sem run_in_executor
M-5	edit_state.py ~240	Schema probe (SELECT limit=1) antes de cada load_table — poderia ser cacheado
M-6	supabase_client.py ~402	AsyncClient singleton sem lock — duas coroutines simultâneas podem criar dois clientes (leak)
M-7	vários	asyncio.get_event_loop() deprecated em Python 3.10+ — usar get_running_loop()
Como quer prosseguir?
As mais impactantes para o usuário no dia-a-dia são:

C-1 + C-2 — N+1 loops no RDO submit e no recalculate_cron (transformar em asyncio.gather / bulk)
C-3 + C-4 + C-5 — Módulo de usuários e reset de senha bloqueando o event loop (virar background events)
H-4 — CSV upload bulk (chunks de 100 por POST ao invés de 1 por linha)
H-5 — Mover os @rx.var caros do cronograma para vars calculadas só quando os dados mudam
Posso atacar em ordem de impacto, ou você prefere focar em algum módulo específico primeiro?