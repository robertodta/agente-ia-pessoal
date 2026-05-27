"""
Ferramenta de busca na internet via DuckDuckGo.
Não requer chave de API.
"""
import logging
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)


class SearchTools:
    """Encapsula buscas na web usando DuckDuckGo."""

    def buscar(self, query: str, max_results: int = 5) -> list[dict[str, str]]:
        """
        Realiza uma busca na web e retorna os top resultados.

        Args:
            query: Texto da busca
            max_results: Número máximo de resultados (padrão: 5)

        Returns:
            Lista de dicts com: titulo, url, resumo
            Retorna lista vazia em caso de erro.
        """
        try:
            with DDGS() as ddgs:
                resultados_brutos = ddgs.text(query, max_results=max_results)
            resultados = [
                {
                    "titulo": r.get("title", ""),
                    "url": r.get("href", ""),
                    "resumo": r.get("body", ""),
                }
                for r in resultados_brutos
            ]
            logger.info("Busca '%s': %d resultados.", query, len(resultados))
            return resultados
        except Exception as e:
            logger.error("Erro na busca DuckDuckGo: %s", e)
            return []
