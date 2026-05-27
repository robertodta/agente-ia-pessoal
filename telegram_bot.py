"""
Módulo do bot Telegram.
Usa polling para receber mensagens, áudios e fotos, roteando para o Agent.
Filtra mensagens por chat_id para segurança.
"""
import asyncio
import logging

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

logger = logging.getLogger(__name__)


class TelegramBot:
    """Encapsula o bot Telegram com polling e filtragem de chat_id."""

    def __init__(self, token: str, chat_id: int, agent, audio_tools=None, vision_tools=None):
        self.token = token
        self.chat_id = chat_id
        self.agent = agent
        self.audio_tools = audio_tools
        self.vision_tools = vision_tools
        self.app = Application.builder().token(token).build()
        self._loop = None
        self._registrar_handlers()

    def _autorizado(self, update: Update) -> bool:
        """Retorna True se a mensagem vem do chat_id autorizado."""
        if update.effective_chat.id != self.chat_id:
            logger.warning(
                "Mensagem ignorada de chat_id não autorizado: %s",
                update.effective_chat.id,
            )
            return False
        return True

    def _registrar_handlers(self):
        """Registra handlers para texto, voz e foto."""

        async def handle_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not self._autorizado(update):
                return
            texto = update.message.text
            logger.info("Texto recebido: '%s'", texto[:50])
            await context.bot.send_chat_action(chat_id=self.chat_id, action="typing")
            try:
                resposta = self.agent.responder(texto)
            except Exception as e:
                logger.error("Erro ao processar texto: %s", e)
                resposta = f"⚠️ Erro ao processar mensagem.\nDetalhe: {e}"
            await self._enviar_com_retry(resposta)

        async def handle_voz(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not self._autorizado(update):
                return
            if self.audio_tools is None:
                await self._enviar_com_retry("⚠️ Transcrição de áudio não está configurada.")
                return
            logger.info("Áudio recebido — transcrevendo...")
            await context.bot.send_chat_action(chat_id=self.chat_id, action="typing")
            try:
                arquivo = await update.message.voice.get_file()
                texto_transcrito = await self.audio_tools.baixar_e_transcrever(arquivo)
                logger.info("Transcrição: '%s'", texto_transcrito[:80])
                # Confirma a transcrição antes de processar
                await self._enviar_com_retry(f"🎤 _Transcrição:_ {texto_transcrito}")
                resposta = self.agent.responder(texto_transcrito)
            except Exception as e:
                logger.error("Erro ao processar áudio: %s", e)
                resposta = f"⚠️ Erro ao transcrever áudio.\nDetalhe: {e}"
            await self._enviar_com_retry(resposta)

        async def handle_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not self._autorizado(update):
                return
            if self.vision_tools is None:
                await self._enviar_com_retry("⚠️ Análise de imagens não está configurada.")
                return
            logger.info("Foto recebida — analisando...")
            await context.bot.send_chat_action(chat_id=self.chat_id, action="typing")
            try:
                # Pega a maior resolução disponível
                foto = update.message.photo[-1]
                arquivo = await foto.get_file()
                bloco_imagem = await self.vision_tools.baixar_e_preparar(arquivo)
                # Legenda da foto como texto do usuário (pode ser vazia)
                legenda = update.message.caption or ""
                resposta = self.agent.responder_com_imagem(legenda, bloco_imagem)
            except Exception as e:
                logger.error("Erro ao processar foto: %s", e)
                resposta = f"⚠️ Erro ao analisar imagem.\nDetalhe: {e}"
            await self._enviar_com_retry(resposta)

        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_texto))
        self.app.add_handler(MessageHandler(filters.VOICE, handle_voz))
        self.app.add_handler(MessageHandler(filters.PHOTO, handle_foto))

    async def _enviar_com_retry(self, texto: str, tentativas: int = 3) -> None:
        """Envia mensagem ao chat_id com retry em caso de falha."""
        for tentativa in range(1, tentativas + 1):
            try:
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
        logger.info("Bot Telegram iniciando polling (texto + voz + foto)...")
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self.app.run_polling(drop_pending_updates=True)
