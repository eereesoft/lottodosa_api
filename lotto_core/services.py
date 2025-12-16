from .models import Round, User, UserNumber, SharedNumber, Store, StoreWin, PurchasedNumber
from .utils.nick_generator import generate_nick
import secrets
from django.core.exceptions import ValidationError
from django.db import transaction
import math
from django.db.models import Q, Case, When, Value, IntegerField

MAX_NICKNAME_LENGTH = 18 # 사용자 닉네임 최대 길이 (의도된 18자)


def get_all_rounds():
    """
    데이터베이스에서 모든 로또 회차 정보를 가져옵니다.

    Returns:
        QuerySet: Round 모델의 모든 객체를 담고 있는 QuerySet.
                  최신 회차가 먼저 오도록 회차(rid)의 내림차순으로 정렬됩니다.
    """
    return Round.objects.all().order_by('-rid')


def get_last_round():
    """
    데이터베이스에서 가장 최신 로또 회차 정보를 가져옵니다.

    Returns:
        Round: 가장 최신 Round 모델 객체. 데이터가 없으면 None을 반환합니다.
    """
    return Round.objects.order_by('-rid').first()


def get_round(rid: int):
    """
    주어진 회차(rid)에 해당하는 로또 회차 정보를 가져옵니다.

    Args:
        rid (int): 조회할 로또 회차 번호.

    Returns:
        Round: 해당 rid를 가진 Round 모델 객체.

    Raises:
        Round.DoesNotExist: 해당 rid를 가진 회차가 없을 경우.
    """
    return Round.objects.get(rid=rid)


def get_regions(addr1: str = None, addr2: str = None):
    """
    주소 정보를 계층적으로 조회합니다.

    - 매개변수가 없으면, 중복되지 않은 시/도 (addr1) 리스트를 반환합니다.
    - addr1이 주어지면, 해당 시/도의 중복되지 않은 시/군/구 (addr2) 리스트를 반환합니다.
    - addr1과 addr2가 주어지면, 해당하는 중복되지 않은 읍/면/동 (addr3) 리스트를 반환합니다.
    """
    queryset = Store.objects.filter(enabled=True)
    if addr1 and addr2:
        queryset = queryset.filter(addr1=addr1, addr2=addr2)
        return list(queryset.values_list('addr3', flat=True).distinct())
    elif addr1:
        queryset = queryset.filter(addr1=addr1)
        return list(queryset.values_list('addr2', flat=True).distinct())
    else:
        return list(queryset.values_list('addr1', flat=True).distinct())


def get_stores_by_region(addr1: str = None, addr2: str = None, addr3: str = None):
    """
    주어진 지역 정보(시/도, 시/군/구, 읍/면/동)에 따라 판매점 목록을 조회합니다.
    - 활성화된(enabled=True) 판매점만 대상으로 합니다.
    - 지역 정보가 주어질수록 더 상세하게 필터링합니다.

    Args:
        addr1 (str, optional): 시/도. Defaults to None.
        addr2 (str, optional): 시/군/구. Defaults to None.
        addr3 (str, optional): 읍/면/동. Defaults to None.

    Returns:
        QuerySet: Store 모델의 QuerySet.
    """
    queryset = Store.objects.filter(enabled=True)

    if addr1:
        queryset = queryset.filter(addr1=addr1)
    if addr2:
        queryset = queryset.filter(addr2=addr2)
    if addr3:
        queryset = queryset.filter(addr3=addr3)

    return queryset.order_by('sid')


