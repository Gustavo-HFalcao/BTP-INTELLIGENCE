📑 Plano de Implantação: Módulo RDO Antigravity (Next-Gen)
1. Visão Geral do Produto
O objetivo é replicar a funcionalidade de "Comprovação de Serviço" do Auvo, adicionando uma camada de inteligência (IA) que transforma fotos e textos brutos em relatórios executivos acionáveis, eliminando o trabalho manual de análise do gestor.

2. Arquitetura Técnica (Stack Python + Reflex)
2.1 Estrutura de Dados (Backend)
Utilizaremos SQLAlchemy para modelar a persistência, garantindo rastreabilidade total.

Entidade Obra:

id, nome, cliente_id, coordenadas_alvo (Point), raio_tolerancia (metros).

Entidade RDO_Master:

uuid (PK), status (Aberto/Finalizado/Cancelado), mestre_id.

checkin_data (JSON: timestamp, lat, long, device_info).

checkout_data (JSON: timestamp, lat, long, signature_url).

ai_summary (Texto gerado pela IA).

Entidade RDO_Evidencia:

rdo_id (FK), foto_url, timestamp_extracao, gps_extraido, legenda_mestre, analise_vision.

2.2 Frontend Mobile-First (Reflex)
O Reflex rodará como um PWA (Progressive Web App) para garantir acesso rápido no celular.

State Management (rx.State): O estado do RDO deve ser persistido em tempo real. Se o navegador fechar, o rdo_id ativo deve ser recuperado do banco ou local storage ao reabrir.

3. Replicação Detalhada das Features (O "Padrão Auvo")
3.1 Check-in & Geofencing
Lógica: Ao clicar em "Iniciar RDO", o sistema captura a posição via rx.geolocation.

Cálculo de Distância: Implementar a fórmula de Haversine no backend para validar se o usuário está a menos de X metros da obra cadastrada.

Bloqueio: Se estiver fora do raio, o RDO permite o preenchimento, mas marca o relatório com uma Tag de Alerta Vermelha (Potencial Fraude).

3.2 Input de Fotos com "Proof of Origin"
Para cada foto enviada:

Extração de Metadados: Usar a biblioteca Pillow (PIL) em Python para ler os dados EXIF da imagem.

Reverse Geocoding: Enviar as coordenadas para a API (Google Maps ou OpenStreetMap) para obter o endereço textual (Rua, Bairro, CEP).

Marca d'Água Dinâmica: Processar a imagem para inserir um rodapé semi-transparente com a data, hora e endereço, tornando a foto um documento oficial e imutável.

3.3 Assinatura Digital
Utilizar um componente de Canvas customizado no Reflex.

O mestre de obras assina com o dedo. O sistema salva o arquivo como assinatura_rdo_{uuid}.png.

Validação: A assinatura só é liberada se todos os campos obrigatórios (Clima, Efetivo, Atividades) estiverem preenchidos.

4. O Diferencial Antigravity (IA & Analytics)
4.1 Módulo Vision (Auditoria Automática)
Cada foto passará pelo GPT-4o ou Gemini 1.5 Flash com o seguinte prompt:

"Analise esta foto de obra. 1. Identifique se há uso de capacete e colete. 2. Descreva brevemente a atividade (ex: concretagem, alvenaria, elétrica). 3. Avalie a organização do canteiro (Limpo/Sujo). 4. Compare com a legenda do usuário: '{user_caption}' e aponte discrepâncias."

4.2 Resumo Executivo para WhatsApp
Ao finalizar o RDO, a IA lê todo o conteúdo (Clima + Fotos + Texto do Mestre) e gera um JSON para o webhook do WhatsApp:

Headline: Resumo de 1 frase (ex: "Dia produtivo: Laje do 2º andar concluída").

Riscos: Apontar possíveis atrasos baseados no clima ou falta de pessoal.

Sugestão de Próximo Passo: "Revisar estoque de cimento para amanhã".

5. Plano de Implementação Passo a Passo
Semana 1: Fundação e Dados
[ ] Configurar as tabelas no PostgreSQL.

[ ] Criar a tela de "Seleção de Obra" e o botão de "Check-in" com geolocalização.

[ ] Implementar o salvamento de rascunho automático (Drafting).

Semana 2: O Motor de Evidências
[ ] Criar o componente de upload múltiplo de fotos.

[ ] Desenvolver o worker Python que extrai GPS/Data e aplica a marca d'água.

[ ] Integrar API de Mapas para exibir o "Mini Map" ao lado de cada foto no dashboard.

Semana 3: O Cérebro (IA)
[ ] Integrar o pipeline de Vision (Processamento assíncrono para não travar o app).

[ ] Criar o gerador de PDF via WeasyPrint seguindo o layout do Auvo (porém com design moderno).

[ ] Implementar o módulo de assinatura manual.

Semana 4: Distribuição e Dashboard
[ ] Configurar o Webhook de saída para WhatsApp (Evolution API).

[ ] Criar o Dashboard do Gestor no Reflex para visualizar o histórico de RDOs com filtros de "Anomalias de GPS" ou "Falta de EPI".

6. Riscos e Mitigações
Falta de Sinal: Implementar um sistema de fila. O usuário preenche tudo, e o app tenta reenviar os dados a cada 5 minutos até obter sucesso.

Bateria: O uso constante de GPS consome bateria. O app só deve requisitar a localização no Check-in, no momento da Foto e no Checkout.