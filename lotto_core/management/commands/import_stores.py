import pandas as pd
import numpy as np
from django.core.management.base import BaseCommand
from lotto_core.models import Store


class Command(BaseCommand):
    help = 'CSV 파일로부터 판매점 정보(Store)를 가져와 데이터베이스에 저장합니다.'

    def add_arguments(self, parser):
        # 명령어 실행 시 CSV 파일 경로를 인자로 받습니다.
        parser.add_argument('csv_file', type=str, help='판매점 정보가 담긴 CSV 파일의 경로')

    def handle(self, *args, **options):
        file_path = options['csv_file']
        self.stdout.write(self.style.SUCCESS(f'"{file_path}" 파일에서 판매점 데이터 임포트를 시작합니다...'))

        try:
            # Pandas를 사용하여 CSV 파일을 DataFrame으로 읽어옵니다. CSV에 헤더가 있다고 가정합니다.
            df = pd.read_csv(file_path, header=0, encoding='utf-8')

            # Pandas에서 빈 값을 나타내는 NaN을 Python의 None으로 변경합니다.
            df = df.replace({np.nan: None})

            # 데이터베이스에 이미 존재하는 판매점 ID를 미리 조회하여 성능을 최적화합니다.
            existing_sids = set(Store.objects.values_list('sid', flat=True))

            stores_to_create = []
            store_obj = Store(
                sid=51100000,
                enabled=True,
                sname='인터넷 복권판매사이트',
                phone='02-1588-6450',
                addr1='',
                addr2='',
                addr3='',
                addr4='동행복권(dhlottery.co.kr)',
                addr_doro='동행복권(dhlottery.co.kr)',
                geo_e=float(127.015785),
                geo_n=float(37.482063),
            )
            stores_to_create.append(store_obj)
            for index, r in df.iterrows():
                try:
                    # CSV의 'sid' 컬럼 값을 가져옵니다. 컬럼명이 다르면 이 부분을 수정해야 합니다.
                    sid = int(r.sid)

                    # 이미 존재하는 판매점이면 건너뜁니다.
                    if sid in existing_sids:
                        self.stdout.write(self.style.WARNING(f'판매점 ID {sid}는 이미 존재하므로 건너뜁니다.'))
                        continue

                    store_obj = Store(
                        sid=sid,
                        enabled=r.get('enabled', True), # 'enabled' 컬럼이 없으면 기본값 True
                        sname=r.sname,
                        phone=r.get('phone') or '',
                        addr1=r.get('addr1') or '',
                        addr2=r.get('addr2') or '',
                        addr3=r.get('addr3') or '',
                        addr4=r.get('addr4') or '',
                        addr_doro=r.get('addr_doro') or '',
                        geo_e=float(r.get('geo_e') or 0.0),
                        geo_n=float(r.get('geo_n') or 0.0),
                    )
                    stores_to_create.append(store_obj)

                except (KeyError, ValueError, TypeError) as e:
                    self.stderr.write(self.style.ERROR(f'오류 발생 (행 번호: {index + 1}, 데이터: {r.to_dict()}): {e}'))
                    # 오류가 발생한 행은 건너뛰고 계속 진행
                    continue

            # 여러 객체를 한 번의 쿼리로 생성하여 성능을 향상시킵니다.
            if stores_to_create:
                Store.objects.bulk_create(stores_to_create)
                self.stdout.write(self.style.SUCCESS(f'{len(stores_to_create)}개의 새로운 판매점 정보가 성공적으로 추가되었습니다.'))
            else:
                self.stdout.write(self.style.SUCCESS('추가할 새로운 데이터가 없습니다.'))

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f'파일을 찾을 수 없습니다: "{file_path}"'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'예상치 못한 오류가 발생했습니다: {e}'))