def get_nearby_stores(latitude: float, longitude: float):
    """
    주어진 좌표 근처의 판매점을 검색합니다.
    - 초기 위도 ±0.1, 경도 ±0.1 (약 10km) 범위로 검색합니다.
    - 결과가 5개 미만이면, 최소 5개의 판매점이 나올 때까지 위/경도 범위를 각각 0.05씩 늘려나갑니다.

    Args:
        latitude (float): 기준점의 위도.
        longitude (float): 기준점의 경도.

    Returns:
        QuerySet: Store 모델의 QuerySet. 활성화된 판매점만 반환합니다.
    """
    # 초기 위/경도 차이 (약 10km)
    lat_diff = 0.1
    lon_diff = 0.1
    min_stores_count = 5
    max_iterations = 20  # 무한 루프 방지를 위한 최대 반복 횟수
    current_iteration = 0

    while current_iteration < max_iterations:
        current_iteration += 1

        stores = Store.objects.filter(
            enabled=True,
            geo_n__gte=latitude - lat_diff,
            geo_n__lte=latitude + lat_diff,
            geo_e__gte=longitude - lon_diff,
            geo_e__lte=longitude + lon_diff
        )

        # 조회된 상점이 5개 이상이면 루프를 종료하고 결과를 반환합니다.
        if stores.count() >= min_stores_count:
            break

        # 결과가 부족하면 검색 범위를 확장합니다.
        lat_diff += 0.05
        lon_diff += 0.05

    return stores


def get_round_stores(rid: int):
    """
    주어진 회차(rid)에 당첨된 판매점 목록을 조회합니다.

    Args:
        rid (int): 조회할 로또 회차 번호.

    Returns:
        QuerySet: Store 모델의 QuerySet.
        해당 회차에 당첨된 StoreWin 객체들의 QuerySet이며,
        각 StoreWin 객체에는 관련 Store 객체가 select_related로 함께 로드됩니다.
    """
    # StoreWin 객체를 직접 쿼리하고, 관련 Store 객체를 select_related로 함께 가져옵니다.
    # 이렇게 하면 StoreWin과 Store 테이블이 DB 레벨에서 JOIN되어 한 번의 쿼리로 모든 데이터를 가져옵니다.
    return StoreWin.objects.filter(round__rid=rid).select_related('store').order_by('store__sid', 'rank')


def get_top_stores():
    """
    1등 당첨 횟수가 많은 순서로 판매점 목록을 조회합니다.
    1등 또는 2등 당첨 이력이 있는 판매점만 대상으로 하며,
    1등 횟수가 같으면 2등 횟수가 많은 순으로 정렬합니다.

    Returns:
        QuerySet: Store 모델의 QuerySet.
    """
    return Store.objects.filter(
        Q(matches1__gt=0) | Q(matches2__gt=0),
        enabled=True
    ).order_by('-matches1', '-matches2')


def get_store(sid: int):
    """
    주어진 ID(sid)에 해당하는 판매점 정보를 조회합니다.

    Args:
        sid (int): 판매점의 고유 ID.

    Returns:
        Store: 해당 Store 모델 객체.

    Raises:
        Store.DoesNotExist: 해당 ID를 가진 판매점이 없을 경우.
    """
    return Store.objects.get(sid=sid)


def register_user():
    """
    새로운 사용자를 생성하고 데이터베이스에 저장합니다.

    - 20자리의 고유한 16진수 UID를 생성합니다.
    - `generate_nick`을 사용하여 닉네임을 생성합니다.
    - 닉네임이 중복될 경우, 닉네임 뒤에 숫자를 붙여 고유한 닉네임을 찾을 때까지 반복합니다.
    - 닉네임 길이는 20자를 넘지 않도록 조정됩니다.

    Returns:
        User: 새로 생성된 User 모델 객체.
    """
    uid = secrets.token_hex(10)  # 20자리 16진수 문자열 생성

    # 고유한 닉네임 생성
    base_nick = generate_nick()
    # 닉네임이 18자를 초과하면 18자에 맞게 자릅니다.
    if len(base_nick) > MAX_NICKNAME_LENGTH:
        base_nick = base_nick[:MAX_NICKNAME_LENGTH]

    nick_candidate = base_nick
    counter = 1
    while User.objects.filter(nick=nick_candidate).exists():
        suffix = str(counter)
        # DB의 max_length(20)를 초과하지 않도록 base_nick 길이를 조정합니다.
        # 예: base_nick(18자) + counter(10) -> base_nick(18자)가 아닌, 18자에서 2자를 뺀 16자 + "10"
        allowed_base_len = 20 - len(suffix)
        nick_candidate = f"{base_nick[:allowed_base_len]}{suffix}"
        counter += 1
        if counter > 1000: # 무한 루프 방지
            raise Exception("고유한 닉네임을 생성하는 데 실패했습니다.")

    return User.objects.create(uid=uid, nick=nick_candidate)


