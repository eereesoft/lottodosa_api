import pandas as pd
import numpy as np
from django.core.management.base import BaseCommand
from django.db import transaction
from lotto_core.models import StoreWin, Round, Store


class Command(BaseCommand):
    help = 'CSV 파일로부터 당첨 판매점 정보(StoreWin)를 가져와 데이터베이스에 저장합니다.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='당첨 판매점 정보가 담긴 CSV 파일의 경로')

    def handle(self, *args, **options):
        file_path = options['csv_file']
        self.stdout.write(self.style.SUCCESS(f'"{file_path}" 파일에서 당첨 판매점 데이터 임포트를 시작합니다...'))

        try:
            df = pd.read_csv(file_path, header=0, encoding='utf-8')
            df = df.replace({np.nan: None})

            store_wins_to_create = []
            
            # 성능 최적화를 위해 필요한 Round와 Store 객체를 미리 가져옵니다.
            required_rids = set(df['rid'].dropna().astype(int))
            required_sids = set(df['sid'].dropna().astype(int))
            
            rounds_map = {r.rid: r for r in Round.objects.filter(rid__in=required_rids)}
            stores_map = {s.sid: s for s in Store.objects.filter(sid__in=required_sids)}

            for index, r in df.iterrows():
                try:
                    rid = int(r.get('rid'))
                    sid = int(r.get('sid'))

                    round_instance = rounds_map.get(rid)
                    store_instance = stores_map.get(sid)

                    # 회차 정보가 없으면 건너뜁니다.
                    if not round_instance:
                        self.stdout.write(self.style.WARNING(f'회차({rid})가 DB에 없어 건너뜁니다. (행: {index + 1})'))
                        continue

                    # 판매점 정보가 없으면 새로 생성합니다.
                    if not store_instance:
                        self.stdout.write(self.style.NOTICE(f'판매점({sid})이 DB에 없어 새로 생성합니다.'))
                        store_instance = Store.objects.create(
                            sid=sid,
                            enabled=True,
                            sname=r.sname,
                            phone=r.get('phone') or '',
                            addr1='',
                            addr2='',
                            addr3='',
                            addr4='',
                            addr_doro=r.get('address') or '',
                            geo_e=float(0.0),
                            geo_n=float(0.0),
                        )
                        # 새로 생성된 판매점을 추후 조회를 위해 맵에 추가합니다.
                        stores_map[sid] = store_instance

                    # 'auto' 필드 값을 IntegerChoices에 맞게 변환합니다.
                    auto_value_str = str(r.get('auto', ''))
                    auto_value_int = StoreWin.WinType.SECOND_PLACE # 기본값 '2등'
                    if auto_value_str == '자동':
                        auto_value_int = StoreWin.WinType.AUTO
                    elif auto_value_str == '반자동':
                        auto_value_int = StoreWin.WinType.HAUTO
                    elif auto_value_str == '수동':
                        auto_value_int = StoreWin.WinType.MANUAL

                    store_win_obj = StoreWin(
                        round=round_instance,
                        store=store_instance,
                        rank=int(r.get('rank')),
                        auto=auto_value_int,
                    )
                    store_wins_to_create.append(store_win_obj)

                except (KeyError, ValueError, TypeError) as e:
                    self.stderr.write(self.style.ERROR(f'오류 발생 (행 번호: {index + 1}, 데이터: {r.to_dict()}): {e}'))
                    continue

            if store_wins_to_create:
                # bulk_create는 시그널을 호출하지 않으므로, 생성 후 수동으로 시그널 로직을 실행해야 합니다.
                with transaction.atomic():
                    created_objects = StoreWin.objects.bulk_create(store_wins_to_create)
                    self.stdout.write(self.style.SUCCESS(f'{len(created_objects)}개의 새로운 당첨 정보가 성공적으로 추가되었습니다.'))
            else:
                self.stdout.write(self.style.SUCCESS('추가할 새로운 데이터가 없습니다.'))

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f'파일을 찾을 수 없습니다: "{file_path}"'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'예상치 못한 오류가 발생했습니다: {e}'))
