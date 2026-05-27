"""
Módulo do bot Telegram.
Usa polling para receber mensagens e roteia para o Agent.
Filtra mensagens por chat_id para segurança.
"""
import asyncio
import logging

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

logger = logging.getLogger(__name__)


class TelegramBot:
    """Encapsula o bot Telegram com polling e filtragem de chat_id."""

    def __init__(self, token: str, chat_id: int, agent):
        self.token = token
        self.chat_id = chat_id
        self.agent = agent
        self.app = Application.builder().token(token).build()
        self._loop = None
        self._registrar_handlers()

    def _registrar_handlers(self):
        """Registra o handler para mensagens de texto."""

        async def handle_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
            # Ignora mensagens de outros chat_ids (segurança)
            if update.effective_chat.id != self.chat_id:
                logger.warning(
                    "Mensagem ignorada de chat_id não autorizado: %s",
                    update.effective_chat.id,
                )
                return

            texto = update.message.text
            logger.info("Mensagem recebida: '%s'", texto[:50])

            # Mostra "digitando..." enquanto processa
            await context.bot.send_chat_action(
                chat_id=self.chat_id, action="typing"
            )

            try:
                resposta = self.agent.responder(texto)
            except Exception as e:
                logger.error("Erro ao processar mensagem: %s", e)
                resposta = f"⚠️ Ocorreu um erro ao processar sua mensagem.\nDetalhe: {e}"

            await self._enviar_com_retry(resposta)

        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mensagem)
        )

    async def _enviar_com_retry(self, texto: str, tentativas: int = 3) -> None:
        """Envia mensagem ao chat_id com retry em caso de falha."""
        for tentativa in range(1, tentativas + 1):
            try:
                # Divide mensagens longas (limite do Telegram: 4096 chars)
                for i in range(0, len(texto), 4096):
                    await self.app.bot.send_message(
                        chat_id=self.chat_id,
                        text=texto[i : i + 4096],
                        parse_mode="Markdown",
                    )
                return
            except Exception as e:
                logger.warning("Tentativa %d de envio falhou: %s", tentativa, e)
                if tentativa < tentativas:
                    await asyncio.sleep(2)
        logger.error("Falha ao enviar mensagem após %d tentativas.", tentativas)

    def enviar_mensagem_sincrono(self, texto: str) -> None:
        """
        Envia mensagem de forma síncrona (usado pelo scheduler na thread de background).
        Usa o event loop da aplicação do bot para enfileirar a coroutine.
        """
        if self._loop is None or self._loop.is_closed():
            logger.error("Loop do bot não disponível para envio síncrono.")
            return
        future = asyncio.run_coroutine_threadsafe(
            self._enviar_com_retry(texto),
            self._loop,
        )
        try:
            future.result(timeout=30)
        except Exception as e:
            logger.error("Erro no envio síncrono: %s", e)

    def iniciar(self) -> None:
        """Inicia o polling em modo bloqueante (chamar em thread separada)."""
        logger.info("Bot Telegram iniciando polling...")
        # Salva referência ao loop para uso pelo scheduler
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self.app.run_polling(drop_pending_updates=True)