def set_user_nick(uid: str, new_nick: str):
    """
    주어진 UID를 가진 사용자의 닉네임을 변경합니다.

    Args:
        uid (str): 닉네임을 변경할 사용자의 고유 ID.
        new_nick (str): 새로 설정할 닉네임.

    Returns:
        User: 닉네임이 업데이트된 User 모델 객체.

    Raises:
        User.DoesNotExist: 해당 UID를 가진 사용자가 없을 경우.
        ValidationError: 새 닉네임이 이미 존재하거나 유효하지 않을 경우.
    """
    if not new_nick or not new_nick.strip():
        raise ValidationError("닉네임은 비워둘 수 없습니다.")
    
    new_nick = new_nick.strip()
    if len(new_nick) > MAX_NICKNAME_LENGTH:
        raise ValidationError(f"닉네임은 {MAX_NICKNAME_LENGTH}자를 초과할 수 없습니다.")

    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        raise User.DoesNotExist(f"UID '{uid}'를 가진 사용자를 찾을 수 없습니다.")

    if user.nick == new_nick: # 현재 닉네임과 동일하면 변경할 필요 없음
        return user

    if User.objects.exclude(uid=uid).filter(nick=new_nick).exists():
        raise ValidationError(f"닉네임 '{new_nick}'은(는) 이미 사용 중입니다.")

    user.nick = new_nick
    user.save()
    return user


def add_user_numbers(uid: str, numbers_list: list[list[int]]):
    """
    주어진 UID를 가진 사용자의 로또 번호를 저장합니다.
    여러 개의 번호 세트를 한 번에 저장할 수 있습니다.

    Args:
        uid (str): 로또 번호를 저장할 사용자의 고유 ID.
        numbers_list (list[list[int]]): 6개의 숫자로 이루어진 로또 번호 세트들의 리스트.

    Returns:
        list[UserNumber]: 새로 생성된 UserNumber 객체들의 리스트.

    Raises:
        User.DoesNotExist: 해당 UID를 가진 사용자가 없을 경우.
        ValidationError: 로또 번호가 유효하지 않을 경우.
    """
    # 1. 사용자 조회
    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        raise User.DoesNotExist(f"UID '{uid}'를 가진 사용자를 찾을 수 없습니다.")

    user_numbers_to_create = []
    with transaction.atomic():
        for numbers in numbers_list:
            # 2. 입력 유효성 검사 (각 번호 세트별)
            if not isinstance(numbers, list) or len(numbers) != 6:
                raise ValidationError("각 로또 번호 세트는 6개의 숫자로 이루어진 리스트여야 합니다.")
            if len(set(numbers)) != 6:
                raise ValidationError("로또 번호는 중복될 수 없습니다.")
            for num in numbers:
                if not isinstance(num, int) or not (1 <= num <= 45):
                    raise ValidationError("로또 번호는 1에서 45 사이의 정수여야 합니다.")

            # 3. UserNumber 객체 생성 준비
            sorted_numbers = sorted(numbers)
            user_number_obj = UserNumber(
                user=user,
                number1=sorted_numbers[0],
                number2=sorted_numbers[1],
                number3=sorted_numbers[2],
                number4=sorted_numbers[3],
                number5=sorted_numbers[4],
                number6=sorted_numbers[5],
            )
            user_numbers_to_create.append(user_number_obj)

        # 4. bulk_create를 사용하여 한 번의 쿼리로 여러 객체를 생성합니다.
        # ignore_conflicts=False 이므로, UniqueConstraint 위반 시 IntegrityError가 발생합니다.
        try:
            created_numbers = UserNumber.objects.bulk_create(user_numbers_to_create)
        except Exception as e: # IntegrityError 등
            raise ValidationError("이미 저장된 번호 조합이 포함되어 있습니다.")

    return created_numbers


