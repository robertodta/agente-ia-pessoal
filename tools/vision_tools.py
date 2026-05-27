"""
Ferramenta de visão: prepara imagens para envio à Claude API.
Claude suporta visão nativamente — não requer lib extra.
Formatos suportados: JPEG, PNG, GIF, WebP (máx ~5MB por imagem).
"""
import base64
import logging
import os
import tempfile

logger = logging.getLogger(__name__)

# Mapeamento de extensão para media type aceito pela Claude API
MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


class VisionTools:
    """Prepara imagens para envio à Claude API como blocos de visão."""

    def detectar_media_type(self, nome_arquivo: str) -> str:
        """
        Detecta o media type pela extensão do arquivo.

        Args:
            nome_arquivo: Nome ou caminho do arquivo

        Returns:
            Media type no formato 'image/xxx'. Fallback: 'image/jpeg'.
        """
        extensao = os.path.splitext(nome_arquivo)[1].lower()
        return MEDIA_TYPES.get(extensao, "image/jpeg")

    def preparar_bloco_imagem(self, caminho_arquivo: str, media_type: str | None = None) -> dict:
        """
        Lê um arquivo de imagem e retorna o bloco no formato da Claude API.

        Args:
            caminho_arquivo: Caminho local para o arquivo de imagem
            media_type: Media type explícito. Se None, detecta pela extensão.

        Returns:
            Dict com estrutura:
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": "<base64>"
                }
            }
        """
        if media_type is None:
            media_type = self.detectar_media_type(caminho_arquivo)

        with open(caminho_arquivo, "rb") as f:
            dados = f.read()

        dados_b64 = base64.standard_b64encode(dados).decode("utf-8")
        logger.info(
            "Imagem preparada: %s (%s, %.1f KB)",
            os.path.basename(caminho_arquivo),
            media_type,
            len(dados) / 1024,
        )
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": dados_b64,
            },
        }

    async def baixar_e_preparar(self, arquivo_telegram, extensao: str = ".jpg") -> dict:
        """
        Baixa uma foto do Telegram e prepara o bloco para a Claude API.

        Args:
            arquivo_telegram: Objeto File do python-telegram-bot
            extensao: Extensão do arquivo para detecção de media type

        Returns:
            Bloco de imagem no formato da Claude API
        """
        with tempfile.NamedTemporaryFile(suffix=extensao, delete=False) as f:
            caminho_tmp = f.name
        try:
            await arquivo_telegram.download_to_drive(caminho_tmp)
            return self.preparar_bloco_imagem(caminho_tmp)
        finally:
            if os.path.exists(caminho_tmp):
                os.unlink(caminho_tmp)
