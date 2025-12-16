from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)


def sync_round_job():
    """
    매주 토요일 저녁에 실행되는 스케줄링 작업입니다.
    `round_sync` 관리자 커맨드를 호출하여 최신 회차 정보를 동기화합니다.
    """
    logger.info(">> 스케줄러: 최신 회차 정보 동기화 작업을 시작합니다.")
    try:
        # 'round_sync' 관리자 커맨드를 실행합니다.
        call_command('round_sync')
        logger.info(">> 스케줄러: 최신 회차 정보 동기화 작업이 성공적으로 완료되었습니다.")
    except Exception as e:
        logger.error(f">> 스케줄러: 최신 회차 정보 동기화 작업 중 오류 발생: {e}", exc_info=True)

def sync_stores_job():
    """
    매주 화요일에 실행되는 스케줄링 작업입니다.
    `store_sync` 관리자 커맨드를 호출하여 전체 판매점 정보를 동기화합니다.
    """
    logger.info(">> 스케줄러: 판매점 정보 동기화 작업을 시작합니다.")
    try:
        # 'store_sync' 관리자 커맨드를 실행합니다.
        call_command('store_sync')
        logger.info(">> 스케줄러: 판매점 정보 동기화 작업이 성공적으로 완료되었습니다.")
    except Exception as e:
        logger.error(f">> 스케줄러: 판매점 정보 동기화 작업 중 오류 발생: {e}", exc_info=True)