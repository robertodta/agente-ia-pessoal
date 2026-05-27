"""
Ferramentas para interagir com o board do Notion.
Lê tarefas de um database e cria novas páginas.
"""
import logging
from typing import Any

from notion_client import Client
from notion_client.errors import APIResponseError

logger = logging.getLogger(__name__)


class NotionTools:
    """Encapsula operações de leitura e escrita no Notion."""

    def __init__(self, token: str, database_id: str):
        self.client = Client(auth=token)
        self.database_id = database_id

    def _extrair_texto(self, prop: dict) -> str:
        """Extrai texto de uma propriedade title ou rich_text."""
        items = prop.get("title") or prop.get("rich_text") or []
        return "".join(item.get("plain_text", "") for item in items)

    def _extrair_select(self, prop: dict) -> str:
        """Extrai o nome de uma propriedade select."""
        select = prop.get("select")
        return select.get("name", "") if select else ""

    def _extrair_people(self, prop: dict) -> str:
        """Extrai nomes de uma propriedade people."""
        pessoas = prop.get("people", [])
        nomes = [p.get("name", "") for p in pessoas]
        return ", ".join(nomes) if nomes else ""

    def _extrair_date(self, prop: dict) -> str:
        """Extrai a data de início de uma propriedade date."""
        date = prop.get("date")
        return date.get("start", "") if date else ""

    def buscar_tarefas(self) -> list[dict[str, str]]:
        """
        Busca todas as tarefas do database do Notion.

        Returns:
            Lista de dicts com: id, titulo, status, responsavel, prazo, prioridade
        """
        try:
            resposta = self.client.databases.query(database_id=self.database_id)
            tarefas = []
            for pagina in resposta.get("results", []):
                props = pagina.get("properties", {})
                tarefa = {
                    "id": pagina.get("id", ""),
                    "titulo": self._extrair_texto(props.get("Nome", props.get("Name", {}))),
                    "status": self._extrair_select(props.get("Status", {})),
                    "responsavel": self._extrair_people(props.get("Responsável", props.get("Assignee", {}))),
                    "prazo": self._extrair_date(props.get("Prazo", props.get("Due Date", {}))),
                    "prioridade": self._extrair_select(props.get("Prioridade", props.get("Priority", {}))),
                }
                tarefas.append(tarefa)
            logger.info("Notion: %d tarefas carregadas.", len(tarefas))
            return tarefas
        except APIResponseError as e:
            logger.error("Erro ao buscar tarefas no Notion: %s", e)
            raise

    def criar_tarefa(
        self,
        titulo: str,
        status: str = "A fazer",
        prioridade: str = "Média",
        prazo: str | None = None,
        notas: str = "",
    ) -> dict[str, Any]:
        """
        Cria uma nova tarefa no database do Notion.

        Args:
            titulo: Nome da tarefa
            status: Status inicial (ex: "A fazer", "Em andamento")
            prioridade: Nível de prioridade (ex: "Alta", "Média", "Baixa")
            prazo: Data no formato YYYY-MM-DD, ou None
            notas: Texto adicional da tarefa

        Returns:
            Página criada (dict retornado pela API do Notion)
        """
        properties: dict[str, Any] = {
            "Nome": {"title": [{"text": {"content": titulo}}]},
            "Status": {"select": {"name": status}},
            "Prioridade": {"select": {"name": prioridade}},
        }
        if prazo:
            properties["Prazo"] = {"date": {"start": prazo}}
        if notas:
            properties["Notas"] = {"rich_text": [{"text": {"content": notas}}]}

        try:
            resultado = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties,
            )
            logger.info("Notion: tarefa '%s' criada com id %s.", titulo, resultado.get("id"))
            return resultado
        except APIResponseError as e:
            logger.error("Erro ao criar tarefa no Notion: %s", e)
            raise
