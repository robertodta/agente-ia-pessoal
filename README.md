# Agente de IA Pessoal — Telegram + Notion + Google

Agente de IA que roda proativamente (resumo diário às 8h30) e responde
mensagens no Telegram, com acesso ao Notion, Google Calendar, Gmail e busca web.

## Pré-requisitos

- Python 3.11+
- Conta no Telegram com bot criado via [@BotFather](https://t.me/BotFather)
- Workspace no Notion com database de tarefas
- Projeto no Google Cloud Console com Calendar API e Gmail API habilitadas

## Instalação

```bash
git clone <url-do-repo>
cd projeto-agente
pip install -r requirements.txt
cp .env.example .env
# Edite .env com suas credenciais
```

## Configuração do Google OAuth2

1. Acesse [Google Cloud Console](https://console.cloud.google.com)
2. Crie um projeto e habilite **Google Calendar API** e **Gmail API**
3. Em "Credenciais", crie **OAuth 2.0** para aplicativo Desktop
4. Copie `client_id` e `client_secret` para o `.env`
5. Execute localmente para gerar `token.json` (abre o browser uma vez):
   ```bash
   python -c "from tools.calendar_tools import CalendarTools; CalendarTools('SEU_CLIENT_ID', 'SEU_CLIENT_SECRET')"
   ```
6. No VPS: copie o `token.json` gerado:
   ```bash
   scp token.json usuario@servidor:/caminho/projeto-agente/
   ```

## Configuração do Notion

1. Acesse [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Crie uma nova integração e copie o `NOTION_TOKEN`
3. No seu database do Notion, clique em **"..."** → **"Connections"** → adicione sua integração
4. Copie o ID do database da URL: `notion.so/<workspace>/<DATABASE_ID>?v=...`

## Configuração do Telegram

1. Crie um bot via [@BotFather](https://t.me/BotFather) — copie o token
2. Para obter seu `TELEGRAM_CHAT_ID`: envie uma mensagem para o bot e acesse:
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```

## Executar

```bash
python main.py
```

## Deploy no VPS com systemd

Crie `/etc/systemd/system/agente-ia.service`:

```ini
[Unit]
Description=Agente de IA Pessoal
After=network.target

[Service]
Type=simple
User=seu-usuario
WorkingDirectory=/caminho/projeto-agente
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable agente-ia
sudo systemctl start agente-ia
sudo systemctl status agente-ia
```

## Estrutura do projeto

```
projeto-agente/
├── main.py                  # Ponto de entrada
├── agent.py                 # Loop de tool use + Claude API
├── conversation_store.py    # Histórico persistido em JSON
├── scheduler.py             # Resumo diário agendado (APScheduler)
├── telegram_bot.py          # Polling Telegram + filtro chat_id
├── tools/
│   ├── notion_tools.py      # Lê e cria tarefas no Notion
│   ├── search_tools.py      # Busca web via DuckDuckGo
│   ├── calendar_tools.py    # Google Calendar (OAuth2)
│   └── gmail_tools.py       # Gmail (OAuth2)
├── data/
│   └── conversation.json    # Histórico de conversa (gerado automaticamente)
├── .env.example             # Template de configuração
└── requirements.txt
```

## Ferramentas disponíveis para o agente

| Ferramenta | Descrição |
|---|---|
| `buscar_tarefas_notion` | Lê todas as tarefas do board |
| `criar_tarefa_notion` | Cria nova tarefa no board |
| `buscar_internet` | Pesquisa no DuckDuckGo |
| `criar_evento_calendar` | Cria evento no Google Calendar |
| `listar_eventos_calendar` | Lista eventos de um período |
| `enviar_email` | Envia e-mail via Gmail |

## Como funciona

### Modo Proativo (agendado)
Todo dia no horário definido em `SCHEDULE_TIME` (padrão: `08:30`), o agente:
1. Acorda automaticamente via APScheduler
2. Busca tarefas do Notion
3. Claude analisa e gera resumo: atrasadas, em risco, sem dono, prioridades do dia
4. Envia via Telegram sem você precisar pedir

### Modo Responsivo (sob demanda)
Quando você envia mensagem no Telegram:
1. O bot recebe e filtra pelo seu `chat_id`
2. O agente busca contexto atualizado e usa ferramentas conforme necessário
3. Responde com base nos dados mais recentes
4. **Mantém o histórico completo** — se você responder ao resumo das 8h30 às 10h, o Claude lembra tudo

### Compartilhamento de contexto
Ambos os modos compartilham o mesmo histórico (`data/conversation.json`).
O histórico é truncado automaticamente (padrão: últimas 40 mensagens) e
sobrevive a restarts do processo.
