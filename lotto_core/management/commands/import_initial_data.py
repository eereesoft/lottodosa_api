from django.core.management.base import BaseCommand
from lotto_core.models import User


class Command(BaseCommand):
    help = '초기 데이터를 데이터베이스에 저장합니다.'

    def handle(self, *args, **options):
        """
        '운영자' 사용자가 없으면 생성합니다.
        """
        try:
            # '운영자' 사용자가 있으면 가져오고, 없으면 생성합니다.
            user_obj, created = User.objects.get_or_create(
                uid='00000000000000000000',
                defaults={'nick': '운영자'}
            )

            if created:
                self.stdout.write(self.style.SUCCESS("'운영자' 사용자가 성공적으로 생성되었습니다."))
            else:
                self.stdout.write(self.style.WARNING("'운영자' 사용자는 이미 존재합니다."))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'예상치 못한 오류가 발생했습니다: {e}'))
