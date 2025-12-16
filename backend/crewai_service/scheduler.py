#!/usr/bin/env python3
"""
Scheduler para execucao automatica do pipeline
Roda 2x por semana: Segunda e Quinta as 8h (horario de Brasilia)
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

# Adiciona path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# Configuracao
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Timezone
TIMEZONE = pytz.timezone('America/Sao_Paulo')


def executar_pipeline():
    """Executa o pipeline de analise"""
    logger.info("=" * 60)
    logger.info("SCHEDULER: Iniciando execucao programada")
    logger.info(f"Data/Hora: {datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    try:
        from main_pipeline import PipelineLeilao

        pipeline = PipelineLeilao()
        result = pipeline.executar()

        logger.info(f"Resultado: {result.get('status')}")
        logger.info(f"Stats: {result.get('stats')}")

        # Envia notificacao de conclusao (opcional)
        if result.get('status') == 'success':
            enviar_notificacao_sucesso(result)

    except Exception as e:
        logger.error(f"ERRO no pipeline: {e}")
        enviar_notificacao_erro(str(e))


def enviar_notificacao_sucesso(result):
    """Envia notificacao de sucesso (WhatsApp/Telegram)"""
    stats = result.get('stats', {})

    mensagem = f"""
*Pipeline Leilao Concluido*

Total analisado: {stats.get('total_analisado', 0)}
Recomendados (COMPRAR): {stats.get('recomendados', 0)}

Fonte Caixa: {stats.get('fonte_caixa', 0)}
Fonte Zuk: {stats.get('fonte_zuk', 0)}

Data: {datetime.now(TIMEZONE).strftime('%d/%m/%Y %H:%M')}
    """.strip()

    logger.info(f"Notificacao: {mensagem}")

    # TODO: Integrar com WhatsApp/Telegram
    # from tools.notification_tools import send_whatsapp_alert
    # send_whatsapp_alert(os.getenv("NOTIFY_WHATSAPP"), mensagem)


def enviar_notificacao_erro(erro):
    """Envia notificacao de erro"""
    mensagem = f"""
*ERRO no Pipeline Leilao*

{erro}

Data: {datetime.now(TIMEZONE).strftime('%d/%m/%Y %H:%M')}
    """.strip()

    logger.error(f"Notificacao erro: {mensagem}")


def main():
    """Inicializa scheduler"""
    logger.info("Iniciando Scheduler de Leiloes...")
    logger.info(f"Timezone: {TIMEZONE}")

    scheduler = BlockingScheduler(timezone=TIMEZONE)

    # Agenda para Segunda e Quinta as 8h
    scheduler.add_job(
        executar_pipeline,
        CronTrigger(
            day_of_week='mon,thu',  # Segunda (mon) e Quinta (thu)
            hour=8,
            minute=0,
            timezone=TIMEZONE
        ),
        id='pipeline_leilao',
        name='Pipeline de Analise de Leiloes',
        replace_existing=True
    )

    # Log proximas execucoes
    job = scheduler.get_job('pipeline_leilao')
    if job:
        proxima = job.next_run_time
        logger.info(f"Proxima execucao: {proxima.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    logger.info("Scheduler configurado. Aguardando...")
    logger.info("Execucoes: Segunda e Quinta as 08:00 (Brasilia)")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler encerrado")


def executar_agora():
    """Executa pipeline imediatamente (para testes)"""
    logger.info("Executando pipeline AGORA (modo manual)...")
    executar_pipeline()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Scheduler de Leiloes')
    parser.add_argument('--now', action='store_true', help='Executa imediatamente')
    parser.add_argument('--daemon', action='store_true', help='Roda como daemon')

    args = parser.parse_args()

    if args.now:
        executar_agora()
    else:
        main()
