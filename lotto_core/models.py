from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Round(models.Model):
    rid = models.IntegerField(primary_key=True) # 회차
    date = models.DateField() # 추첨일
    number1 = models.IntegerField() # 당첨번호(오름차순): 1
    number2 = models.IntegerField() # 당첨번호(오름차순): 2
    number3 = models.IntegerField() # 당첨번호(오름차순): 3
    number4 = models.IntegerField() # 당첨번호(오름차순): 4
    number5 = models.IntegerField() # 당첨번호(오름차순): 5
    number6 = models.IntegerField() # 당첨번호(오름차순): 6
    number7 = models.IntegerField() # 당첨번호(오름차순): 7
    count1 = models.IntegerField() # 당첨게임 수: 1등
    count2 = models.IntegerField() # 당첨게임 수: 2등
    count3 = models.IntegerField() # 당첨게임 수: 3등
    count4 = models.IntegerField() # 당첨게임 수: 4등
    count5 = models.IntegerField() # 당첨게임 수: 5등
    count_auto = models.IntegerField() # 1등 당첨유형: 자동
    count_hauto = models.IntegerField() # 1등 당첨유형: 반자동
    count_manual = models.IntegerField() # 1등 당첨유형: 수동
    amount1 = models.BigIntegerField() # 1게임당 당첨금액: 1등
    amount2 = models.BigIntegerField() # 1게임당 당첨금액: 2등
    amount3 = models.BigIntegerField() # 1게임당 당첨금액: 3등
    amount4 = models.BigIntegerField() # 1게임당 당첨금액: 4등
    amount5 = models.BigIntegerField() # 1게임당 당첨금액: 5등
    allamount1 = models.BigIntegerField() # 등위별 총 당첨금액: 1등
    allamount2 = models.BigIntegerField() # 등위별 총 당첨금액: 2등
    allamount3 = models.BigIntegerField() # 등위별 총 당첨금액: 3등
    allamount4 = models.BigIntegerField() # 등위별 총 당첨금액: 4등
    allamount5 = models.BigIntegerField() # 등위별 총 당첨금액: 5등
    sales = models.BigIntegerField() # 총 판매금액
    drawing1 = models.IntegerField(default=0) # 당첨번호(추첨순): 1
    drawing2 = models.IntegerField(default=0) # 당첨번호(추첨순): 2
    drawing3 = models.IntegerField(default=0) # 당첨번호(추첨순): 3
    drawing4 = models.IntegerField(default=0) # 당첨번호(추첨순): 4
    drawing5 = models.IntegerField(default=0) # 당첨번호(추첨순): 5
    drawing6 = models.IntegerField(default=0) # 당첨번호(추첨순): 6
    drawing7 = models.IntegerField(default=0) # 당첨번호(추첨순): 7
    practice1 = models.IntegerField(default=0) # 모의추첨번호: 1
    practice2 = models.IntegerField(default=0) # 모의추첨번호: 2
    practice3 = models.IntegerField(default=0) # 모의추첨번호: 3
    practice4 = models.IntegerField(default=0) # 모의추첨번호: 4
    practice5 = models.IntegerField(default=0) # 모의추첨번호: 5
    practice6 = models.IntegerField(default=0) # 모의추첨번호: 6
    practice7 = models.IntegerField(default=0) # 모의추첨번호: 7
    rule_ballset = models.IntegerField(default=0) # 추첨방식: 볼세트 (1~3)
    rule_garo = models.IntegerField(default=0) # 추첨방식: 모름/가로/세로 (0~2)
    rule_machine = models.IntegerField(default=0) # 추첨방식: 추첨기 (1~3)


class Store(models.Model):
    sid = models.IntegerField(primary_key=True) # 판매점 ID
    enabled = models.BooleanField(default=True)
    sname = models.CharField(max_length=30)
    phone = models.CharField(max_length=20)
    addr1 = models.CharField(max_length=10)
    addr2 = models.CharField(max_length=15)
    addr3 = models.CharField(max_length=15)
    addr4 = models.CharField(max_length=80)
    addr_doro = models.CharField(max_length=80)
    geo_e = models.FloatField(default=0) # longitude
    geo_n = models.FloatField(default=0) # latitude
    matches1 = models.IntegerField(default=0) # 1등 당첨 수 
    matches2 = models.IntegerField(default=0) # 2등 당첨 수
    updated_at = models.DateTimeField(auto_now=True) # 갱신일


