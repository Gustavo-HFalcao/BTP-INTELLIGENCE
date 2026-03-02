# Centro de Custos da Aplicação (Dashboard Bomtempo)

Para profissionalizar a aplicação e sair do modelo *freemium* (garantindo estabilidade, disponibilidade 24/7 sem "dormir", backups automáticos e performance), precisamos estruturar nosso **Centro de Custos Operacionais (OPEX)**. 

Os custos de SaaS e nuvem são divididos em duas linhas principais: **Custos Fixos de Infraestrutura** e **Custos Variáveis (por uso e por cliente)**.

---

## 1. Custos Fixos Mensais (Infraestrutura Base)
Estes são os custos fundamentais para manter a plataforma no ar de forma rápida, segura e escalável, independentemente de você ter 1 ou 100 clientes.

| Serviço / Componente | O que resolve | Plano Recomendado | Custo Mensal (Aprox. USD) | Custo Mensal (Aprox. BRL)* |
| :--- | :--- | :--- | :--- | :--- |
| **Supabase (DB + Auth)** | Banco de Dados PostgreSQL, Autenticação e Storage sem pausas automáticas (*cold starts*). Backups diários. | **Pro Tier** | $ 25.00 | R$ 140,00 |
| **Hospedagem Front/Back**<br>*(Fly.io ou Reflex Deploy)* | Servidores 24/7 para rodar o Python/Reflex de forma rápida. Evita quedas quando o uso sobe. | **Hobby ou Pro / VM Dedicada** | $ 10.00 a $ 15.00 | R$ 55,00 a R$ 85,00 |
| **Domínio Customizado** | URL profissional (ex: `app.bomtempo.com.br`). Custo anual diluído. | **N/A** (Anual ~$15) | $ 1.25 | R$ 7,00 |
| **E-mail Transacional**<br>*(Resend ou SendGrid)* | Disparo de e-mails para reset de senha, convites, envio de relatórios. | **Free** (Até 3.000 emails/mês) | $ 0.00 | R$ 0,00 |
| **Integração de Dados**<br>*(Make, Zapier ou Pipefy limit)* | Se houver consumo complexo extra, além do que o script Python já faz. | Pode ser interno via CRON/Python | $ 0.00 | R$ 0,00 |
| **Subtotal Fixo:** | | | **~$ 36.25 / mês** | **~R$ 202,00 a R$ 232,00 / mês** |

---

## 2. Custos Variáveis por Cliente (Variável / Escalonável)
Estes são os custos associados especificamente ao uso da plataforma. Quanto mais análise um cliente processar, mais esse custo sobe (proporcionalmente).

| Componente | Cálculo / Dinâmica | Custo Estimado por Cliente Ativo / Mês (BRL) |
| :--- | :--- | :--- |
| **LLMs (OpenAI API / Kimi AI API)** | Cobrança por token. O consumo ocorre durante geração de relatórios de IA, classificações de texto ou consultas no dashboard. (*O consumo de IA para painéis e análises não-interativas repetitivas tende a ser baixíssimo*). | **~R$ 2,50 a R$ 10,00** |
| **Armazenamento de Dados Adicionais** | O Supabase Pro já possui *8GB de Database* e *100GB de Storage de imagens/arquivos*. Você não pagará um centavo a mais até ultrapassar esse limite. 8GB de texto suportam o histórico de dezenas de clientes por muito tempo. | **R$ 0,00** (para os primeiros ~100+ clientes) |
| **Custos de Rede / Egress (Trafego)** | Tráfego de download de dados para o navegador do cliente. Os pacotes base já cobrem a maioria das aplicações até haver milhares de visitas longas por mês. | **R$ 0,00** (inicial) |
| **Subtotal Variável Otimizado:** | | **~R$ 2,50 a R$ 10,00 / mês / cliente** |

---

## 3. Projeção de Cenários Operacionais

### Cenário A: Início (2 Clientes Ativos)
* **Custo Fixo Base:** R$ 202,00
* **Variável (2 clientes x R$ 7,00):** R$ 14,00
* **Custo Operacional Total:** **R$ 216,00 / mês**
* **Custo por conta:** R$ 108,00 / cliente

### Cenário B: Tração (10 Clientes Ativos)
* **Custo Fixo Base:** R$ 202,00
* **Variável (10 clientes x R$ 7,00):** R$ 70,00
* **Custo Operacional Total:** **R$ 272,00 / mês**
* **Custo por conta:** **R$ 27,20 / cliente** (A economia de escala entra aqui)

### Cenário C: Crescimento (50 Clientes Ativos)
* Neste estágio, você pode precisar fazer um *upgrade* ou adicionar mais máquinas no Fly.io / Reflex. (+ R$ 100 de servidor, totalizando R$ 302 de fixo).
* **Custo Fixo Escalado:** R$ 302,00
* **Variável (50 clientes x R$ 7,00):** R$ 350,00
* **Custo Operacional Total:** **R$ 652,00 / mês**
* **Custo por conta:** **R$ 13,04 / cliente**

*(Nota técnica: Cotações baseadas no Dólar aproximado a R$ 5,60)*

---

## Próximos Passos Obrigatórios para "Profissionalizar"

1. **Fazer o Upgrade do Supabase para o Tier Pro ($25/mês)**
   * **Por quê?** Atualmente, no plano Free, se o banco não receber conexões por 7 dias, ele entra em modo "Idling" (hibernação). Demora a acordar e quebra a experiência do usuário. O projeto Pro nunca dorme.
   * Você ganha garantias (SLA), Backups diários e recuperação Point-in-Time, vital contra perda acidental de dados de clientes.

2. **Garantir Limites Físicos de Uso nas APIs (Rate Limits)**
   * No dashboard da plataforma da **OpenAI**, defina um "Hard Budget Limit" (*ex: limite de uso de USD 15,00 no mês*) para evitar que bugs ou uso agressivo esgotem seu cartão de crédito subitamente. O mesmo para o Kimi, se suportar.

3. **Plano de Domínio e Infra**
   * Configurar CNAME e Certificado SSL em um domínio próprio (se ainda não usar) na sua hospedagem (Fly.io/Vercel/Reflex). Se os deploys exigem muito recurso, assinar o plano menor pago do *host* também elimina *cold-starts* do backend.
