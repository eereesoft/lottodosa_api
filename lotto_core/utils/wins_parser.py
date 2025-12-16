# wins_parser.py

import requests
from bs4 import BeautifulSoup
import time
from collections import Counter
from lotto_core.models import StoreWin, Round, Store
from django.db import transaction, models

PAGE_INTERVAL = 6


class WinsParser:
    STOREWIN_URL = 'https://dhlottery.co.kr/store.do?method=topStore&pageGubun=L645'
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Referer': 'https://dhlottery.co.kr/store.do?method=topStore'
    }

    def __init__(self):
        self.round_no = 0
        self.wins = None
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def parse_wins(self, round):
        self.round_no = round
        print(f'##  parse_wins: {self.round_no}')
        resp = self.session.get(f'{self.STOREWIN_URL}&drwNo={self.round_no}')
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        wins = []

        groups = soup.select('.group_content')
        
        # 1등, 2등(1페이지)
        print(f'# parse first prize store')
        first_table = groups[0].select_one('.tbl_data')
        wins = wins + self._parse_storewin_1st_table(first_table)

        # 2등 (1페이지)
        print(f'# parse second prize store (1/?)')
        second_table = groups[1].select_one('.tbl_data')
        wins = wins + self._parse_storewin_2nd_table(second_table)

        # 2등(2페이지~)
        cur_page = 1
        while (True):
            cur_page = cur_page + 1
            time.sleep(PAGE_INTERVAL)
            resp = self.session.get(f'{self.STOREWIN_URL}&drwNo={self.round_no}&nowPage={cur_page}')
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            pages = soup.select('.paginate_common a')
            cur_page_exists = False
            for a in pages:
                if (a.get('title') != None):
                    cur_page_exists = True
                    break
            if not cur_page_exists: # 마지막 페이지 넘어감
                break
            groups = soup.select('.group_content')
            print(f'# parse second prize store ({cur_page}/?)')
            second_table = groups[1].select_one('.tbl_data')
            wins = wins + self._parse_storewin_2nd_table(second_table)

        self.wins = wins

    def _parse_storewin_1st_table(self, table_soup):
        cells = table_soup.select('tbody tr td')
        if len(cells) == 1:
            return []
        rows = table_soup.select('tbody tr')
        result = []
        for row in rows:
            items = row.find_all('td')
            id = items[4].find('a').get('onclick', '').split("'")[1].strip()
            result.append({
                'round': self.round_no,
                'rank': 1,
                'sid': id,
                'name': items[1].get_text(strip=True),
                'auto': items[2].get_text(strip=True),
                'address': items[3].get_text(strip=True),
                'phone': None,
                'geo_e': 0,
                'geo_n': 0,
            })
        return result

    def _parse_storewin_2nd_table(self, table_soup):
        cells = table_soup.select('tbody tr td')
        if len(cells) == 1:
            return []
        rows = table_soup.select('tbody tr')
        result = []
        for row in rows:
            items = row.find_all('td')
            id = items[3].find('a').get('onclick', '').split("'")[1].strip()
            result.append({
                'round': self.round_no,
                'rank': 2,
                'sid': id,
                'name': items[1].get_text(strip=True),
                'auto': '-',
                'address': items[2].get_text(strip=True),
                'phone': None,
                'geo_e': 0,
                'geo_n': 0,
            })
        return result

    def upload_wins(self):
        print(f'## upload_wins: {self.round_no}')
        if not self.wins:
            print("# 파싱된 당첨 정보가 없어 업로드를 건너뜁니다.")
            return

        try:
            round_instance = Round.objects.get(rid=self.round_no)
        except Round.DoesNotExist:
            print(f"# 오류: 회차({self.round_no}) 정보가 DB에 없습니다. 먼저 회차 정보를 동기화해야 합니다.")
            return

        # 성능을 위해 필요한 Store 객체들을 미리 가져옵니다.
        sids = {int(win['sid']) for win in self.wins}
        stores_map = {s.sid: s for s in Store.objects.filter(sid__in=sids)}

        store_wins_to_create = []
        for win_data in self.wins:
            sid = int(win_data['sid'])
            store_instance = stores_map.get(sid)

            # DB에 없는 판매점이면 새로 생성합니다.
            if not store_instance:
                print(f"# 판매점({sid})이 DB에 없어 새로 생성합니다.")
                store_instance, created = Store.objects.get_or_create(
                    sid=sid,
                    enabled=True,
                    sname=win_data['name'],
                    phone=win_data.get('phone') or '',
                    addr1='',
                    addr2='',
                    addr3='',
                    addr4='',
                    addr_doro=win_data.get('address') or '',
                    geo_e=float(0.0),
                    geo_n=float(0.0),
                )
                stores_map[sid] = store_instance # 새로 생성된 객체를 맵에 추가

            # 'auto' 필드 값을 IntegerChoices에 맞게 변환합니다.
            auto_str = win_data['auto']
            if auto_str == '자동':
                auto_int = StoreWin.WinType.AUTO
            elif auto_str == '반자동':
                auto_int = StoreWin.WinType.HAUTO
            elif auto_str == '수동':
                auto_int = StoreWin.WinType.MANUAL
            else: # 2등 당첨은 '-'로 표시됨
                auto_int = StoreWin.WinType.SECOND_PLACE

            # 중복 생성을 방지하기 위해 get_or_create 사용
            _, created = StoreWin.objects.get_or_create(
                round=round_instance,
                store=store_instance,
                rank=win_data['rank'],
                auto=auto_int
            )
            if created:
                store_wins_to_create.append(win_data)

        if not store_wins_to_create:
            print("# 새로 추가된 당첨 정보가 없습니다.")
            return

        print(f"# {len(store_wins_to_create)}개의 새로운 당첨 정보를 DB에 반영합니다.")

        # bulk_create는 post_save 시그널을 호출하지 않으므로, 수동으로 당첨 횟수를 집계합니다.
        rank1_counts = Counter()
        rank2_counts = Counter()

        for win in store_wins_to_create:
            sid = int(win['sid'])
            if win['rank'] == 1:
                rank1_counts[sid] += 1
            elif win['rank'] == 2:
                rank2_counts[sid] += 1

        all_sids = set(rank1_counts.keys()) | set(rank2_counts.keys())
        if not all_sids:
            return

        stores_to_update = Store.objects.filter(sid__in=all_sids)
        for store in stores_to_update:
            store.matches1 += rank1_counts.get(store.sid, 0)
            store.matches2 += rank2_counts.get(store.sid, 0)

        with transaction.atomic():
            Store.objects.bulk_update(stores_to_update, ['matches1', 'matches2'])
            print(f"# {len(stores_to_update)}개 판매점의 1, 2등 당첨 횟수를 업데이트했습니다.")
