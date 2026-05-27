"""
Módulo de persistência do histórico de conversa.
Salva e carrega mensagens em um arquivo JSON local.
"""
import json
import logging
import os
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class ConversationStore:
    """
    Gerencia o histórico de conversa persistido em disco.
    Thread-safe desde que o chamador use um Lock externo.
    """

    def __init__(self, caminho: str = "data/conversation.json"):
        self.caminho = caminho
        self._mensagens: list[dict[str, Any]] = []
        self._carregar()

    def _carregar(self) -> None:
        """Carrega histórico do disco, se existir."""
        if not os.path.exists(self.caminho):
            logger.info("Nenhum histórico encontrado em %s. Iniciando vazio.", self.caminho)
            return
        try:
            with open(self.caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
            self._mensagens = dados.get("messages", [])
            logger.info("Histórico carregado: %d mensagens.", len(self._mensagens))
        except (json.JSONDecodeError, IOError) as e:
            logger.error("Erro ao carregar histórico: %s. Iniciando vazio.", e)
            self._mensagens = []

    def _salvar(self) -> None:
        """Persiste o histórico atual em disco."""
        os.makedirs(os.path.dirname(self.caminho) if os.path.dirname(self.caminho) else ".", exist_ok=True)
        dados = {
            "messages": self._mensagens,
            "last_updated": datetime.now().isoformat(),
            "message_count": len(self._mensagens),
        }
        try:
            with open(self.caminho, "w", encoding="utf-8") as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error("Erro ao salvar histórico: %s", e)

    def adicionar_mensagem(
        self,
        role: str,
        content: Any,
        max_mensagens: int = 40,
    ) -> None:
        """
        Adiciona uma mensagem ao histórico e persiste em disco.
        Trunca automaticamente se ultrapassar max_mensagens.

        Args:
            role: 'user', 'assistant' ou 'tool'
            content: texto da mensagem ou lista de blocos (tool use)
            max_mensagens: limite máximo de mensagens no histórico
        """
        self._mensagens.append({"role": role, "content": content})
        if len(self._mensagens) > max_mensagens:
            self._mensagens = self._mensagens[-max_mensagens:]
            logger.debug("Histórico truncado para %d mensagens.", max_mensagens)
        self._salvar()

    def obter_mensagens(self) -> list[dict[str, Any]]:
        """Retorna uma cópia da lista de mensagens."""
        return list(self._mensagens)

    def limpar(self) -> None:
        """Remove todo o histórico da memória e do disco."""
        self._mensagens = []
        self._salvar()
        logger.info("Histórico limpo.")
