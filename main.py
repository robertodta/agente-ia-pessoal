"""
Ponto de entrada do agente.
Inicializa todos os componentes e sobe as threads do bot e do scheduler.
"""
import logging
import os
import signal
import sys
import threading
import time

from dotenv import load_dotenv

# Carrega variáveis de ambiente antes de qualquer import interno
load_dotenv()

from agent import Agent
from conversation_store import ConversationStore
from scheduler import iniciar_scheduler
from telegram_bot import TelegramBot
from tools.audio_tools import AudioTools
from tools.calendar_tools import CalendarTools
from tools.gmail_tools import GmailTools
from tools.notion_tools import NotionTools
from tools.search_tools import SearchTools
from tools.sheets_tools import SheetsTools
from tools.vision_tools import VisionTools

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def validar_variaveis_de_ambiente() -> None:
    """Garante que todas as variáveis obrigatórias estão definidas."""
    obrigatorias = [
        "ANTHROPIC_API_KEY",
        "TELEGRAM_TOKEN",
        "TELEGRAM_CHAT_ID",
        "NOTION_TOKEN",
        "NOTION_DATABASE_ID",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
    ]
    faltando = [v for v in obrigatorias if not os.getenv(v)]
    if faltando:
        logger.error("Variáveis de ambiente faltando: %s", ", ".join(faltando))
        logger.error("Configure o arquivo .env com base no .env.example")
        sys.exit(1)


def main():
    logger.info("=== Iniciando Agente de IA ===")
    validar_variaveis_de_ambiente()

    # Inicializar ferramentas principais
    logger.info("Inicializando ferramentas...")
    notion = NotionTools(
        token=os.getenv("NOTION_TOKEN"),
        database_id=os.getenv("NOTION_DATABASE_ID"),
    )
    search = SearchTools()
    calendar = CalendarTools(
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    )
    gmail = GmailTools(
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    )

    # Ferramentas opcionais
    audio_tools = AudioTools()
    vision_tools = VisionTools()

    sheets = None
    sheets_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
    if sheets_id:
        logger.info("Google Sheets configurado: %s", sheets_id)
        sheets = SheetsTools(
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            spreadsheet_id=sheets_id,
        )
    else:
        logger.info("Google Sheets não configurado (GOOGLE_SHEETS_SPREADSHEET_ID não definido).")

    # Inicializar store e agent
    logger.info("Carregando histórico de conversa...")
    store = ConversationStore(caminho="data/conversation.json")
    agent = Agent(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        store=store,
        notion=notion,
        search=search,
        calendar=calendar,
        gmail=gmail,
        sheets=sheets,
        max_mensagens=int(os.getenv("MAX_HISTORY_MESSAGES", "40")),
    )
    logger.info("Agente inicializado com %d mensagens no histórico.", len(store.obter_mensagens()))

    # Inicializar bot Telegram com suporte a voz e foto
    chat_id = int(os.getenv("TELEGRAM_CHAT_ID"))
    bot = TelegramBot(
        token=os.getenv("TELEGRAM_TOKEN"),
        chat_id=chat_id,
        agent=agent,
        audio_tools=audio_tools,
        vision_tools=vision_tools,
    )

    # Inicializar scheduler
    scheduler = iniciar_scheduler(
        agent=agent,
        enviar_mensagem_func=bot.enviar_mensagem_sincrono,
    )

    # Handler para encerramento limpo (Ctrl+C ou SIGTERM)
    def encerrar(signum, frame):
        logger.info("Encerrando agente...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, encerrar)
    signal.signal(signal.SIGTERM, encerrar)

    # Inicia bot em thread separada (bloqueante)
    thread_bot = threading.Thread(target=bot.iniciar, daemon=True, name="telegram-bot")
    thread_bot.start()

    logger.info("✅ Agente rodando! Texto + voz + foto + sheets ativos.")
    logger.info("Pressione Ctrl+C para encerrar.")

    # Mantém o processo principal vivo
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
