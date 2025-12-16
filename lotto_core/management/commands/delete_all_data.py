from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connection, transaction


class Command(BaseCommand):
    help = 'lotto_core 앱의 모든 모델에서 모든 데이터를 삭제하고, auto-increment 값을 초기화합니다.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('경고: 이 명령어는 lotto_core 앱의 모든 테이블에서 모든 데이터를 영구적으로 삭제하고, ID 시퀀스를 초기화합니다.'))
        confirmation = input('정말로 모든 데이터를 삭제하시겠습니까? (yes/no): ')

        if confirmation.lower() != 'yes':
            self.stdout.write(self.style.SUCCESS('데이터 삭제를 취소했습니다.'))
            return

        self.stdout.write(self.style.WARNING('데이터 삭제를 시작합니다...'))

        # lotto_core 앱의 모든 모델을 가져옵니다.
        app_models = list(apps.get_app_config('lotto_core').get_models())

        # 외래 키 제약 조건으로 인한 오류를 피하기 위해 역순으로 삭제를 시도합니다.
        # 일반적으로 Django의 CASCADE 설정이 되어 있다면 순서는 크게 중요하지 않지만,
        # 안전을 위해 의존성이 낮은 모델부터 삭제하는 것이 좋습니다.
        # 여기서는 간단히 모든 모델을 순회하며 삭제합니다.
        with transaction.atomic():
            with connection.cursor() as cursor:
                for model in reversed(app_models): # 의존성이 있는 모델이 먼저 삭제되지 않도록 역순으로 시도
                    table_name = model._meta.db_table
                    model_name = model.__name__
                    
                    self.stdout.write(f'  - {model_name} 테이블 처리 중...')
                    if connection.vendor == 'sqlite':
                        # SQLite: TRUNCATE를 지원하지 않으므로 DELETE 후 시퀀스를 수동으로 초기화합니다.
                        cursor.execute(f'DELETE FROM "{table_name}"')
                        cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table_name}'")
                    elif connection.vendor == 'postgresql':
                        # PostgreSQL: TRUNCATE ... RESTART IDENTITY CASCADE를 사용하여 테이블과 시퀀스를 초기화합니다.
                        cursor.execute(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE')
                    else: # MySQL 등
                        # MySQL: TRUNCATE TABLE을 사용하여 테이블과 auto_increment를 초기화합니다.
                        cursor.execute(f'TRUNCATE TABLE `{table_name}`')

        self.stdout.write(self.style.SUCCESS('모든 데이터 삭제 및 시퀀스 초기화가 완료되었습니다.'))
