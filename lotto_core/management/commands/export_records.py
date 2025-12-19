import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from lotto_core.models import Round, Store, StoreWin

class Command(BaseCommand):
    help = 'Round, Store, StoreWin 테이블의 데이터를 CSV 파일로 내보냅니다.'

    def handle(self, *args, **options):
        today = datetime.now().strftime('%Y%m%d')
        self.export_round(f'round_{today}.csv')
        self.export_store(f'store_{today}.csv')
        self.export_storewin(f'wins_{today}.csv')

    def export_round(self, filename):
        self.stdout.write(f'Exporting Round to {filename}...')
        # 모델의 모든 필드명을 가져옵니다.
        fields = [f.name for f in Round._meta.fields]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(fields)
            
            queryset = Round.objects.all().order_by('rid')
            for obj in queryset:
                writer.writerow([getattr(obj, field) for field in fields])
        
        self.stdout.write(self.style.SUCCESS(f'Successfully exported {filename}'))

    def export_store(self, filename):
        self.stdout.write(f'Exporting Store to {filename}...')
        fields = [f.name for f in Store._meta.fields]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(fields)
            
            queryset = Store.objects.all().order_by('sid')
            for obj in queryset:
                writer.writerow([getattr(obj, field) for field in fields])
                
        self.stdout.write(self.style.SUCCESS(f'Successfully exported {filename}'))

    def export_storewin(self, filename):
        self.stdout.write(f'Exporting StoreWin to {filename}...')
        # StoreWin 필드 + Store 조인 정보
        # import_storewins.py와의 호환성을 고려하여 헤더를 구성합니다.
        headers = ['rid', 'rank', 'auto', 'sid', 'sname', 'phone', 'address']
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            # Store 테이블을 조인하여 쿼리 성능을 최적화합니다.
            # StoreWin의 PK(id) 기준으로 오름차순 정렬합니다.
            queryset = StoreWin.objects.select_related('store').all().order_by('id')
            
            for obj in queryset:
                # auto 필드는 사람이 읽을 수 있는 문자열('자동', '수동' 등)로 변환합니다.
                # import_storewins.py에서 이 문자열 형식을 인식합니다.
                row = [
                    obj.round_id,
                    obj.store_id,
                    obj.rank,
                    obj.get_auto_display(),
                    obj.store.sname,
                    obj.store.phone,
                    obj.store.addr_doro
                ]
                writer.writerow(row)
                
        self.stdout.write(self.style.SUCCESS(f'Successfully exported {filename}'))
