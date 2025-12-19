from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)


def sync_round_job():
    """
    매주 토요일 저녁에 실행되는 스케줄링 작업입니다.
    `sync_round` 관리자 커맨드를 호출하여 최신 회차 정보를 동기화합니다.
    """
    logger.info(">> 스케줄러: 최신 회차 정보 동기화 작업을 시작합니다.")
    try:
        # 'sync_round' 관리자 커맨드를 실행합니다.
        call_command('sync_round')
        logger.info(">> 스케줄러: 최신 회차 정보 동기화 작업이 성공적으로 완료되었습니다.")
    except Exception as e:
        logger.error(f">> 스케줄러: 최신 회차 정보 동기화 작업 중 오류 발생: {e}", exc_info=True)

def sync_stores_job():
    """
    매주 화요일에 실행되는 스케줄링 작업입니다.
    `sync_store` 관리자 커맨드를 호출하여 전체 판매점 정보를 동기화합니다.
    """
    logger.info(">> 스케줄러: 판매점 정보 동기화 작업을 시작합니다.")
    try:
        # 'sync_store' 관리자 커맨드를 실행합니다.
        call_command('sync_store')
        logger.info(">> 스케줄러: 판매점 정보 동기화 작업이 성공적으로 완료되었습니다.")
    except Exception as e:
        logger.error(f">> 스케줄러: 판매점 정보 동기화 작업 중 오류 발생: {e}", exc_info=True)

def sync_cafe_job():
    """
    매주 월요일 오전 9시에 실행되는 스케줄링 작업입니다.
    `sync_cafe` 관리자 커맨드를 호출하여 카페 정보를 동기화합니다.
    """
    logger.info(">> 스케줄러: 카페 정보 동기화 작업을 시작합니다.")
    try:
        # 'sync_cafe' 관리자 커맨드를 실행합니다.
        call_command('sync_cafe')
        logger.info(">> 스케줄러: 카페 정보 동기화 작업이 성공적으로 완료되었습니다.")
    except Exception as e:
        logger.error(f">> 스케줄러: 카페 정보 동기화 작업 중 오류 발생: {e}", exc_info=True)
