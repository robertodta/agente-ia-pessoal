"""
Ferramenta para envio de e-mails via Gmail API OAuth2.
Reutiliza o mesmo token.json do CalendarTools.
"""
import base64
import json
import logging
import os
from email.mime.text import MIMEText

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


class GmailTools:
    """Encapsula envio de e-mails via Gmail."""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.service = self._autenticar()

    def _autenticar(self):
        """
        Autentica com OAuth2. Reutiliza token.json se disponível.
        Os escopos incluem Calendar para que o token seja compatível.
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
        return build("gmail", "v1", credentials=creds)

    def enviar_email(self, destinatario: str, assunto: str, corpo: str) -> dict:
        """
        Envia um e-mail via Gmail.

        Args:
            destinatario: Endereço de e-mail do destinatário
            assunto: Assunto do e-mail
            corpo: Corpo do e-mail em texto simples

        Returns:
            Dict com 'id' da mensagem enviada
        """
        mensagem = MIMEText(corpo)
        mensagem["to"] = destinatario
        mensagem["subject"] = assunto
        raw = base64.urlsafe_b64encode(mensagem.as_bytes()).decode()
        try:
            resultado = (
                self.service.users()
                .messages()
                .send(userId="me", body={"raw": raw})
                .execute()
            )
            logger.info("E-mail enviado para %s. ID: %s", destinatario, resultado.get("id"))
            return {"id": resultado.get("id")}
        except HttpError as e:
            logger.error("Erro ao enviar e-mail: %s", e)
            raise
