"""
Módulo de agendamento.
Usa APScheduler para disparar o resumo diário no horário configurado.
"""
import logging
import os
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def iniciar_scheduler(agent, enviar_mensagem_func: callable) -> BackgroundScheduler:
    """
    Configura e inicia o scheduler em background.

    Args:
        agent: Instância do Agent para chamar analisar_board()
        enviar_mensagem_func: Função que envia texto ao Telegram

    Returns:
        Instância do BackgroundScheduler (já iniciado)
    """
    horario = os.getenv("SCHEDULE_TIME", "08:30")
    timezone = os.getenv("TIMEZONE", "America/Sao_Paulo")

    hora, minuto = horario.split(":")

    scheduler = BackgroundScheduler(timezone=timezone)

    def job_resumo_diario():
        logger.info("Scheduler: iniciando resumo diário (%s)", datetime.now().strftime("%H:%M"))
        try:
            resumo = agent.analisar_board()
            enviar_mensagem_func(resumo)
            logger.info("Scheduler: resumo enviado com sucesso.")
        except Exception as e:
            logger.error("Scheduler: erro ao gerar resumo: %s", e)
            try:
                enviar_mensagem_func(
                    f"⚠️ Não consegui gerar o resumo diário.\nErro: {e}"
                )
            except Exception:
                pass

    scheduler.add_job(
        job_resumo_diario,
        trigger=CronTrigger(hour=int(hora), minute=int(minuto)),
        id="resumo_diario",
        name="Resumo diário do board",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "Scheduler iniciado. Próximo resumo: todo dia às %s (%s)",
        horario,
        timezone,
    )
    return scheduler
