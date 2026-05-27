"""
Ferramenta de transcrição de áudio usando Whisper local.
Não requer chave de API — o modelo roda localmente.
Na primeira chamada, faz download do modelo (~140MB para 'base').
"""
import logging
import os
import tempfile

import whisper

logger = logging.getLogger(__name__)

# Modelo Whisper a usar. Opções por tamanho/qualidade:
# "tiny" (~75MB, mais rápido), "base" (~140MB), "small" (~460MB), "medium" (~1.5GB)
MODELO_WHISPER = os.getenv("WHISPER_MODEL", "base")


class AudioTools:
    """Encapsula transcrição de áudio via Whisper local."""

    def __init__(self):
        # Carrega o modelo na inicialização (faz download se necessário)
        logger.info("Carregando modelo Whisper '%s'...", MODELO_WHISPER)
        self._modelo = whisper.load_model(MODELO_WHISPER)
        logger.info("Modelo Whisper carregado.")

    def transcrever(self, caminho_arquivo: str) -> str:
        """
        Transcreve um arquivo de áudio para texto.

        Args:
            caminho_arquivo: Caminho local para o arquivo de áudio (.ogg, .mp3, .wav etc.)

        Returns:
            Texto transcrito (strip aplicado), ou mensagem de erro.
        """
        try:
            resultado = self._modelo.transcribe(caminho_arquivo, language="pt")
            texto = resultado.get("text", "").strip()
            logger.info("Áudio transcrito: '%s'", texto[:80])
            return texto
        except Exception as e:
            logger.error("Erro ao transcrever áudio: %s", e)
            return f"Erro ao transcrever áudio: {e}"

    async def baixar_e_transcrever(self, arquivo_telegram, prefixo: str = "audio") -> str:
        """
        Baixa um arquivo de áudio do Telegram e transcreve.

        Args:
            arquivo_telegram: Objeto File do python-telegram-bot
            prefixo: Prefixo para o nome do arquivo temporário

        Returns:
            Texto transcrito, ou mensagem de erro.
        """
        with tempfile.NamedTemporaryFile(suffix=".ogg", prefix=prefixo, delete=False) as f:
            caminho_tmp = f.name
        try:
            await arquivo_telegram.download_to_drive(caminho_tmp)
            return self.transcrever(caminho_tmp)
        finally:
            if os.path.exists(caminho_tmp):
                os.unlink(caminho_tmp)
