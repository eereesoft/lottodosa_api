from django.core.management.base import BaseCommand, CommandError
from lotto_core.utils.round_parser import RoundParser
from lotto_core.utils.wins_parser import WinsParser
import time


class Command(BaseCommand):
    help = '동행복권 사이트에서 최신 회차 정보를 가져와 데이터베이스에 동기화합니다.'

    def handle(self, *args, **options):
        """
        동행복권 사이트에서 최신 회차 정보를 폴링하여 가져옵니다.
        새로운 회차 정보가 발표되면 해당 회차의 정보와 당첨 판매점 정보를 DB에 동기화합니다.
        주로 토요일 저녁 로또 추첨 시간에 실행되도록 스케줄링됩니다.
        """
        try:
            self.stdout.write(self.style.SUCCESS('>> 최신 로또 회차 정보 동기화를 시작합니다.'))

            round_parser = RoundParser(None)
            last_round = round_parser.get_last_round()
            next_round = last_round + 1
            self.stdout.write(f"# 현재 마지막 회차: {last_round}. 다음 회차({next_round}) 파싱을 시도합니다.")

            # 추첨 발표 시간(토요일 20:45) 이후, 새 회차 정보가 올라올 때까지 1분 간격으로 최대 200회 시도합니다.
            for i in range(200):
                round_parser.parse_latest_round()
                if round_parser.round_no != next_round:
                    self.stdout.write(f"# 아직 다음 회차({next_round}) 정보가 없습니다. 1분 후 재시도합니다... (시도 {i+1}/200)")
                    time.sleep(60) # 1분 대기
                else:
                    self.stdout.write(self.style.SUCCESS(f"# 다음 회차({next_round}) 정보를 성공적으로 가져왔습니다."))
                    round_parser.upload_round()

                    self.stdout.write(f"# 회차({next_round})의 당첨 판매점 정보 동기화를 시작합니다.")
                    wins_parser = WinsParser()
                    wins_parser.parse_wins(next_round)
                    wins_parser.upload_wins()
                    self.stdout.write(self.style.SUCCESS(f"# 회차({next_round})의 당첨 판매점 정보 동기화가 완료되었습니다."))
                    
                    # 성공적으로 동기화를 마쳤으므로 루프를 종료합니다.
                    break

            self.stdout.write(self.style.SUCCESS('>> 최신 로또 회차 정보 동기화 작업이 성공적으로 완료되었습니다.'))

        except Exception as e:
            raise CommandError(f'회차 정보 동기화 중 오류가 발생했습니다: {e}')