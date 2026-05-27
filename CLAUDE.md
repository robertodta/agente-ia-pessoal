# Agente de IA Pessoal — Contexto do Projeto

## Visão Geral
Agente de IA pessoal em Python com dois modos de operação simultâneos:
- **Proativo:** resumo diário automático às 8h30 via APScheduler
- **Responsivo:** responde mensagens no Telegram a qualquer hora

Histórico de conversa compartilhado entre os dois modos, persistido em `data/conversation.json`.

## Stack
- Python 3.13
- `anthropic` SDK — claude-sonnet-4-20250514 com **tool use**
- `python-telegram-bot` 22.7 — modo polling
- `notion-client` — lê e cria tarefas
- `APScheduler` 3.10 — BackgroundScheduler
- `openai-whisper` — transcrição de áudio local
- `google-api-python-client` — Calendar, Gmail, Sheets (OAuth2, token.json)
- `duckduckgo-search` — busca web sem chave
- `python-dotenv`

## Estrutura de Arquivos
```
projeto-agente/
├── main.py                  # Ponto de entrada — sobe bot + scheduler em threads
├── agent.py                 # Loop de tool use + threading.Lock + responder_com_imagem()
├── conversation_store.py    # Histórico persistido em data/conversation.json
├── scheduler.py             # APScheduler — job diário
├── telegram_bot.py          # Polling + handlers de texto, voz e foto
├── tools/
│   ├── notion_tools.py      # buscar_tarefas(), criar_tarefa()
│   ├── search_tools.py      # buscar() via DuckDuckGo
│   ├── calendar_tools.py    # criar_evento(), listar_eventos() — OAuth2
│   ├── gmail_tools.py       # enviar_email() — OAuth2
│   ├── audio_tools.py       # transcrever(), baixar_e_transcrever() — Whisper local
│   ├── vision_tools.py      # preparar_bloco_imagem(), baixar_e_preparar()
│   └── sheets_tools.py      # ler_planilha(), escrever_planilha() — OAuth2
├── data/
│   └── conversation.json    # Histórico de conversa
├── .env                     # Credenciais (nunca commitar)
├── .env.example             # Template
└── requirements.txt
```

## Ferramentas do Claude (tool use)
- `buscar_tarefas_notion` — lê board completo
- `criar_tarefa_notion(titulo, status, prioridade, prazo, notas)`
- `buscar_internet(query, max_results)`
- `criar_evento_calendar(titulo, data, hora_inicio, hora_fim, descricao)`
- `listar_eventos_calendar(data_inicio, data_fim)`
- `enviar_email(destinatario, assunto, corpo)`
- `ler_planilha(intervalo)` — ex: "Sheet1!A1:D10"
- `escrever_planilha(intervalo, valores)`

## Variáveis de Ambiente (.env)
```
ANTHROPIC_API_KEY=
TELEGRAM_TOKEN=
TELEGRAM_CHAT_ID=
NOTION_TOKEN=
NOTION_DATABASE_ID=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_SHEETS_SPREADSHEET_ID=   # opcional
SCHEDULE_TIME=08:30
MAX_HISTORY_MESSAGES=40
TIMEZONE=America/Sao_Paulo
WHISPER_MODEL=base               # tiny | base | small | medium
```

## Autenticação Google
OAuth2 via `token.json` — gerado na primeira execução (abre browser).
Os escopos cobrem: Calendar + Gmail + Sheets.
Se adicionar Sheets depois: deletar `token.json` e re-autenticar.

## Testes
```
tests/
├── test_conversation_store.py   # 5 testes
├── test_tools.py                # 8+ testes (Notion, Search, Calendar, Gmail, Audio, Vision, Sheets)
└── test_agent.py                # 4+ testes (responder, tool use, lock, visão)
```

Rodar: `cd C:\Users\roberto.vinicius && pytest tests/ -v`

## Status do Projeto (2026-05-27)
- ✅ Plano base completo (Tasks 1-12, 16 testes passando)
- ✅ Plano áudio + visão + sheets completo (Tasks 1-8, 24 testes passando)
- ✅ Repositório no GitHub: https://github.com/robertodta/agente-ia-pessoal (privado)
- 🔜 Próximo passo: **deploy na VPS**

## Checklist de Deploy (VPS)
1. `git clone https://github.com/robertodta/agente-ia-pessoal.git`
2. `pip install -r requirements.txt`
3. `sudo apt install ffmpeg`
4. Copiar `.env.example` → `.env` e preencher credenciais
5. Habilitar **Google Sheets API** no Google Cloud Console (mesmo projeto)
6. Gerar `token.json` com os 3 escopos (Calendar + Gmail + Sheets):
   ```bash
   python -c "from tools.sheets_tools import SheetsTools; SheetsTools('CLIENT_ID', 'CLIENT_SECRET', 'SHEETS_ID')"
   ```
7. Configurar systemd: `/etc/systemd/system/agente-ia.service` (ver README)
8. `sudo systemctl enable agente-ia && sudo systemctl start agente-ia`

## Commits (branch master)
```
4c3f4fe  feat: integra AudioTools, VisionTools e SheetsTools no main.py
1333dd1  feat: adiciona handlers de voz e foto no TelegramBot
d52f8f9  feat: adiciona suporte a Sheets e visão no Agent
7365105  feat: adiciona SheetsTools para Google Sheets
24090b7  feat: adiciona VisionTools para preparar imagens para Claude
3170bfd  feat: adiciona AudioTools com Whisper local
70d5bdc  chore: adiciona openai-whisper às dependências
92c3b48  docs: adiciona CLAUDE.md com contexto completo do projeto
4a78f98  docs: adiciona README com instruções de setup e deploy
0e4f3ed  feat: adiciona scheduler, telegram_bot e main.py
27761af  feat: adiciona Agent com loop de tool use e threading.Lock
3701635  feat: adiciona GmailTools para envio de e-mails
23ccc18  feat: adiciona CalendarTools para Google Calendar
c93a808  feat: adiciona SearchTools com DuckDuckGo
3773de8  feat: adiciona NotionTools para leitura e criação de tarefas
3f7f216  feat: adiciona ConversationStore com persistência em JSON
cc32096  chore: estrutura base do projeto
```

## Docs
- Spec: `docs/superpowers/specs/2026-05-26-agente-ia-telegram-notion-design.md`
- Plano base: `docs/superpowers/plans/2026-05-26-agente-ia-telegram-notion.md`
- Plano áudio/visão/sheets: `docs/superpowers/plans/2026-05-26-audio-visao-sheets.md`

## Notas Importantes
- Bot só responde ao `TELEGRAM_CHAT_ID` configurado (segurança)
- `agent.py` usa `threading.Lock` — thread-safe para bot + scheduler simultâneos
- Histórico truncado automaticamente (últimas `MAX_HISTORY_MESSAGES` mensagens)
- Sheets é **opcional** — agente funciona sem ele se `GOOGLE_SHEETS_SPREADSHEET_ID` não estiver no .env
- Deploy: `python main.py` via systemd ou screen/tmux no VPS
