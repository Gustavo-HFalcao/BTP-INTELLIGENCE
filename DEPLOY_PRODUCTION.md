# 🚀 BOMTEMPO Dashboard - Guia de Deploy em Produção

## Métodos de Deploy

### 1. Reflex Deploy (Recomendado - Mais Fácil)
```bash
reflex deploy
```
- Hospedagem gerenciada pela Reflex
- HTTPS automático
- Ambiente configurado automaticamente
- **Custo:** Plano pago necessário

### 2. Self-Hosting (Docker/VPS)
- Mais controle e gratuito
- Requer configuração manual
- Ver seção "Self-Hosting" abaixo

---

## ⚠️ Problemas Potenciais e Soluções

### 1. **CORS (Cross-Origin Resource Sharing)**

**Problema:** Se o frontend estiver em um domínio diferente do backend, APIs podem bloquear requisições.

**APIs Externas Usadas:**
- ✅ **Kimi/Moonshot AI** (`https://api.moonshot.cn`) - Análise de IA
- ✅ **OpenWeather API** (`https://api.open-meteo.com`) - Previsão do tempo
- ✅ **Google Sheets** (CSV export) - Dados

**Solução para Reflex Deploy:**
```python
# Adicionar em bomtempo.py
app = rx.App(
    # ... config existente ...
    cors_allowed_origins=[
        "https://api.moonshot.cn",
        "https://api.open-meteo.com",
        "https://docs.google.com",
    ]
)
```

**Solução para Self-Hosting (nginx):**
```nginx
location /api/ {
    add_header 'Access-Control-Allow-Origin' '*';
    add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS';
}
```

---

### 2. **CSP (Content Security Policy)**

**Problema:** Browsers bloqueiam scripts/APIs não autorizados por segurança.

**Features que podem ser bloqueadas:**
- ❌ **Speech-to-Text (Audio Input)** - Requer permissão `microphone`
- ❌ **API calls** - Requer `connect-src`
- ✅ **Recharts** - Já funciona (scripts locais)

**Solução - Adicionar em `assets/style.css` ou via meta tag:**

```html
<!-- Em index.html ou como meta tag no Reflex -->
<meta http-equiv="Content-Security-Policy"
      content="default-src 'self';
               script-src 'self' 'unsafe-inline' 'unsafe-eval';
               connect-src 'self' https://api.moonshot.cn https://api.open-meteo.com https://docs.google.com;
               media-src 'self' blob:;
               img-src 'self' data: https:;">
```

**Para Reflex, adicionar em `rxconfig.py`:**
```python
config = rx.Config(
    app_name="bomtempo",
    # ... outros configs ...
    custom_headers={
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "connect-src 'self' https://api.moonshot.cn https://api.open-meteo.com https://docs.google.com; "
            "media-src 'self' blob:; "
            "img-src 'self' data: https:;"
        )
    }
)
```

---

### 3. **Speech-to-Text (Audio Input) - ANTECIPAÇÃO**

**Feature Planejada:** Falar com o chat via áudio

**Tecnologias Disponíveis:**
1. **Browser API (Web Speech API)** - Grátis, funciona no Chrome/Edge
2. **Whisper OpenAI** - Pago, mais preciso
3. **Google Cloud Speech-to-Text** - Pago, boa precisão em PT-BR

**Problemas Potenciais:**

#### A. **Permissão de Microfone**
```javascript
// Frontend precisa pedir permissão
navigator.mediaDevices.getUserMedia({ audio: true })
```

**Solução Reflex:**
- Usar componente custom com JavaScript
- Ou biblioteca externa como `reflex-audio-recorder` (se existir)

#### B. **HTTPS Obrigatório**
- ❌ `http://` não permite acesso ao microfone
- ✅ `https://` requerido para produção
- ✅ Reflex Deploy já fornece HTTPS

#### C. **CSP Bloqueando Áudio**
```python
# Adicionar em rxconfig.py
"media-src 'self' blob: mediastream:"
```

#### D. **Tamanho de Upload**
- Arquivos de áudio podem ser grandes (1-5MB por 1min)
- Reflex tem limite de upload padrão (verificar docs)

**Solução Recomendada:**
```python
# Em rxconfig.py
config = rx.Config(
    # ...
    api_url="https://seu-dominio.com",  # HTTPS obrigatório
    # Aumentar limite de upload se necessário
    upload_max_size=10 * 1024 * 1024,  # 10MB
)
```

