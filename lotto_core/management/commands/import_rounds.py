import pandas as pd
from django.core.management.base import BaseCommand
from lotto_core.models import Round
from datetime import datetime


class Command(BaseCommand):
    help = 'CSV 파일로부터 로또 회차 정보(Round)를 가져와 데이터베이스에 저장합니다.'

    def add_arguments(self, parser):
        # 명령어 실행 시 CSV 파일 경로를 인자로 받습니다.
        parser.add_argument('csv_file', type=str, help='회차 정보가 담긴 CSV 파일의 경로')

    def handle(self, *args, **options):
        file_path = options['csv_file']
        
        self.stdout.write(self.style.SUCCESS(f'"{file_path}" 파일에서 데이터 임포트를 시작합니다...'))

        try:
            # Pandas를 사용하여 CSV 파일을 DataFrame으로 읽어옵니다. CSV에 헤더가 있다고 가정합니다.
            df = pd.read_csv(file_path, header=0, encoding='utf-8')

            rounds_to_create = []
            # DataFrame의 각 행을 순회합니다.
            for index, r in df.iterrows():
                # CSV 파일의 각 열이 어떤 데이터인지에 따라 인덱스를 조정해야 합니다.
                # 예: rid, date, number1, number2, ...
                try:
                    # CSV의 'sid' 컬럼 값을 가져옵니다. 컬럼명이 다르면 이 부분을 수정해야 합니다.
                    rid = int(r.rid)

                    # rid가 이미 DB에 존재하면 건너뜁니다.
                    if Round.objects.filter(rid=rid).exists():
                        self.stdout.write(self.style.WARNING(f'회차 {rid}는 이미 존재하므로 건너뜁니다.'))
                        continue

                    round_obj = Round(
                        rid=rid,
                        date=pd.to_datetime(r.date).date(),
                        number1=int(r.number1),
                        number2=int(r.number2),
                        number3=int(r.number3),
                        number4=int(r.number4),
                        number5=int(r.number5),
                        number6=int(r.number6),
                        number7=int(r.number7),
                        count1=int(r.count1),
                        count2=int(r.count2),
                        count3=int(r.count3),
                        count4=int(r.count4),
                        count5=int(r.count5),
                        count_auto=int(r.count_auto),
                        count_hauto=int(r.count_hauto),
                        count_manual=int(r.count_manual),
                        amount1=int(r.amount1),
                        amount2=int(r.amount2),
                        amount3=int(r.amount3),
                        amount4=int(r.amount4),
                        amount5=int(r.amount5),
                        allamount1=int(r.allamount1),
                        allamount2=int(r.allamount2),
                        allamount3=int(r.allamount3),
                        allamount4=int(r.allamount4),
                        allamount5=int(r.allamount5),
                        sales=int(r.sales),
                        drawing1=int(r.drawing1),
                        drawing2=int(r.drawing2),
                        drawing3=int(r.drawing3),
                        drawing4=int(r.drawing4),
                        drawing5=int(r.drawing5),
                        drawing6=int(r.drawing6),
                        drawing7=int(r.drawing7),
                        practice1=int(r.practice1),
                        practice2=int(r.practice2),
                        practice3=int(r.practice3),
                        practice4=int(r.practice4),
                        practice5=int(r.practice5),
                        practice6=int(r.practice6),
                        practice7=int(r.practice7),
                        rule_ballset=int(r.rule_ballset),
                        rule_garo=int(r.rule_garo),
                        rule_machine=int(r.rule_machine),
                    )
                    rounds_to_create.append(round_obj)

                except (IndexError, ValueError, TypeError) as e:
                    self.stderr.write(self.style.ERROR(f'오류 발생 (행 번호: {index + 1}, 데이터: {r.to_list()}): {e}'))
                    # 오류가 발생한 행은 건너뛰고 계속 진행
                    continue
            
            # 여러 객체를 한 번의 쿼리로 생성하여 성능을 향상시킵니다.
            if rounds_to_create:
                Round.objects.bulk_create(rounds_to_create)
                self.stdout.write(self.style.SUCCESS(f'{len(rounds_to_create)}개의 새로운 회차 정보가 성공적으로 추가되었습니다.'))
            else:
                self.stdout.write(self.style.SUCCESS('추가할 새로운 데이터가 없습니다.'))

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f'파일을 찾을 수 없습니다: "{file_path}"'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'예상치 못한 오류가 발생했습니다: {e}'))