def del_user_numbers(uid: str, numbers_list: list[list[int]]):
    """
    주어진 UID를 가진 사용자의 특정 로또 번호들을 '삭제' 처리합니다.
    실제 데이터는 삭제하지 않고, 'deleted' 필드를 True로 업데이트합니다.

    Args:
        uid (str): 로또 번호를 삭제할 사용자의 고유 ID.
        numbers_list (list[list[int]]): 삭제할 6개의 숫자로 이루어진 로또 번호 세트들의 리스트.

    Returns:
        int: 성공적으로 '삭제' 처리된 번호의 개수.

    Raises:
        User.DoesNotExist: 해당 UID를 가진 사용자가 없을 경우.
        ValidationError: 유효하지 않은 번호 세트가 포함된 경우.
    """
    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        raise User.DoesNotExist(f"UID '{uid}'를 가진 사용자를 찾을 수 없습니다.")

    q_objects = Q()
    for numbers in numbers_list:
        if not isinstance(numbers, list) or len(numbers) != 6:
            raise ValidationError("각 로또 번호 세트는 6개의 숫자로 이루어진 리스트여야 합니다.")
        
        sorted_numbers = sorted(numbers)
        q_objects |= Q(
            number1=sorted_numbers[0], number2=sorted_numbers[1], number3=sorted_numbers[2],
            number4=sorted_numbers[3], number5=sorted_numbers[4], number6=sorted_numbers[5]
        )

    # 사용자의 번호 중, 삭제 요청된 번호 조합과 일치하고 아직 삭제되지 않은 번호들을 업데이트합니다.
    updated_count = UserNumber.objects.filter(user=user, deleted=False).filter(q_objects).update(deleted=True)
    return updated_count


def get_user_numbers(uid: str):
    """
    주어진 UID를 가진 사용자의 모든 로또 번호를 조회합니다.

    Args:
        uid (str): 로또 번호를 조회할 사용자의 고유 ID.

    Returns:
        QuerySet: UserNumber 모델의 QuerySet.

    Raises:
        User.DoesNotExist: 해당 UID를 가진 사용자가 없을 경우.
    """
    try:
        return UserNumber.objects.filter(user__uid=uid, deleted=False).order_by('-created_at')
    except User.DoesNotExist:
        raise User.DoesNotExist(f"UID '{uid}'를 가진 사용자를 찾을 수 없습니다.")


def add_purchased_numbers(uid: str, numbers_list: list[list[int]]):
    """
    주어진 UID를 가진 사용자의 구매 번호를 저장합니다.
    여러 개의 번호 세트를 한 번에 저장할 수 있습니다.

    Args:
        uid (str): 구매 번호를 저장할 사용자의 고유 ID.
        numbers_list (list[list[int]]): 6개의 숫자로 이루어진 로또 번호 세트들의 리스트.

    Returns:
        list[PurchasedNumber]: 새로 생성된 PurchasedNumber 객체들의 리스트.

    Raises:
        User.DoesNotExist: 해당 UID를 가진 사용자가 없을 경우.
        ValidationError: 로또 번호가 유효하지 않을 경우.
    """
    # 1. 사용자 조회
    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        raise User.DoesNotExist(f"UID '{uid}'를 가진 사용자를 찾을 수 없습니다.")

    # 2. 다음 회차 번호 결정
    last_round = get_last_round()
    rid = (last_round.rid + 1) if last_round else 1

    purchased_numbers_to_create = []
    with transaction.atomic():
        for numbers in numbers_list:
            # 3. 입력 유효성 검사 (각 번호 세트별)
            if not isinstance(numbers, list) or len(numbers) != 6:
                raise ValidationError("각 로또 번호 세트는 6개의 숫자로 이루어진 리스트여야 합니다.")
            if len(set(numbers)) != 6:
                raise ValidationError("로또 번호는 중복될 수 없습니다.")
            for num in numbers:
                if not isinstance(num, int) or not (1 <= num <= 45):
                    raise ValidationError("로또 번호는 1에서 45 사이의 정수여야 합니다.")

            # 4. PurchasedNumber 객체 생성 준비
            sorted_numbers = sorted(numbers)
            purchased_number_obj = PurchasedNumber(
                user=user,
                rid=rid,
                number1=sorted_numbers[0],
                number2=sorted_numbers[1],
                number3=sorted_numbers[2],
                number4=sorted_numbers[3],
                number5=sorted_numbers[4],
                number6=sorted_numbers[5],
            )
            purchased_numbers_to_create.append(purchased_number_obj)

        # 5. bulk_create를 사용하여 한 번의 쿼리로 여러 객체를 생성합니다.
        return PurchasedNumber.objects.bulk_create(purchased_numbers_to_create)