class StoreWin(models.Model):
    class WinType(models.IntegerChoices):
        SECOND_PLACE = 0, '2등'
        AUTO = 1, '자동'
        HAUTO = 2, '반자동'
        MANUAL = 3, '수동'

    round = models.ForeignKey(Round, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    rank = models.IntegerField()
    auto = models.IntegerField(choices=WinType.choices)


class User(models.Model):
    uid = models.CharField(max_length=20, unique=True)
    nick = models.CharField(max_length=20, unique=True)
    matches1 = models.IntegerField(default=0) # 1등 당첨 수
    matches2 = models.IntegerField(default=0) # 2등 당첨 수
    matches3 = models.IntegerField(default=0) # 3등 당첨 수
    created_at = models.DateTimeField(auto_now_add=True) # 생성일
    updated_at = models.DateTimeField(auto_now=True) # 갱신일


class UserNumber(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    number1 = models.IntegerField()
    number2 = models.IntegerField()
    number3 = models.IntegerField()
    number4 = models.IntegerField()
    number5 = models.IntegerField()
    number6 = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True) # 생성일

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'number1', 'number2', 'number3', 'number4', 'number5', 'number6'], name='unique_user_number')
        ]


class PurchasedNumber(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rid = models.IntegerField()
    deleted = models.BooleanField(default=False)
    number1 = models.IntegerField()
    number2 = models.IntegerField()
    number3 = models.IntegerField()
    number4 = models.IntegerField()
    number5 = models.IntegerField()
    number6 = models.IntegerField()
    result = models.IntegerField(default=-1) # 당첨 결과 (-1:미추첨, 0:꽝, 1~5:1~5등)
    created_at = models.DateTimeField(auto_now_add=True) # 생성일


class SharedNumber(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rid = models.IntegerField()
    deleted = models.BooleanField(default=False)
    number1 = models.IntegerField()
    number2 = models.IntegerField()
    number3 = models.IntegerField()
    number4 = models.IntegerField()
    number5 = models.IntegerField()
    number6 = models.IntegerField()
    description = models.TextField() # 글 내용
    result = models.IntegerField(default=-1) # 당첨 결과 (-1:미추첨, 0:꽝, 1~5:1~5등)
    created_at = models.DateTimeField(auto_now_add=True) # 생성일

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'rid', 'number1', 'number2', 'number3', 'number4', 'number5', 'number6'], name='unique_shared_number')
        ]


class SharedNumberComment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    shared_number = models.ForeignKey(SharedNumber, on_delete=models.CASCADE)
    comment = models.TextField() # 댓글 내용
    created_at = models.DateTimeField(auto_now_add=True) # 생성일


@receiver(post_save, sender=Round)
def update_shared_number_results(sender, instance, created, **kwargs):
    """
    (시그널 핸들러)
    새로운 Round가 생성될 때, 해당 회차의 SharedNumber들의 당첨 결과를 업데이트합니다.
    """
    if not created:
        return

    # 해당 회차의 공유 번호들을 가져옵니다.
    shared_numbers_to_check = SharedNumber.objects.filter(
        rid=instance.rid, result=-1 # 아직 처리되지 않은 번호만 대상으로 합니다.
    )

    if not shared_numbers_to_check:
        return

    # 당첨 번호와 보너스 번호를 세트로 만듭니다.
    win_numbers = {instance.number1, instance.number2, instance.number3, instance.number4, instance.number5, instance.number6}
    bonus_number = instance.number7

    updated_shared_numbers = []
    users_to_update = {} # 사용자의 당첨 횟수를 업데이트하기 위한 딕셔너리
    for shared in shared_numbers_to_check:
        shared_nums = {shared.number1, shared.number2, shared.number3, shared.number4, shared.number5, shared.number6}
        
        # 일치하는 번호 개수 확인
        match_count = len(win_numbers.intersection(shared_nums))

        # 등수 판정
        if match_count == 6:
            shared.result = 1
            if shared.user_id not in users_to_update: users_to_update[shared.user_id] = {'matches1': 0, 'matches2': 0, 'matches3': 0}
            users_to_update[shared.user_id]['matches1'] += 1
        elif match_count == 5 and bonus_number in shared_nums:
            shared.result = 2
            if shared.user_id not in users_to_update: users_to_update[shared.user_id] = {'matches1': 0, 'matches2': 0, 'matches3': 0}
            users_to_update[shared.user_id]['matches2'] += 1
        elif match_count == 5:
            shared.result = 3
            if shared.user_id not in users_to_update: users_to_update[shared.user_id] = {'matches1': 0, 'matches2': 0, 'matches3': 0}
            users_to_update[shared.user_id]['matches3'] += 1
        elif match_count == 4:
            shared.result = 4
        elif match_count == 3:
            shared.result = 5
        else:
            shared.result = 0

        updated_shared_numbers.append(shared)

    # 데이터베이스 업데이트 (트랜잭션으로 묶어 원자성 보장)
    with models.manager.transaction.atomic():
        # 1. SharedNumber의 당첨 결과(result)를 bulk_update 합니다.
        if updated_shared_numbers:
            SharedNumber.objects.bulk_update(updated_shared_numbers, ['result'])

        # 2. User의 당첨 횟수(matches)를 F() 표현식을 사용하여 업데이트합니다.
        for user_id, counts in users_to_update.items():
            User.objects.filter(id=user_id).update(
                matches1=models.F('matches1') + counts['matches1'],
                matches2=models.F('matches2') + counts['matches2'],
                matches3=models.F('matches3') + counts['matches3'],
            )
