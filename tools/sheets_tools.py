"""
Ferramenta para Google Sheets via OAuth2.
Reutiliza o mesmo token.json do CalendarTools e GmailTools.
Requer que a Google Sheets API esteja habilitada no Google Cloud Console.
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
    "https://www.googleapis.com/auth/spreadsheets",
]
TOKEN_PATH = "token.json"
CREDENTIALS_PATH = "credentials.json"


class SheetsTools:
    """Encapsula leitura e escrita no Google Sheets."""

    def __init__(self, client_id: str, client_secret: str, spreadsheet_id: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.spreadsheet_id = spreadsheet_id
        self.service = self._autenticar()

    def _autenticar(self):
        """
        Autentica com OAuth2. Reutiliza token.json se disponível.
        ATENÇÃO: ao adicionar Sheets ao escopo, será necessário re-autenticar
        (deletar token.json e rodar novamente para gerar novo token com os novos escopos).
        """
        creds = None
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
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
        return build("sheets", "v4", credentials=creds)

    def ler_planilha(self, intervalo: str) -> list[list]:
        """
        Lê valores de um intervalo da planilha.

        Args:
            intervalo: Intervalo no formato A1 notation, ex: "Sheet1!A1:D10"

        Returns:
            Lista de listas com os valores. Lista vazia se não houver dados.
        """
        try:
            resultado = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=self.spreadsheet_id, range=intervalo)
                .execute()
            )
            valores = resultado.get("values", [])
            logger.info("Sheets: leu %d linhas de '%s'.", len(valores), intervalo)
            return valores
        except HttpError as e:
            logger.error("Erro ao ler planilha: %s", e)
            raise

    def escrever_planilha(self, intervalo: str, valores: list[list]) -> dict:
        """
        Escreve valores em um intervalo da planilha.

        Args:
            intervalo: Intervalo no formato A1 notation, ex: "Sheet1!A2:B2"
            valores: Lista de listas com os valores a escrever,
                     ex: [["Nome", "Status"], ["Tarefa 1", "A fazer"]]

        Returns:
            Dict com informações da atualização (ex: {'updatedCells': 4})
        """
        corpo = {"values": valores}
        try:
            resultado = (
                self.service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=self.spreadsheet_id,
                    range=intervalo,
                    valueInputOption="USER_ENTERED",
                    body=corpo,
                )
                .execute()
            )
            logger.info(
                "Sheets: escreveu %d célula(s) em '%s'.",
                resultado.get("updatedCells", 0),
                intervalo,
            )
            return resultado
        except HttpError as e:
            logger.error("Erro ao escrever na planilha: %s", e)
            raise