def del_purchased_numbers(uid: str, numbers_list: list[list[int]]):
    """
    주어진 UID를 가진 사용자의 특정 구매 번호들을 '삭제' 처리합니다.
    실제 데이터는 삭제하지 않고, 'deleted' 필드를 True로 업데이트합니다.

    Args:
        uid (str): 구매 번호를 삭제할 사용자의 고유 ID.
        numbers_list (list[list[int]]): 삭제할 6개의 숫자로 이루어진 로또 번호 세트들의 리스트.

    Returns:
        int: 성공적으로 '삭제' 처리된 번호의 개수.

    Raises:
        User.DoesNotExist: 해당 UID를 가진 사용자가 없을 경우.
        ValidationError: 유효하지 않은 번호 세트가 포함된 경우.
    """
    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        raise User.DoesNotExist(f"UID '{uid}'를 가진 사용자를 찾을 수 없습니다.")

    q_objects = Q()
    for numbers in numbers_list:
        if not isinstance(numbers, list) or len(numbers) != 6:
            raise ValidationError("각 로또 번호 세트는 6개의 숫자로 이루어진 리스트여야 합니다.")
        
        sorted_numbers = sorted(numbers)
        q_objects |= Q(number1=sorted_numbers[0], number2=sorted_numbers[1], number3=sorted_numbers[2], number4=sorted_numbers[3], number5=sorted_numbers[4], number6=sorted_numbers[5])

    updated_count = PurchasedNumber.objects.filter(user=user, deleted=False).filter(q_objects).update(deleted=True)
    return updated_count


def get_purchased_numbers(uid: str):
    """
    주어진 UID를 가진 사용자의 모든 구매 번호를 조회합니다.

    Args:
        uid (str): 구매 번호를 조회할 사용자의 고유 ID.

    Returns:
        QuerySet: PurchasedNumber 모델의 QuerySet.

    Raises:
        User.DoesNotExist: 해당 UID를 가진 사용자가 없을 경우.
    """
    # User.DoesNotExist는 view에서 처리하므로 여기서는 filter만 사용
    return PurchasedNumber.objects.filter(user__uid=uid, deleted=False).order_by('-created_at')


def add_shared_number(uid: str, rid: int, numbers: list[int], description: str):
    """
    주어진 정보를 바탕으로 공유 번호를 생성하고 저장합니다.

    Args:
        uid (str): 번호를 공유하는 사용자의 고유 ID.
        rid (int): 공유하려는 로또 회차.
        numbers (list[int]): 1에서 45 사이의 중복 없는 6개의 로또 번호 리스트.
        description (str): 공유 번호에 대한 설명.

    Returns:
        SharedNumber: 새로 생성된 SharedNumber 모델 객체.

    Raises:
        User.DoesNotExist: 해당 UID를 가진 사용자가 없을 경우.
        ValidationError: 입력값이 유효하지 않을 경우.
    """
    # 1. 입력 유효성 검사
    if not isinstance(numbers, list) or len(numbers) != 6:
        raise ValidationError("로또 번호는 6개의 숫자로 이루어진 리스트여야 합니다.")
    if len(set(numbers)) != 6:
        raise ValidationError("로또 번호는 중복될 수 없습니다.")
    for num in numbers:
        if not isinstance(num, int) or not (1 <= num <= 45):
            raise ValidationError("로또 번호는 1에서 45 사이의 정수여야 합니다.")

    if not description or not description.strip():
        raise ValidationError("공유 내용(description)은 비워둘 수 없습니다.")

    # 2. 사용자 조회
    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        raise User.DoesNotExist(f"UID '{uid}'를 가진 사용자를 찾을 수 없습니다.")

    # 3. 회차 유효성 검사 (이미 추첨이 끝난 과거 회차는 공유 불가)
    last_round = get_last_round()
    if last_round and rid <= last_round.rid:
        raise ValidationError(f"이미 추첨이 완료된 회차({rid})의 번호는 공유할 수 없습니다. 다음 회차({last_round.rid + 1})부터 공유 가능합니다.")

    # 4. SharedNumber 객체 생성 및 저장
    sorted_numbers = sorted(numbers)
    # get_or_create를 사용하여 중복 생성을 방지합니다.
    # UniqueConstraint에 명시된 모든 필드를 기준으로 조회합니다.
    shared_number, created = SharedNumber.objects.get_or_create(
        user=user,
        rid=rid,
        number1=sorted_numbers[0],
        number2=sorted_numbers[1],
        number3=sorted_numbers[2],
        number4=sorted_numbers[3],
        number5=sorted_numbers[4],
        number6=sorted_numbers[5],
        defaults={
            'description': description.strip()
        }
    )

    # 이미 존재하는 번호 조합이라면 ValidationError를 발생시킵니다.
    if not created:
        raise ValidationError(f"{rid}회차에 이미 공유한 번호 조합입니다.")

    return shared_number