**Exemplo de Implementação (Speech-to-Text):**
```python
# No GlobalState
async def process_audio(self, audio_file: rx.UploadFile):
    """Converte áudio para texto usando Whisper ou Web Speech API"""
    # Opção 1: Usar Whisper (OpenAI)
    import openai
    transcript = openai.Audio.transcribe("whisper-1", audio_file)

    # Opção 2: Processar no frontend via Web Speech API
    # (mais barato, mas menos preciso)
    return transcript.text
```

---

### 4. **Cookies e Sessões**

**Estado Atual:** Reflex gerencia sessões automaticamente

**Em Produção:**
- ✅ Cookies funcionam nativamente no Reflex
- ✅ Login/Logout já implementado com `is_authenticated`
- ⚠️ **IMPORTANTE:** Configurar `secure=True` para HTTPS

**Recomendação:**
```python
# Se adicionar cookies manualmente no futuro:
rx.cookie.set("session", value, secure=True, httponly=True, samesite="strict")
```

---

### 5. **Variáveis de Ambiente**

**APIs que precisam de chaves:**
- ✅ Kimi/Moonshot: `MOONSHOT_API_KEY`
- ✅ Supabase (backend): `SUPABASE_SERVICE_KEY`
- ✅ OpenWeather: Gratuito, sem key

**Em Produção (Reflex Deploy):**
```bash
reflex deploy --env MOONSHOT_API_KEY=your_key_here --env SUPABASE_SERVICE_KEY=your_sb_key
```

**Self-Hosting (.env file):**
```bash
# .env
MOONSHOT_API_KEY=your_key_here
SUPABASE_SERVICE_KEY=your_sb_key
ENVIRONMENT=production
```

---

## 📋 Checklist de Deploy

### Antes do Deploy
- [ ] Testar todas as features localmente
- [ ] Verificar se APIs externas funcionam
- [ ] Configurar variáveis de ambiente
- [ ] Adicionar CORS/CSP configs em `rxconfig.py`
- [ ] Testar login/logout
- [ ] Verificar se dados do Google Sheets carregam

### Durante o Deploy (Reflex)
```bash
# 1. Login
reflex login

# 2. Configurar variáveis de ambiente
reflex deploy --env MOONSHOT_API_KEY=xxx

# 3. Deploy
reflex deploy
```

### Após Deploy
- [ ] Testar HTTPS funcionando
- [ ] Verificar se análise de IA funciona
- [ ] Testar weather widget
- [ ] Verificar se Google Sheets atualiza
- [ ] Testar em diferentes browsers (Chrome, Firefox, Safari)
- [ ] Testar em mobile

---

## 🎤 Implementação Futura: Speech-to-Text

**Quando implementar feature de áudio:**

1. **Adicionar permissão de microfone em CSP**
2. **Usar Web Speech API (grátis) ou Whisper (pago)**
3. **Garantir HTTPS em produção**
4. **Aumentar limite de upload se necessário**

**Exemplo de componente:**
```python
# bomtempo/components/audio_recorder.py
def audio_recorder() -> rx.Component:
    return rx.box(
        rx.button(
            rx.icon("mic"),
            "Gravar Áudio",
            on_click=GlobalState.start_recording,
        ),
        # JavaScript inline para capturar áudio
        rx.script("""
            async function startRecording() {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                // ... lógica de gravação
            }
        """)
    )
```

---

## 🐳 Self-Hosting (Alternativa)

**Dockerfile:**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["reflex", "run", "--env", "prod"]
```

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  bomtempo:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MOONSHOT_API_KEY=${MOONSHOT_API_KEY}
    restart: unless-stopped
```

---

## 📊 Monitoramento Recomendado

1. **Logs de Erro:** Configurar Sentry ou similar
2. **Uptime:** UptimeRobot (grátis)
3. **Performance:** Google Analytics

---

## ✅ Resumo

**Problemas que PODEM ocorrer:**
1. ✅ CORS - **Resolvido** com config em `rxconfig.py`
2. ✅ CSP - **Resolvido** com headers customizados
3. ⚠️ Speech-to-Text - **Requer HTTPS + permissões** (antecipado)
4. ✅ Cookies/Sessões - **Funcionam nativamente**
5. ✅ APIs Externas - **Funcionam** (Kimi, Weather, Google Sheets)

**Tudo rodará corretamente em produção SE:**
- Usar **HTTPS** (obrigatório para áudio)
- Configurar **CORS/CSP** em `rxconfig.py`
- Definir **variáveis de ambiente** no deploy
- Testar **antes** de ir pra produção

🚀 **Reflex Deploy é recomendado** - gerencia HTTPS, CORS e sessões automaticamente!
