from django.core.management.base import BaseCommand, CommandError
from lotto_core.utils.store_parser import StoreParser


class Command(BaseCommand):
    help = '전체 로또 판매점 정보를 가져와 데이터베이스에 동기화합니다.'

    def handle(self, *args, **options):
        """
        동행복권 사이트에서 전체 로또 판매점 정보를 스크래핑하여 데이터베이스와 동기화합니다.
        - 신규 판매점은 추가합니다.
        - 정보가 변경된 판매점은 업데이트합니다.
        - 없어진 판매점은 비활성화(enabled=False) 처리합니다.
        """
        try:
            self.stdout.write(self.style.SUCCESS('>> 로또 판매점 정보 동기화를 시작합니다.'))

            parser = StoreParser()
            parser.parse_store()
            parser.upload_store()

            self.stdout.write(self.style.SUCCESS('>> 성공적으로 판매점 정보를 동기화했습니다.'))

        except Exception as e:
            raise CommandError(f'판매점 정보 동기화 중 오류가 발생했습니다: {e}')