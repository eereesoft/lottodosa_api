# round_parser.py

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from lotto_core.models import Round
from django.db.models import Max

FORMAT_STRING = '%Y.%m.%d'


class RoundParser:

    BYWIN_URL = 'https://dhlottery.co.kr/gameResult.do?method=byWin'
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Referer': 'https://dhlottery.co.kr/gameResult.do?method=byWin'
    }

    def __init__(self, round):
        self.round_no = 0
        self.round_info = None
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def _clean_amount(self, s: str) -> str:
        if s is None:
            return ''
        return s.replace(',', '').replace('원', '').strip()

    def get_last_round(self):
        """
        Django DB의 'Round' 테이블에서 가장 큰 회차 번호(rid)를 가져옵니다.
        """
        print("## get_last_round")
        # Round.objects.aggregate(Max('rid'))는 {'rid__max': <값>} 형태의 딕셔너리를 반환합니다.
        # 테이블이 비어있으면 {'rid__max': None}을 반환합니다.
        max_rid_data = Round.objects.aggregate(max_rid=Max('rid'))
        last_round = max_rid_data.get('max_rid')

        if last_round is None:
            print("# 'Round' 테이블에 데이터가 없습니다. 0을 반환합니다.")
            return 0
        else:
            return last_round

    def parse_latest_round(self):
        print(f'## parse_latest_round')
        resp = self.session.get(self.BYWIN_URL)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        # 회차
        round_el = soup.select_one('.win_result h4 strong')
        if round_el:
            self.round_no = int(round_el.get_text(strip=True).replace('회', '').strip())
            if self.round_no == 0:
                raise ValueError("# Could not determine the latest round number.")
            print(f'# current latest round: {self.round_no}')

        # 날짜
        date_el = soup.select_one('.win_result p')
        date = ''
        if date_el:
            date = date_el.get_text(strip=True).replace('(', '').replace('년 ', '.').replace('월 ', '.').replace('일 추첨)', '').strip()

        # 번호
        nums = soup.select('.win_result .nums .num p span')
        n = [el.get_text(strip=True) for el in nums]
        while len(n) < 7:
            n.append('')

        # 상세 (tbl_data 테이블의 각 등수 행)
        rows = soup.select('.tbl_data tbody tr')
        amounts = [''] * 5
        counts = [''] * 5
        means = [''] * 5
        if len(rows) >= 5:
            for i in range(5):
                items = rows[i].find_all('td')
                if len(items) >= 4:
                    amounts[i] = self._clean_amount(items[1].get_text())
                    counts[i] = items[2].get_text().replace(',', '').strip()
                    means[i] = self._clean_amount(items[3].get_text())
                # auto/manual/hauto info sometimes in items[5]
            # 자동/수동 정보
            auto = manual = hauto = '0'
            first_items = rows[0].find_all('td')
            if len(first_items) > 5:
                info_text = first_items[5].get_text(separator='\n')
                for line in info_text.splitlines():
                    line = line.strip()
                    if line.startswith('자동'):
                        auto = line.replace('자동', '').strip()
                    if line.startswith('수동'):
                        manual = line.replace('수동', '').strip()
                    if line.startswith('반자동'):
                        hauto = line.replace('반자동', '').strip()
        else:
            auto = manual = hauto = '0'

        # 총판매금액
        sales_el = soup.select_one('.list_text_common li strong')
        sales = self._clean_amount(sales_el.get_text() if sales_el else '')

        # 딕셔너리로 저장
        self.round_info = {
            'round': self.round_no,
            'date': date,
            'number1': n[0], 'number2': n[1], 'number3': n[2], 'number4': n[3], 'number5': n[4], 'number6': n[5], 'number7': n[6],
            'count1': counts[0], 'count2': counts[1], 'count3': counts[2], 'count4': counts[3], 'count5': counts[4],
            'amount1': amounts[0], 'amount2': amounts[1], 'amount3': amounts[2], 'amount4': amounts[3], 'amount5': amounts[4],
            'allamount1': means[0], 'allamount2': means[1], 'allamount3': means[2], 'allamount4': means[3], 'allamount5': means[4],
            'auto': auto, 'manual': manual, 'hauto': hauto,
            'sales': sales
        }

    def parse_round(self, round): # for manual
        self.round_no = round
        print(f'## parse_round: {self.round_no}')
        url = f'{self.BYWIN_URL}&drwNo={self.round_no}'
        resp = self.session.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        # 날짜
        date_el = soup.select_one('.win_result p')
        date = ''
        if date_el:
            date = date_el.get_text(strip=True).replace('(', '').replace('년 ', '.').replace('월 ', '.').replace('일 추첨)', '').strip()

        # 번호
        nums = soup.select('.win_result .nums .num p span')
        n = [el.get_text(strip=True) for el in nums]
        while len(n) < 7:
            n.append('')

        # 상세 (tbl_data 테이블의 각 등수 행)
        rows = soup.select('.tbl_data tbody tr')
        amounts = [''] * 5
        counts = [''] * 5
        means = [''] * 5
        if len(rows) >= 5:
            for i in range(5):
                items = rows[i].find_all('td')
                if len(items) >= 4:
                    amounts[i] = self._clean_amount(items[1].get_text())
                    counts[i] = items[2].get_text().replace(',', '').strip()
                    means[i] = self._clean_amount(items[3].get_text())
                # auto/manual/hauto info sometimes in items[5]
            # 자동/수동 정보
            auto = manual = hauto = '0'
            first_items = rows[0].find_all('td')
            if len(first_items) > 5:
                info_text = first_items[5].get_text(separator='\n')
                for line in info_text.splitlines():
                    line = line.strip()
                    if line.startswith('자동'):
                        auto = line.replace('자동', '').strip()
                    if line.startswith('수동'):
                        manual = line.replace('수동', '').strip()
                    if line.startswith('반자동'):
                        hauto = line.replace('반자동', '').strip()
        else:
            auto = manual = hauto = '0'

        # 총판매금액
        sales_el = soup.select_one('.list_text_common li strong')
        sales = self._clean_amount(sales_el.get_text() if sales_el else '')

        # 딕셔너리로 저장
        self.round_info = {
            'round': self.round_no,
            'date': date,
            'number1': n[0], 'number2': n[1], 'number3': n[2], 'number4': n[3], 'number5': n[4], 'number6': n[5], 'number7': n[6],
            'count1': counts[0], 'count2': counts[1], 'count3': counts[2], 'count4': counts[3], 'count5': counts[4],
            'amount1': amounts[0], 'amount2': amounts[1], 'amount3': amounts[2], 'amount4': amounts[3], 'amount5': amounts[4],
            'allamount1': means[0], 'allamount2': means[1], 'allamount3': means[2], 'allamount4': means[3], 'allamount5': means[4],
            'auto': auto, 'manual': manual, 'hauto': hauto,
            'sales': sales
        }

    def upload_round(self):
        print(f'## upload_round: {self.round_no}')

        round_obj, created = Round.objects.get_or_create(
            rid=self.round_no, # 회차
            date=datetime.strptime(str(self.round_info['date']), FORMAT_STRING).date(), # 추첨일
            number1=int(self.round_info['number1']), # 당첨번호(오름차순): 1
            number2=int(self.round_info['number2']), # 당첨번호(오름차순): 2
            number3=int(self.round_info['number3']), # 당첨번호(오름차순): 3
            number4=int(self.round_info['number4']), # 당첨번호(오름차순): 4
            number5=int(self.round_info['number5']), # 당첨번호(오름차순): 5
            number6=int(self.round_info['number6']), # 당첨번호(오름차순): 6
            number7=int(self.round_info['number7']), # 당첨번호(오름차순): 7
            count1=int(self.round_info['count1']), # 당첨게임 수: 1등
            count2=int(self.round_info['count2']), # 당첨게임 수: 2등
            count3=int(self.round_info['count3']), # 당첨게임 수: 3등
            count4=int(self.round_info['count4']), # 당첨게임 수: 4등
            count5=int(self.round_info['count5']), # 당첨게임 수: 5등
            count_auto=int(self.round_info['auto']), # 1등 당첨유형: 자동
            count_hauto=int(self.round_info['hauto']), # 1등 당첨유형: 반자동
            count_manual=int(self.round_info['manual']), # 1등 당첨유형: 수동
            amount1=int(self.round_info['amount1']), # 1게임당 당첨금액: 1등
            amount2=int(self.round_info['amount2']), # 1게임당 당첨금액: 2등
            amount3=int(self.round_info['amount3']), # 1게임당 당첨금액: 3등
            amount4=int(self.round_info['amount4']), # 1게임당 당첨금액: 4등
            amount5=int(self.round_info['amount5']), # 1게임당 당첨금액: 5등
            allamount1=int(self.round_info['allamount1']), # 등위별 총 당첨금액: 1등
            allamount2=int(self.round_info['allamount2']), # 등위별 총 당첨금액: 2등
            allamount3=int(self.round_info['allamount3']), # 등위별 총 당첨금액: 3등
            allamount4=int(self.round_info['allamount4']), # 등위별 총 당첨금액: 4등
            allamount5=int(self.round_info['allamount5']), # 등위별 총 당첨금액: 5등
            sales=int(self.round_info['sales']), # 총 판매금액
            drawing1=0, # 당첨번호(추첨순): 1
            drawing2=0, # 당첨번호(추첨순): 2
            drawing3=0, # 당첨번호(추첨순): 3
            drawing4=0, # 당첨번호(추첨순): 4
            drawing5=0, # 당첨번호(추첨순): 5
            drawing6=0, # 당첨번호(추첨순): 6
            drawing7=0, # 당첨번호(추첨순): 7
            practice1=0, # 모의추첨번호: 1
            practice2=0, # 모의추첨번호: 2
            practice3=0, # 모의추첨번호: 3
            practice4=0, # 모의추첨번호: 4
            practice5=0, # 모의추첨번호: 5
            practice6=0, # 모의추첨번호: 6
            practice7=0, # 모의추첨번호: 7
            rule_ballset=0, # 추첨방식: 볼세트 (1~3)
            rule_garo=0, # 추첨방식: 모름/가로/세로 (0~2)
            rule_machine=0, # 추첨방식: 추첨기 (1~3)
        )

        if created:
            print(f"# 회차 {self.round_no} 정보가 성공적으로 생성되었습니다.")
        else:
            print(f"# 회차 {self.round_no} 정보는 이미 존재하여 건너뜁니다.")
