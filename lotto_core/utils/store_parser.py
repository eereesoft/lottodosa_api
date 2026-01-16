# store_parser.py

import requests
import time
import math
from lotto_core.models import Store
from django.db import transaction

PAGE_INTERVAL = 6


class StoreParser:
    STORE_URL = 'https://www.dhlottery.co.kr/prchsplcsrch/selectLtShp.do?pageNum='
    STORE_HEADERS = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    '(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'Referer': 'https://www.dhlottery.co.kr/prchsplcsrch/home',
    }
    
    # Django 모델 필드와 동기화할 필드 목록
    UPDATE_FIELDS = ['enabled', 'sname', 'phone', 'addr1', 'addr2', 'addr3', 'addr4', 'addr_doro', 'geo_e', 'geo_n', 'l645', 'p720', 'st05', 'st10', 'st20']
    INTERNET_STORE_SID = 51100000

    def __init__(self):
        self.stores = None
        self.session = requests.Session()
        self.session.headers.update(self.STORE_HEADERS)

    def _replace(self, s):
        if s is None:
            return ''
        return s.replace('&&#35;40;', '(').replace('&&#35;41;', ')').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"').replace('&nbsp;', ' ').replace('&#35;', '').replace('&apos;', '').strip()

    def parse_store(self):
        print(f'## parse_store')
        stores = []

        response = self.session.get(f'{self.STORE_URL}1')
        response.raise_for_status()
        json_data = response.json()
        data = json_data.get('data')

        total_count = data.get('total', 0)
        page_size = data['boundInfo'].get('recordCountPerPage', 10)
        total_pages = math.ceil(total_count / page_size)

        for page in range(1, total_pages + 1):
            print(f'# {page:03d} / {total_pages:04d}')
            response = self.session.get(f'{self.STORE_URL}{page}')
            response.raise_for_status()
            json_data = response.json()
            items = json_data['data'].get('list', [])
            stores.extend([item for item in items if not str(item.get('ltShpId', '')).startswith('7')])
            time.sleep(PAGE_INTERVAL)

        for i, r in enumerate(stores):
            stores[i]['conmNm'] = self._replace(stores[i]['conmNm'])
            stores[i]['bplcLctnDaddr'] = self._replace(stores[i]['bplcLctnDaddr'])
            stores[i]['bplcRdnmDaddr'] = self._replace(stores[i]['bplcRdnmDaddr'])

        self.stores = stores
        return self # 메서드 체이닝을 위해 self 반환

    def _prepare_stores_data(self):
        """파싱된 원본 데이터를 Django 모델 필드에 맞게 정제하고 타입을 변환합니다."""
        if not self.stores:
            return {}

        def safe_float(value, default=0.0):
            try:
                return float(value)
            except (ValueError, TypeError):
                return default

        def safe_bool(value):
            return str(value).strip().upper() == 'Y'

        return {
            int(s['ltShpId']): {
                'enabled': True,
                'sname': s.get('conmNm'),
                'phone': s.get('shpTelno') or '',
                'addr1': s.get('tm1BplcLctnAddr') or '',
                'addr2': s.get('tm2BplcLctnAddr') or '',
                'addr3': s.get('tm3BplcLctnAddr') or '',
                'addr4': s.get('bplcLctnDaddr') or '',
                'addr_doro': s.get('bplcRdnmDaddr') or '',
                'geo_e': safe_float(s.get('shpLot')),
                'geo_n': safe_float(s.get('shpLat')),
                'l645': safe_bool(s.get('l645LtNtslYn')),
                'p720': safe_bool(s.get('pt720NtslYn')),
                'st05': safe_bool(s.get('st5LtNtslYn')),
                'st10': safe_bool(s.get('st10LtNtslYn')),
                'st20': safe_bool(s.get('st20LtNtslYn'))
            } for s in self.stores
        }

    def upload_store(self):
        print(f'## upload_store')

        parsed_stores_map = self._prepare_stores_data()
        if not parsed_stores_map:
            print("# 파싱된 판매점 데이터가 없어 업로드를 건너뜁니다.")
            return

        print("# Django DB에서 모든 판매점 정보를 가져오는 중...")
        existing_stores_map = {store.sid: store for store in Store.objects.all()}
        print(f"# 총 {len(existing_stores_map)}개의 판매점 정보를 DB에서 가져왔습니다.")

        parsed_sids = set(parsed_stores_map.keys())
        existing_sids = set(existing_stores_map.keys())

        # 1. 신규 추가 대상
        sids_to_add = parsed_sids - existing_sids
        print(f"# 신규 추가 대상: {len(sids_to_add)}개")
        for sid in sids_to_add:
            store_data = parsed_stores_map[sid]
            Store.objects.create(sid=sid, **store_data)
            print(f"[INSERT] 판매점 생성: {sid} - {store_data['sname']}")

        # 2. 업데이트 대상
        sids_to_check_update = parsed_sids.intersection(existing_sids)
        print(f"# 업데이트 점검 대상: {len(sids_to_check_update)}개")
        for sid in sids_to_check_update:
            store_obj = existing_stores_map[sid]
            parsed_data = parsed_stores_map[sid]
            is_changed = False
            for field in self.UPDATE_FIELDS:
                parsed_value = parsed_data[field]
                db_value = getattr(store_obj, field)
                if field in ['geo_e', 'geo_n'] and not math.isclose(parsed_value, db_value):
                    setattr(store_obj, field, parsed_value)
                    is_changed = True
                elif parsed_value != db_value:
                    setattr(store_obj, field, parsed_value)
                    is_changed = True
            if is_changed:
                store_obj.enabled = True
                store_obj.save()
                print(f"[UPDATE] 판매점 수정: {sid} - {store_obj.sname}")

        # 3. 비활성화 대상
        sids_to_disable = existing_sids - parsed_sids
        print(f"# 비활성화 점검 대상: {len(sids_to_disable)}개")
        for sid in sids_to_disable:
            if sid == self.INTERNET_STORE_SID:
                continue
            store_obj = existing_stores_map[sid]
            if store_obj.enabled:
                store_obj.enabled = False
                store_obj.save()
                print(f"[DISABLE] 판매점 비활성화: {sid} - {store_obj.sname}")

        print("# 판매점 정보 동기화가 완료되었습니다.")
