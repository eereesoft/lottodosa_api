from django.core.management.base import BaseCommand
from django.db import transaction, models
from django.core.paginator import Paginator
from lotto_core.models import Store


class Command(BaseCommand):
    help = '모든 판매점(Store)의 1등 및 2등 당첨 횟수를 전체 재계산하여 업데이트합니다.'

    def handle(self, *args, **options):
        """
        모든 Store의 matches1, matches2 필드를 StoreWin 데이터를 기반으로 전체 재계산하여 업데이트합니다.
        """
        self.stdout.write(self.style.SUCCESS("## 모든 판매점의 1, 2등 당첨 횟수 전체 업데이트 시작..."))

        # 한 번에 모든 데이터를 처리하지 않고, Paginator를 사용하여 1000개씩 나누어 처리합니다.
        all_stores = Store.objects.order_by('sid')
        paginator = Paginator(all_stores, 1000)
        total_updated_count = 0

        for page_num in paginator.page_range:
            page = paginator.page(page_num)
            self.stdout.write(f"# {page_num}/{paginator.num_pages} 페이지 처리 중...")

            # 현재 페이지의 Store 객체에 대해서만 annotate를 실행합니다.
            stores_with_counts = page.object_list.annotate(
                new_matches1=models.Count('storewin', filter=models.Q(storewin__rank=1)),
                new_matches2=models.Count('storewin', filter=models.Q(storewin__rank=2))
            )

            stores_to_update = []
            for store in stores_with_counts:
                # 계산된 값과 실제 필드 값이 다른 경우에만 업데이트 목록에 추가합니다.
                if store.matches1 != store.new_matches1 or store.matches2 != store.new_matches2:
                    store.matches1 = store.new_matches1
                    store.matches2 = store.new_matches2
                    stores_to_update.append(store)

            if stores_to_update:
                with transaction.atomic():
                    Store.objects.bulk_update(stores_to_update, ['matches1', 'matches2'])
                total_updated_count += len(stores_to_update)
                self.stdout.write(self.style.SUCCESS(f"  - {len(stores_to_update)}개 판매점 업데이트 완료."))

        if total_updated_count > 0:
            self.stdout.write(self.style.SUCCESS(f"# 총 {total_updated_count}개 판매점의 당첨 횟수 정보를 업데이트했습니다."))
        else:
            self.stdout.write(self.style.SUCCESS("# 모든 판매점의 당첨 횟수 정보가 이미 최신 상태입니다."))