def del_shared_numbers(uid: str, numbers_list: list[list[int]]):
    """
    주어진 UID를 가진 사용자의 특정 공유 번호들을 '삭제' 처리합니다.
    실제 데이터는 삭제하지 않고, 'deleted' 필드를 True로 업데이트합니다.

    Args:
        uid (str): 공유 번호를 삭제할 사용자의 고유 ID.
        numbers_list (list[list[int]]): 삭제할 6개의 숫자로 이루어진 로또 번호 세트들의 리스트.

    Returns:
        int: 성공적으로 '삭제' 처리된 번호의 개수.

    Raises:
        User.DoesNotExist: 해당 UID를 가진 사용자가 없을 경우.
        ValidationError: 유효하지 않은 번호 세트가 포함된 경우.
    """
    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        raise User.DoesNotExist(f"UID '{uid}'를 가진 사용자를 찾을 수 없습니다.")

    q_objects = Q()
    for numbers in numbers_list:
        if not isinstance(numbers, list) or len(numbers) != 6:
            raise ValidationError("각 로또 번호 세트는 6개의 숫자로 이루어진 리스트여야 합니다.")
        
        sorted_numbers = sorted(numbers)
        q_objects |= Q(number1=sorted_numbers[0], number2=sorted_numbers[1], number3=sorted_numbers[2], number4=sorted_numbers[3], number5=sorted_numbers[4], number6=sorted_numbers[5])

    # 사용자의 번호 중, 삭제 요청된 번호 조합과 일치하고 아직 삭제되지 않은 번호들을 업데이트합니다.
    updated_count = SharedNumber.objects.filter(user=user, deleted=False).filter(q_objects).update(deleted=True)
    return updated_count


def get_shared_numbers():
    """
    삭제되지 않은 모든 공유 번호를 조회합니다.

    Returns:
        QuerySet: SharedNumber 모델의 QuerySet.
        최신 데이터가 먼저 오도록 생성일(created_at)의 내림차순으로 정렬됩니다.
    """
    # 삭제되지 않은 번호만 조회하고, 성능을 위해 user 정보도 함께 가져옵니다.
    return SharedNumber.objects.filter(deleted=False).select_related('user').order_by('-created_at')


def get_top_shared_numbers():
    """
    당첨 결과가 좋은 순서대로 공유 번호 목록을 조회합니다.
    - 정렬 순서: 1등 > 2등 > ... > 5등
    - 등수가 같을 경우, 최신 회차 순으로 정렬합니다.

    Returns:
        QuerySet: SharedNumber 모델의 QuerySet.
    """
    return SharedNumber.objects.filter(
        deleted=False,
        result__gt=0  # 1~5등 당첨된 번호만 조회
    ).select_related('user').order_by('result', '-rid')


def get_top_shared_users():
    """
    당첨 횟수가 많은 순서대로 사용자 목록을 조회합니다.
    - 1, 2, 3등 당첨 이력이 있는 사용자만 대상으로 합니다.
    - 정렬 순서: 1등 횟수 > 2등 횟수 > 3등 횟수

    Returns:
        QuerySet: User 모델의 QuerySet.
    """
    return User.objects.filter(
        Q(matches1__gt=0) | Q(matches2__gt=0) | Q(matches3__gt=0)
    ).order_by('-matches1', '-matches2', '-matches3')
