"""
Agente de IA principal.
Gerencia o histórico de conversa e o loop de tool use com o Claude.
"""
import json
import logging
import threading
import time
from typing import Any

import anthropic

from conversation_store import ConversationStore
from tools.notion_tools import NotionTools
from tools.search_tools import SearchTools
from tools.calendar_tools import CalendarTools
from tools.gmail_tools import GmailTools

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é um assistente pessoal de gestão de tarefas e produtividade.
Você tem acesso ao board de tarefas do Notion, ao Google Calendar, ao Gmail
e pode buscar informações na internet.
Responda sempre em português do Brasil, de forma objetiva e direta.
Quando for criar eventos ou tarefas, confirme os detalhes antes de executar.
Hoje é {data_hoje}."""

# Definição das ferramentas para o Claude
FERRAMENTAS = [
    {
        "name": "buscar_tarefas_notion",
        "description": "Busca todas as tarefas do board do Notion com status, responsável, prazo e prioridade.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "criar_tarefa_notion",
        "description": "Cria uma nova tarefa no board do Notion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "titulo": {"type": "string", "description": "Nome da tarefa"},
                "status": {"type": "string", "description": "Status: 'A fazer', 'Em andamento', 'Concluído'"},
                "prioridade": {"type": "string", "description": "Prioridade: 'Alta', 'Média', 'Baixa'"},
                "prazo": {"type": "string", "description": "Data no formato YYYY-MM-DD"},
                "notas": {"type": "string", "description": "Descrição adicional da tarefa"},
            },
            "required": ["titulo"],
        },
    },
    {
        "name": "buscar_internet",
        "description": "Busca informações atuais na internet usando DuckDuckGo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Termo de busca"},
                "max_results": {"type": "integer", "description": "Número de resultados (padrão: 5)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "criar_evento_calendar",
        "description": "Cria um evento no Google Calendar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "titulo": {"type": "string"},
                "data": {"type": "string", "description": "Formato YYYY-MM-DD"},
                "hora_inicio": {"type": "string", "description": "Formato HH:MM"},
                "hora_fim": {"type": "string", "description": "Formato HH:MM"},
                "descricao": {"type": "string"},
            },
            "required": ["titulo", "data", "hora_inicio", "hora_fim"],
        },
    },
    {
        "name": "listar_eventos_calendar",
        "description": "Lista eventos do Google Calendar em um período.",
        "input_schema": {
            "type": "object",
            "properties": {
                "data_inicio": {"type": "string", "description": "Formato YYYY-MM-DD"},
                "data_fim": {"type": "string", "description": "Formato YYYY-MM-DD"},
            },
            "required": ["data_inicio", "data_fim"],
        },
    },
    {
        "name": "enviar_email",
        "description": "Envia um e-mail via Gmail.",
        "input_schema": {
            "type": "object",
            "properties": {
                "destinatario": {"type": "string"},
                "assunto": {"type": "string"},
                "corpo": {"type": "string"},
            },
            "required": ["destinatario", "assunto", "corpo"],
        },
    },
]


class Agent:
    """
    Agente central. Mantém histórico e executa o loop de tool use com Claude.
    Thread-safe via threading.Lock.
    """

    def __init__(
        self,
        api_key: str,
        store: ConversationStore,
        notion: NotionTools,
        search: SearchTools,
        calendar: CalendarTools,
        gmail: GmailTools,
        max_mensagens: int = 40,
    ):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.store = store
        self.notion = notion
        self.search = search
        self.calendar = calendar
        self.gmail = gmail
        self.max_mensagens = max_mensagens
        self._lock = threading.Lock()

    def _executar_ferramenta(self, nome: str, argumentos: dict) -> Any:
        """Despacha a chamada de ferramenta para o módulo correto."""
        try:
            if nome == "buscar_tarefas_notion":
                return self.notion.buscar_tarefas()
            elif nome == "criar_tarefa_notion":
                return self.notion.criar_tarefa(**argumentos)
            elif nome == "buscar_internet":
                return self.search.buscar(
                    query=argumentos["query"],
                    max_results=argumentos.get("max_results", 5),
                )
            elif nome == "criar_evento_calendar":
                return self.calendar.criar_evento(**argumentos)
            elif nome == "listar_eventos_calendar":
                return self.calendar.listar_eventos(
                    data_inicio=argumentos["data_inicio"],
                    data_fim=argumentos["data_fim"],
                )
            elif nome == "enviar_email":
                return self.gmail.enviar_email(**argumentos)
            else:
                return {"erro": f"Ferramenta desconhecida: {nome}"}
        except Exception as e:
            logger.error("Erro ao executar ferramenta '%s': %s", nome, e)
            return {"erro": str(e)}

    def _chamar_claude_com_retry(self, mensagens: list, system: str) -> Any:
        """Chama a API do Claude com backoff exponencial (3 tentativas)."""
        delays = [1, 2, 4]
        ultimo_erro = None
        for tentativa, delay in enumerate(delays, 1):
            try:
                return self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    system=system,
                    tools=FERRAMENTAS,
                    messages=mensagens,
                )
            except anthropic.APIError as e:
                logger.warning("Tentativa %d falhou: %s. Aguardando %ds...", tentativa, e, delay)
                ultimo_erro = e
                time.sleep(delay)
        raise ultimo_erro

    def responder(self, mensagem_usuario: str) -> str:
        """
        Processa uma mensagem do usuário e retorna a resposta do agente.
        Thread-safe via lock interno.

        Args:
            mensagem_usuario: Texto enviado pelo usuário

        Returns:
            Texto da resposta final do Claude
        """
        from datetime import date
        system = SYSTEM_PROMPT.format(data_hoje=date.today().isoformat())

        with self._lock:
            self.store.adicionar_mensagem("user", mensagem_usuario, self.max_mensagens)
            mensagens = self.store.obter_mensagens()

            # Loop de tool use
            while True:
                resposta = self._chamar_claude_com_retry(mensagens, system)

                if resposta.stop_reason == "end_turn":
                    # Resposta final em texto
                    texto = next(
                        (b.text for b in resposta.content if b.type == "text"), ""
                    )
                    self.store.adicionar_mensagem("assistant", texto, self.max_mensagens)
                    return texto

                elif resposta.stop_reason == "tool_use":
                    # Claude quer usar uma ferramenta — salva bloco no histórico
                    conteudo_assistant = []
                    for b in resposta.content:
                        if b.type == "tool_use":
                            conteudo_assistant.append({
                                "type": "tool_use",
                                "id": b.id,
                                "name": b.name,
                                "input": b.input,
                            })
                        elif b.type == "text":
                            conteudo_assistant.append({
                                "type": "text",
                                "text": b.text,
                            })
                    self.store.adicionar_mensagem(
                        "assistant",
                        conteudo_assistant,
                        self.max_mensagens,
                    )

                    # Executa cada ferramenta solicitada e coleta resultados
                    resultados_tools = []
                    for bloco in resposta.content:
                        if bloco.type == "tool_use":
                            logger.info("Executando ferramenta: %s", bloco.name)
                            resultado = self._executar_ferramenta(bloco.name, bloco.input)
                            resultados_tools.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": bloco.id,
                                    "content": json.dumps(resultado, ensure_ascii=False),
                                }
                            )

                    # Adiciona resultados ao histórico e continua o loop
                    self.store.adicionar_mensagem("user", resultados_tools, self.max_mensagens)
                    mensagens = self.store.obter_mensagens()

                else:
                    # stop_reason inesperado
                    logger.warning("stop_reason inesperado: %s", resposta.stop_reason)
                    return "Desculpe, não consegui processar sua solicitação."

    def analisar_board(self) -> str:
        """
        Modo proativo: busca tarefas e solicita resumo matinal ao Claude.
        Usado pelo scheduler.

        Returns:
            Texto do resumo gerado pelo Claude
        """
        prompt_matinal = (
            "Analise o board do Notion e gere um resumo matinal com:\n"
            "1. Tarefas atrasadas (prazo já passou)\n"
            "2. Tarefas em risco (prazo nos próximos 2 dias)\n"
            "3. Tarefas sem responsável definido\n"
            "4. Sugestão de prioridades para hoje\n\n"
            "Seja direto e use emojis para facilitar a leitura."
        )
        return self.responder(prompt_matinal)
