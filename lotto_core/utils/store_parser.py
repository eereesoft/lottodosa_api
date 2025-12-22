# store_parser.py

import requests
import time
import math
from lotto_core.models import Store
from django.db import transaction

PAGE_INTERVAL = 6
MAX_RETRIES = 3  # 최대 재시도 횟수


class StoreParser:
    STORE_URL = 'https://www.dhlottery.co.kr/store.do?method=sellerInfo645Result'
    SIDO = ['서울', '경기', '부산', '대구', '인천', '대전', '울산', '강원', '충북', '충남', '광주', '전북', '전남', '경북', '경남', '제주', '세종']
    STORE_HEADERS = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    '(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'Referer': 'https://dhlottery.co.kr/store.do?method=sellerInfo645',
    }
    
    # Django 모델 필드와 동기화할 필드 목록
    UPDATE_FIELDS = ['sname', 'phone', 'addr1', 'addr2', 'addr3', 'addr4', 'addr_doro', 'geo_e', 'geo_n', 'enabled']
    INTERNET_STORE_SID = 51100000

    def __init__(self):
        self.stores = None

    def _replace(self, s):
        return s.replace('&&#35;40;', '(').replace('&&#35;41;', ')').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"').replace('&nbsp;', ' ').replace('&#35;', '').replace('&apos;', '').strip()

    def parse_store(self):
        print(f'## parse_store')
        stores = []
        for i1, sido in enumerate(self.SIDO):
            print(f'# {i1:02d}. {sido:<3} - {1:03d} / ???')
            payload = {
                'searchType': '1',
                'nowPage': '1',
                'sltSIDO': sido,
                'sltGUGUN': '',
                'rtlrSttus': '001'
            }
            for retry in range(MAX_RETRIES):
                try:
                    response = requests.post(self.STORE_URL, headers=self.STORE_HEADERS, data=payload)
                    break  # 성공하면 루프 탈출
                except requests.exceptions.RequestException as e:
                    print(f"# Error occurred (attempt {retry + 1}/{MAX_RETRIES}): {e}")
                    if retry == MAX_RETRIES - 1:
                        raise  # 마지막 재시도에도 실패하면 예외 발생
                    time.sleep(10)  # 재시도 전 대기
            response.raise_for_status()
            json_data = response.json()
            stores.extend(json_data['arr'])
            time.sleep(PAGE_INTERVAL)

            totalPage = json_data['totalPage']
            for i2 in range(2, totalPage):
                print(f'# {i1:02d}. {sido:<3} - {i2:03d} / {totalPage:03d}')
                payload['nowPage'] = str(i2)
                for retry in range(MAX_RETRIES):
                    try:
                        response = requests.post(self.STORE_URL, headers=self.STORE_HEADERS, data=payload)
                        break  # 성공하면 루프 탈출
                    except requests.exceptions.RequestException as e:
                        print(f"# Error occurred (attempt {retry + 1}/{MAX_RETRIES}): {e}")
                        if retry == MAX_RETRIES - 1:
                            raise  # 마지막 재시도에도 실패하면 예외 발생
                        time.sleep(10)  # 재시도 전 대기
                response.raise_for_status()
                json_data = response.json()
                stores.extend(json_data['arr'])
                time.sleep(PAGE_INTERVAL)

        for i, r in enumerate(stores):
            stores[i]['FIRMNM'] = self._replace(stores[i]['FIRMNM'])
            stores[i]['BPLCLOCPLCDTLADRES'] = self._replace(stores[i]['BPLCLOCPLCDTLADRES'])
            stores[i]['BPLCDORODTLADRES'] = self._replace(stores[i]['BPLCDORODTLADRES'])

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
        
        return {
            int(s['RTLRID']): {
                'sname': s.get('FIRMNM'),
                'phone': s.get('RTLRSTRTELNO') or '',
                'addr1': s.get('BPLCLOCPLC1') or '',
                'addr2': s.get('BPLCLOCPLC2') or '',
                'addr3': s.get('BPLCLOCPLC3') or '',
                'addr4': s.get('BPLCLOCPLCDTLADRES') or '',
                'addr_doro': s.get('BPLCDORODTLADRES') or '',
                'geo_e': safe_float(s.get('LONGITUDE')),
                'geo_n': safe_float(s.get('LATITUDE')),
                'enabled': True
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
