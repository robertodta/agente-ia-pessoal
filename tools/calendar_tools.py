"""
Ferramenta para Google Calendar via OAuth2.
Na primeira execução, abre o browser para autenticação.
O token é salvo em token.json e renovado automaticamente.
"""
import json
import logging
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.send",
]
TOKEN_PATH = "token.json"
CREDENTIALS_PATH = "credentials.json"


class CalendarTools:
    """Encapsula operações do Google Calendar."""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.service = self._autenticar()

    def _autenticar(self):
        """
        Autentica com OAuth2. Usa token.json se disponível,
        caso contrário abre o browser para autorização.
        """
        creds = None
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Cria credentials.json temporário a partir das variáveis de ambiente
                creds_data = {
                    "installed": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                }
                with open(CREDENTIALS_PATH, "w") as f:
                    json.dump(creds_data, f)
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
        return build("calendar", "v3", credentials=creds)

    def criar_evento(
        self,
        titulo: str,
        data: str,
        hora_inicio: str,
        hora_fim: str,
        descricao: str = "",
    ) -> dict:
        """
        Cria um evento no Google Calendar.

        Args:
            titulo: Nome do evento
            data: Data no formato YYYY-MM-DD
            hora_inicio: Horário de início no formato HH:MM
            hora_fim: Horário de fim no formato HH:MM
            descricao: Descrição opcional

        Returns:
            Dict com 'id' e 'htmlLink' do evento criado
        """
        evento = {
            "summary": titulo,
            "description": descricao,
            "start": {"dateTime": f"{data}T{hora_inicio}:00", "timeZone": "America/Sao_Paulo"},
            "end": {"dateTime": f"{data}T{hora_fim}:00", "timeZone": "America/Sao_Paulo"},
        }
        try:
            resultado = self.service.events().insert(calendarId="primary", body=evento).execute()
            logger.info("Evento criado: %s (%s)", titulo, resultado.get("id"))
            return {"id": resultado.get("id"), "htmlLink": resultado.get("htmlLink")}
        except HttpError as e:
            logger.error("Erro ao criar evento no Calendar: %s", e)
            raise

    def listar_eventos(self, data_inicio: str, data_fim: str) -> list[dict]:
        """
        Lista eventos do calendário em um período.

        Args:
            data_inicio: Data início no formato YYYY-MM-DD
            data_fim: Data fim no formato YYYY-MM-DD

        Returns:
            Lista de dicts com: titulo, inicio, fim, descricao
        """
        time_min = f"{data_inicio}T00:00:00-03:00"
        time_max = f"{data_fim}T23:59:59-03:00"
        try:
            resultado = (
                self.service.events()
                .list(
                    calendarId="primary",
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            eventos = []
            for item in resultado.get("items", []):
                eventos.append(
                    {
                        "titulo": item.get("summary", ""),
                        "inicio": item.get("start", {}).get("dateTime", item.get("start", {}).get("date", "")),
                        "fim": item.get("end", {}).get("dateTime", item.get("end", {}).get("date", "")),
                        "descricao": item.get("description", ""),
                    }
                )
            logger.info("Calendar: %d eventos encontrados.", len(eventos))
            return eventos
        except HttpError as e:
            logger.error("Erro ao listar eventos: %s", e)
            raise
