import logging
import time
import signal

from django.core.management.base import BaseCommand
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from lotto_core.jobs import sync_round_job, sync_stores_job

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "백그라운드 스케줄러를 실행합니다."

    def handle(self, *args, **options):
        scheduler = BackgroundScheduler(timezone='Asia/Seoul')
        scheduler.add_jobstore(DjangoJobStore(), "default")

        logger.info("스케줄러 초기화: 모든 기존 작업을 삭제하고 새로 등록합니다.")
        scheduler.remove_all_jobs()

        # 1. 최신 회차 정보 동기화 작업 등록
        scheduler.add_job(
            sync_round_job,
            trigger='cron',
            day_of_week='sat',
            hour='20',
            minute='40',
            id='sync_round_job',
            name='최신 회차 정보 동기화',
            replace_existing=True,
        )
        logger.info("스케줄러: '최신 회차 정보 동기화' 작업이 등록되었습니다. (매주 토 20:40)")

        # 2. 판매점 정보 동기화 작업 등록
        scheduler.add_job(
            sync_stores_job,
            trigger='cron',
            day_of_week='tue',
            hour='10',
            minute='00',
            id='sync_stores_job1',
            name='판매점 정보 동기화',
            replace_existing=True,
        )
        logger.info("스케줄러: '판매점 정보 동기화 1' 작업이 등록되었습니다. (매주 화 10:00)")

        scheduler.add_job(
            sync_stores_job,
            trigger='cron',
            day_of_week='sat',
            hour='10',
            minute='00',
            id='sync_stores_job2',
            name='판매점 정보 동기화2',
            replace_existing=True,
        )
        logger.info("스케줄러: '판매점 정보 동기화 2' 작업이 등록되었습니다. (매주 토 10:00)")

        def shutdown_scheduler(signum, frame):
            logger.info("종료 시그널을 수신했습니다. 스케줄러를 안전하게 종료합니다...")
            scheduler.shutdown()

        signal.signal(signal.SIGINT, shutdown_scheduler)
        signal.signal(signal.SIGTERM, shutdown_scheduler)

        scheduler.start()
        logger.info("스케줄러가 시작되었습니다. 종료하려면 Ctrl+C를 누르세요.")

        # 스케줄러가 백그라운드에서 계속 실행되도록 메인 스레드를 유지합니다.
        while True:
            time.sleep(1)
