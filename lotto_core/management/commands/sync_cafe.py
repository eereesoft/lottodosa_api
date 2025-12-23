from django.core.management.base import BaseCommand
from lotto_core.utils.cafe_parser import CafeParser
from lotto_core import services
from django.db import transaction
import time
import json
import os
from django.utils import timezone


class Command(BaseCommand):
    help = '네이버 카페를 파싱하여 최신 회차의 상세 정보(모의번호, 추첨기, 볼세트 등)를 동기화합니다.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('>> 카페 데이터 동기화를 시작합니다.'))

        try:
            # DB의 최신 회차 정보를 먼저 가져옵니다.
            db_last_round = services.get_last_round()
            if not db_last_round:
                self.stdout.write(self.style.ERROR('DB에 저장된 회차 정보가 없습니다.'))
                return

            self.stdout.write(f"DB 최신 회차: {db_last_round.rid}회. 해당 회차의 카페 정보 파싱을 시도합니다.")

            # 최신 회차 정보가 올라올 때까지 10분 간격으로 최대 100회 시도합니다.
            for i in range(100):
                parser = None
                try:
                    # 1. CafeParser를 활용해 최신 차수 cafe 게시글 parse
                    parser = CafeParser()
                    parser.login()
                    parser.parse_latest_round()

                    cafe_info = parser.round_info
                    if not cafe_info:
                        raise Exception('파싱된 카페 정보가 없습니다.')

                    cafe_rid = int(cafe_info['rid'])

                    # 2. DB의 최신 회차와 파싱한 회차가 일치하는지 확인
                    if db_last_round.rid == cafe_rid:
                        self.stdout.write(self.style.SUCCESS(f'# {i+1}차 시도: {cafe_rid}회차 카페 정보를 찾았습니다. 데이터 검증 및 동기화를 시작합니다.'))

                        # 3. 당첨번호 비교 (number1 ~ number7)
                        cafe_numbers = [int(cafe_info[f'number{j}']) for j in range(1, 8)]
                        db_numbers = [
                            db_last_round.number1, db_last_round.number2, db_last_round.number3,
                            db_last_round.number4, db_last_round.number5, db_last_round.number6,
                            db_last_round.number7
                        ]

                        if cafe_numbers != db_numbers:
                            self.stdout.write(self.style.WARNING('당첨 번호 불일치. 동기화를 중단합니다.'))
                            self.stdout.write(f'DB: {db_numbers}')
                            self.stdout.write(f'Cafe: {cafe_numbers}')
                            return # 번호가 다르면 재시도할 필요가 없으므로 종료

                        # 4. 정보 갱신
                        self.stdout.write(self.style.SUCCESS(f'{cafe_rid}회차 상세 정보를 업데이트합니다.'))
                        with transaction.atomic():
                            for j in range(1, 8):
                                setattr(db_last_round, f'drawing{j}', int(cafe_info[f'drawing{j}']))
                                setattr(db_last_round, f'practice{j}', int(cafe_info[f'practice{j}']))

                            db_last_round.rule_ballset = int(cafe_info['rule_ballset'])
                            db_last_round.rule_machine = int(cafe_info['rule_machine'])

                            garo_val = cafe_info.get('rule_garo', '')
                            if garo_val == '가로':
                                db_last_round.rule_garo = 1
                            elif garo_val == '세로':
                                db_last_round.rule_garo = 2
                            else:
                                db_last_round.rule_garo = 0

                            db_last_round.save()

                        # dbsync.json 업데이트
                        try:
                            file_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'dbsync.json')

                            data = {}
                            if os.path.exists(file_path):
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    try:
                                        data = json.load(f)
                                    except json.JSONDecodeError:
                                        pass

                            data['cafe'] = timezone.now().strftime('%Y-%m-%d')

                            with open(file_path, 'w', encoding='utf-8') as f:
                                json.dump(data, f, indent=4, ensure_ascii=False)

                            self.stdout.write(self.style.SUCCESS("# dbsync.json의 round 항목을 업데이트했습니다."))
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"# dbsync.json 업데이트 실패: {e}"))

                        self.stdout.write(self.style.SUCCESS('>> 성공적으로 업데이트되었습니다.'))
                        break # 성공했으므로 루프 종료

                    self.stdout.write(self.style.WARNING(f'# {i+1}차 시도: 회차 번호 불일치 (DB: {db_last_round.rid} != Cafe: {cafe_rid}). 10분 후 재시도합니다...'))
                    time.sleep(600) # 10분 대기

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'# {i+1}차 시도 중 오류 발생: {e}'))
                    if i < 99:
                        self.stdout.write(self.style.WARNING('10분 후 재시도합니다...'))
                        time.sleep(600)
                finally:
                    # 파서 및 드라이버 종료
                    if parser and hasattr(parser, 'driver'):
                        parser.driver.quit()
            
            else: # for-else: 루프가 break 없이 완료된 경우
                self.stdout.write(self.style.ERROR('>> 100회 시도 후에도 카페 데이터 동기화에 실패했습니다.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'예상치 못한 오류 발생: {e}'))
