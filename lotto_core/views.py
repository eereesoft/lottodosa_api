from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone
import random
import json
from django.core.exceptions import ValidationError
from django.forms.models import model_to_dict
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from . import services


# ROUND


@require_GET
def get_all_rounds(request):
    """
    모든 회차 정보를 JSON 형태로 응답하는 API 뷰.
    """
    try:
        all_rounds = services.get_all_rounds()
        # QuerySet을 직접 JSON으로 변환할 수 없으므로, values()를 사용해 딕셔너리 리스트로 변환합니다.
        data = list(all_rounds.values())

        return JsonResponse(data, safe=False, status=200, json_dumps_params={'ensure_ascii': False})

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': 'An unexpected error occurred while fetching rounds.',
            'detail': str(e)
        }, status=500)


@require_GET
def get_last_round(request):
    """
    가장 최신 회차 정보를 JSON 형태로 응답하는 API 뷰.
    """
    try:
        last_round = services.get_last_round()
        if last_round:
            # model_to_dict를 사용하여 모델 인스턴스를 딕셔너리로 변환합니다.
            data = model_to_dict(last_round)
            return JsonResponse(data, status=200, json_dumps_params={'ensure_ascii': False})
        else:
            # 데이터가 없을 경우 404 Not Found 응답을 반환합니다.
            return JsonResponse({'status': 'error', 'message': 'No round data found.'}, status=404)

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': 'An unexpected error occurred while fetching the last round.'
        }, status=500)


@require_GET
def get_round(request):
    """
    주어진 회차(rid)에 해당하는 상세 정보를 JSON 형태로 응답하는 API 뷰.
    """
    rid_str = request.GET.get('rid')

    if not rid_str:
        return JsonResponse({'status': 'error', 'message': 'rid는 필수 입력값입니다.'}, status=400)

    try:
        rid = int(rid_str)
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': 'rid는 유효한 정수여야 합니다.'}, status=400)

    try:
        round_instance = services.get_round(rid)
        data = model_to_dict(round_instance)
        return JsonResponse(data, status=200, json_dumps_params={'ensure_ascii': False})

    except services.Round.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': f'{rid}회차 정보를 찾을 수 없습니다.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': '회차 정보 조회 중 예상치 못한 오류가 발생했습니다.'}, status=500)


# STORE


@require_GET
def get_regions(request):
    """
    지역 정보(시/도, 시/군/구, 읍/면/동)를 계층적으로 조회하는 API 뷰.
    """
    addr1 = request.GET.get('addr1')
    addr2 = request.GET.get('addr2')

    try:
        regions = services.get_regions(addr1=addr1, addr2=addr2)
        return JsonResponse(regions, safe=False, status=200, json_dumps_params={'ensure_ascii': False})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': '지역 정보 조회 중 예상치 못한 오류가 발생했습니다.'}, status=500)


@require_GET
def get_stores_by_region(request):
    """
    지역별 판매점 목록을 조회하는 API 뷰.
    GET 요청으로 addr1, addr2, addr3, page, size를 받습니다.
    - page=0이면 전체, page>=1이면 페이지네이션을 적용합니다.
    """
    addr1 = request.GET.get('addr1')
    addr2 = request.GET.get('addr2')
    addr3 = request.GET.get('addr3')
    page_str = request.GET.get('page')

    if page_str is None:
        return JsonResponse({'status': 'error', 'message': 'page는 필수 입력값입니다.'}, status=400)

    try:
        stores_qs = services.get_stores_by_region(addr1, addr2, addr3)

        try:
            page = int(page_str)
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'page는 유효한 정수여야 합니다.'}, status=400)

        if page == 0:
            # page가 0이면 전체 항목을 페이지네이션 구조에 맞춰 반환
            all_items = list(stores_qs.values('sid', 'sname', 'phone', 'addr_doro', 'addr4', 'geo_n', 'geo_e', 'matches1', 'matches2'))
            data = {
                'total_items': len(all_items),
                'total_pages': 1,
                'current_page': 0,
                'items': all_items
            }
            return JsonResponse(data, status=200, json_dumps_params={'ensure_ascii': False})

        elif page >= 1:
            # page가 1 이상이면 size 파라미터가 필수
            size_str = request.GET.get('size')
            if not size_str:
                return JsonResponse({'status': 'error', 'message': 'page가 1 이상일 경우 size는 필수 입력값입니다.'}, status=400)

            try:
                size = int(size_str)
                if size <= 0: raise ValueError
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'size는 0보다 큰 정수여야 합니다.'}, status=400)

            paginator = Paginator(stores_qs, size)
            try:
                paginated_page = paginator.page(page)
            except EmptyPage:
                return JsonResponse({'status': 'error', 'message': '요청한 페이지가 존재하지 않습니다.'}, status=404)

            data = {
                'total_items': paginator.count,
                'total_pages': paginator.num_pages,
                'current_page': paginated_page.number,
                'items': list(paginated_page.object_list.values('sid', 'sname', 'phone', 'addr_doro', 'addr4', 'geo_n', 'geo_e', 'matches1', 'matches2'))
            }
            return JsonResponse(data, status=200, json_dumps_params={'ensure_ascii': False})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': '지역별 판매점 조회 중 예상치 못한 오류가 발생했습니다.'}, status=500)


@require_GET
def get_nearby_stores(request):
    """
    주어진 좌표 근처의 판매점 목록을 JSON 형태로 응답하는 API 뷰.
    GET 요청으로 geo_n(위도)과 geo_e(경도)를 받습니다.
    """
    geo_n_str = request.GET.get('geo_n')
    geo_e_str = request.GET.get('geo_e')

    if not geo_n_str or not geo_e_str:
        return JsonResponse({
            'status': 'error',
            'message': 'geo_n(위도)과 geo_e(경도)는 필수 입력값입니다.'
        }, status=400)

    try:
        latitude = float(geo_n_str)
        longitude = float(geo_e_str)
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': '위도와 경도는 유효한 숫자여야 합니다.'}, status=400)

    try:
        nearby_stores = services.get_nearby_stores(latitude, longitude)
        data = list(nearby_stores.values('sid', 'sname', 'phone', 'addr_doro', 'addr4', 'geo_n', 'geo_e', 'matches1', 'matches2'))
        return JsonResponse(data, safe=False, status=200, json_dumps_params={'ensure_ascii': False})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': '주변 판매점 조회 중 예상치 못한 오류가 발생했습니다.'}, status=500)


@require_GET
def get_round_stores(request):
    """
    특정 회차에 당첨된 판매점 목록과 당첨 내역을 조회하는 API 뷰.
    GET 요청으로 rid를 받습니다.
    """
    rid_str = request.GET.get('rid')

    if not rid_str:
        return JsonResponse({'status': 'error', 'message': 'rid는 필수 입력값입니다.'}, status=400)

    try:
        rid = int(rid_str)
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': 'rid는 유효한 정수여야 합니다.'}, status=400)

    try:
        # 해당 회차에 당첨된 판매점 목록을 가져옵니다.
        # 이제 stores_qs는 StoreWin 객체들의 QuerySet입니다.
        winning_store_wins_qs = services.get_round_stores(rid)

        # 각 판매점 정보와 해당 회차의 당첨 내역을 함께 조합합니다.
        data = []
        for store_win in winning_store_wins_qs:
            # StoreWin 객체와 select_related로 가져온 Store 객체에서 필요한 필드를 추출합니다.
            win_data = {
                'sid': store_win.store.sid,
                'enabled': store_win.store.enabled,
                'sname': store_win.store.sname,
                'phone': store_win.store.phone,
                'addr4': store_win.store.addr4,
                'addr_doro': store_win.store.addr_doro,
                'geo_e': store_win.store.geo_e,
                'geo_n': store_win.store.geo_n,
                'matches1': store_win.store.matches1,
                'matches2': store_win.store.matches2,
                'rank': store_win.rank,
                'auto': store_win.auto,
            }
            data.append(win_data)

        return JsonResponse(data, safe=False, status=200, json_dumps_params={'ensure_ascii': False})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': '회차별 판매점 조회 중 예상치 못한 오류가 발생했습니다.'}, status=500)


@require_GET
def get_top_stores(request):
    """
    1등 당첨 횟수가 많은 순서로 판매점 목록을 조회하는 API 뷰. 
    GET 요청으로 page를 받습니다. page=0이면 전체, page>=1이면 페이지네이션을 적용합니다.
    """
    page_str = request.GET.get('page')

    if page_str is None:
        return JsonResponse({'status': 'error', 'message': 'page는 필수 입력값입니다.'}, status=400)

    try:
        top_stores_qs = services.get_top_stores()

        try:
            page = int(page_str)
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'page는 유효한 정수여야 합니다.'}, status=400)

        if page == 0:
            # page가 0이면 전체 항목을 페이지네이션 구조에 맞춰 반환
            all_items = list(top_stores_qs.values('sid', 'sname', 'phone', 'addr_doro', 'addr4', 'geo_n', 'geo_e', 'matches1', 'matches2', 'enabled'))
            data = {
                'total_items': len(all_items),
                'total_pages': 1,
                'current_page': 0,
                'items': all_items
            }
            return JsonResponse(data, status=200, json_dumps_params={'ensure_ascii': False})

        elif page >= 1:
            # page가 1 이상이면 size 파라미터가 필수
            size_str = request.GET.get('size')
            if not size_str:
                return JsonResponse({'status': 'error', 'message': 'page가 1 이상일 경우 size는 필수 입력값입니다.'}, status=400)

            try:
                size = int(size_str)
                if size <= 0: raise ValueError
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'size는 0보다 큰 정수여야 합니다.'}, status=400)

            paginator = Paginator(top_stores_qs, size)
            try:
                paginated_page = paginator.page(page)
            except EmptyPage:
                return JsonResponse({'status': 'error', 'message': '요청한 페이지가 존재하지 않습니다.'}, status=404)

            data = {
                'total_items': paginator.count,
                'total_pages': paginator.num_pages,
                'current_page': paginated_page.number,
                'items': list(paginated_page.object_list.values('sid', 'sname', 'phone', 'addr_doro', 'addr4', 'geo_n', 'geo_e', 'matches1', 'matches2', 'enabled'))
            }
            return JsonResponse(data, status=200, json_dumps_params={'ensure_ascii': False})

        else:
            # page가 음수인 경우
            return JsonResponse({'status': 'error', 'message': 'page는 0 또는 양의 정수여야 합니다.'}, status=400)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': '상위 판매점 조회 중 예상치 못한 오류가 발생했습니다.'}, status=500)


@require_GET
def get_store(request):
    """
    주어진 ID(sid)에 해당하는 판매점의 상세 정보를 조회하는 API 뷰.
    GET 요청으로 sid를 받습니다.
    """
    sid_str = request.GET.get('sid')

    if not sid_str:
        return JsonResponse({'status': 'error', 'message': 'sid는 필수 입력값입니다.'}, status=400)

    try:
        sid = int(sid_str)
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': 'sid는 유효한 정수여야 합니다.'}, status=400)

    try:
        store = services.get_store(sid)
        # model_to_dict를 사용하여 모델 인스턴스를 딕셔너리로 변환합니다.
        # enabled 필드는 제외합니다.
        data = model_to_dict(store, exclude=['enabled'])
        return JsonResponse(data, status=200, json_dumps_params={'ensure_ascii': False})

    except services.Store.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': f'ID가 {sid}인 판매점을 찾을 수 없습니다.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': '판매점 정보 조회 중 예상치 못한 오류가 발생했습니다.'}, status=500)


# USER


@require_POST
def register_user(request):
    """
    새로운 사용자를 등록하고 생성된 사용자 정보를 응답하는 API 뷰.
    """
    try:
        new_user = services.register_user()
        data = model_to_dict(new_user, fields=['uid', 'nick', 'created_at', 'updated_at'])
        return JsonResponse(data, status=201, json_dumps_params={'ensure_ascii': False})  # 201 Created

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': 'An unexpected error occurred during user registration.'
        }, status=500)


@require_POST
def set_user_nick(request):
    """
    사용자의 닉네임을 변경하는 API 뷰.
    POST 요청으로 uid와 new_nick을 받습니다.
    """
    uid = request.POST.get('uid')
    new_nick = request.POST.get('nick') # 요청 바디에서 'nick' 파라미터로 새 닉네임을 받습니다.

    if not uid or not new_nick:
        return JsonResponse({
            'status': 'error',
            'message': 'UID와 새로운 닉네임은 필수 입력값입니다.'
        }, status=400)

    try:
        updated_user = services.set_user_nick(uid, new_nick)
        data = model_to_dict(updated_user, fields=['uid', 'nick', 'created_at', 'updated_at'])
        return JsonResponse(data, status=200, json_dumps_params={'ensure_ascii': False})

    except services.User.DoesNotExist as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=404)
    except ValidationError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': '닉네임 변경 중 예상치 못한 오류가 발생했습니다.'
        }, status=500)


# USER NUMBER


@require_POST
def add_user_numbers(request):
    """
    주어진 UID를 가진 사용자의 로또 번호를 저장하는 API 뷰.
    POST 요청으로 uid와 numbers(JSON 배열 문자열)를 받습니다.
    """
    uid = request.POST.get('uid')
    numbers_str = request.POST.get('numbers')

    if not uid or not numbers_str:
        return JsonResponse({
            'status': 'error',
            'message': 'UID와 로또 번호는 필수 입력값입니다.'
        }, status=400)

    try:
        numbers = json.loads(numbers_str)
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': '로또 번호 형식이 올바르지 않습니다. JSON 배열 형태여야 합니다.'
        }, status=400)

    try:
        new_user_numbers = services.add_user_numbers(uid, numbers)

        # 생성된 객체들을 딕셔너리 리스트로 변환
        data = [
            model_to_dict(n, fields=['id', 'number1', 'number2', 'number3', 'number4', 'number5', 'number6', 'created_at'])
            for n in new_user_numbers
        ]

        return JsonResponse({
            'status': 'success',
            'message': f'{len(data)}개의 로또 번호가 성공적으로 저장되었습니다.',
            'user_numbers': data
        }, status=201, json_dumps_params={'ensure_ascii': False})

    except services.User.DoesNotExist as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=404)
    except ValidationError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': '로또 번호 저장 중 예상치 못한 오류가 발생했습니다.',
            'detail': str(e)
        }, status=500)


@require_POST
def del_user_numbers(request):
    """
    사용자가 저장한 로또 번호를 삭제 처리하는 API 뷰.
    POST 요청으로 uid와 numbers(JSON 배열의 배열)를 받습니다.
    """
    uid = request.POST.get('uid')
    numbers_str = request.POST.get('numbers')

    if not uid or not numbers_str:
        return JsonResponse({
            'status': 'error',
            'message': 'UID와 로또 번호는 필수 입력값입니다.'
        }, status=400)

    try:
        numbers = json.loads(numbers_str)
        if not isinstance(numbers, list):
            raise ValidationError("numbers는 배열 형태여야 합니다.")
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': '로또 번호 형식이 올바르지 않습니다. JSON 배열 형태여야 합니다.'
        }, status=400)
    except ValidationError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    try:
        deleted_count = services.del_user_numbers(uid, numbers)
        return JsonResponse({'status': 'success', 'message': f'총 {deleted_count}개의 로또 번호가 성공적으로 삭제 처리되었습니다.'}, status=200)

    except services.User.DoesNotExist as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=404)
    except ValidationError as e:
        return JsonResponse({'status': 'error', 'message': e.message}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': '번호 삭제 중 예상치 못한 오류가 발생했습니다.', 'detail': str(e)}, status=500)


@require_GET
def get_user_numbers(request):
    """
    주어진 UID를 가진 사용자의 로또 번호를 조회하는 API 뷰.
    GET 요청으로 uid와 page를 받습니다. page=0이면 전체, page>=1이면 페이지네이션을 적용합니다.
    """
    uid = request.GET.get('uid')
    page_str = request.GET.get('page')

    if not uid or page_str is None:
        return JsonResponse({
            'status': 'error',
            'message': 'UID와 page는 필수 입력값입니다.'
        }, status=400)

    try:
        # 먼저 사용자가 존재하는지 확인합니다.
        if not services.User.objects.filter(uid=uid).exists():
            raise services.User.DoesNotExist(f"UID '{uid}'를 가진 사용자를 찾을 수 없습니다.")

        try:
            page = int(page_str)
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'page는 유효한 정수여야 합니다.'}, status=400)

        user_numbers_qs = services.get_user_numbers(uid)

        if page == 0:
            # page가 0이면 전체 항목을 페이지네이션 구조에 맞춰 반환
            all_items = list(user_numbers_qs.values('id', 'number1', 'number2', 'number3', 'number4', 'number5', 'number6', 'created_at'))
            data = {
                'total_items': len(all_items),
                'total_pages': 1,
                'current_page': 0,
                'items': all_items
            }
            return JsonResponse(data, status=200, json_dumps_params={'ensure_ascii': False})

        elif page >= 1:
            # page가 1 이상이면 size 파라미터가 필수
            size_str = request.GET.get('size')
            if not size_str:
                return JsonResponse({'status': 'error', 'message': 'page가 1 이상일 경우 size는 필수 입력값입니다.'}, status=400)

            try:
                size = int(size_str)
                if size <= 0: raise ValueError
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'size는 0보다 큰 정수여야 합니다.'}, status=400)

            paginator = Paginator(user_numbers_qs, size)
            try:
                paginated_page = paginator.page(page)
            except EmptyPage:
                return JsonResponse({'status': 'error', 'message': '요청한 페이지가 존재하지 않습니다.'}, status=404)

            data = {
                'total_items': paginator.count,
                'total_pages': paginator.num_pages,
                'current_page': paginated_page.number,
                'items': list(paginated_page.object_list.values('id', 'number1', 'number2', 'number3', 'number4', 'number5', 'number6', 'created_at'))
            }
            return JsonResponse(data, status=200, json_dumps_params={'ensure_ascii': False})

        else:
            # page가 음수인 경우
            return JsonResponse({'status': 'error', 'message': 'page는 0 또는 양의 정수여야 합니다.'}, status=400)

    except services.User.DoesNotExist as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': '번호 조회 중 예상치 못한 오류가 발생했습니다.'}, status=500)


# PURCHASED NUMBER


@require_POST
def add_purchased_numbers(request):
    """
    사용자가 구매한 로또 번호 세트들을 저장하는 API 뷰.
    POST 요청으로 uid와 numbers(JSON 배열의 배열)를 받습니다.
    """
    uid = request.POST.get('uid')
    numbers_str = request.POST.get('numbers')

    if not uid or not numbers_str:
        return JsonResponse({
            'status': 'error',
            'message': 'UID와 로또 번호는 필수 입력값입니다.'
        }, status=400)

    try:
        numbers = json.loads(numbers_str)
        if not isinstance(numbers, list):
            raise ValidationError("numbers는 배열 형태여야 합니다.")
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': '로또 번호 형식이 올바르지 않습니다. JSON 배열 형태여야 합니다.'
        }, status=400)
    except ValidationError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    try:
        new_purchased_numbers = services.add_purchased_numbers(uid, numbers)

        data = [
            model_to_dict(n, exclude=['deleted']) for n in new_purchased_numbers
        ]

        return JsonResponse({
            'status': 'success',
            'message': f'{len(data)}개의 구매 번호가 성공적으로 저장되었습니다.',
            'purchased_numbers': data
        }, status=201, json_dumps_params={'ensure_ascii': False})

    except services.User.DoesNotExist as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=404)
    except ValidationError as e:
        return JsonResponse({'status': 'error', 'message': e.message}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': '구매 번호 저장 중 예상치 못한 오류가 발생했습니다.', 'detail': str(e)}, status=500)


@require_POST
def del_purchased_numbers(request):
    """
    사용자가 구매한 로또 번호를 삭제 처리하는 API 뷰.
    POST 요청으로 uid와 numbers(JSON 배열의 배열)를 받습니다.
    """
    uid = request.POST.get('uid')
    numbers_str = request.POST.get('numbers')

    if not uid or not numbers_str:
        return JsonResponse({'status': 'error', 'message': 'UID와 로또 번호는 필수 입력값입니다.'}, status=400)

    try:
        numbers = json.loads(numbers_str)
        if not isinstance(numbers, list):
            raise ValidationError("numbers는 배열 형태여야 합니다.")
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': '로또 번호 형식이 올바르지 않습니다. JSON 배열 형태여야 합니다.'}, status=400)
    except ValidationError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    try:
        deleted_count = services.del_purchased_numbers(uid, numbers)
        return JsonResponse({'status': 'success', 'message': f'총 {deleted_count}개의 구매 번호가 성공적으로 삭제 처리되었습니다.'}, status=200)

    except services.User.DoesNotExist as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=404)
    except ValidationError as e:
        return JsonResponse({'status': 'error', 'message': e.message}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': '구매 번호 삭제 중 예상치 못한 오류가 발생했습니다.', 'detail': str(e)}, status=500)


@require_GET
def get_purchased_numbers(request):
    """
    주어진 UID를 가진 사용자의 구매 번호를 조회하는 API 뷰.
    GET 요청으로 uid와 page를 받습니다. page=0이면 전체, page>=1이면 페이지네이션을 적용합니다.
    """
    uid = request.GET.get('uid')
    page_str = request.GET.get('page')

    if not uid or page_str is None:
        return JsonResponse({
            'status': 'error',
            'message': 'UID와 page는 필수 입력값입니다.'
        }, status=400)

    try:
        # 먼저 사용자가 존재하는지 확인합니다.
        if not services.User.objects.filter(uid=uid).exists():
            raise services.User.DoesNotExist(f"UID '{uid}'를 가진 사용자를 찾을 수 없습니다.")

        try:
            page = int(page_str)
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'page는 유효한 정수여야 합니다.'}, status=400)

        purchased_numbers_qs = services.get_purchased_numbers(uid)

        if page == 0:
            # page가 0이면 전체 항목을 페이지네이션 구조에 맞춰 반환
            all_items = list(purchased_numbers_qs.values('id', 'rid', 'number1', 'number2', 'number3', 'number4', 'number5', 'number6', 'result', 'created_at'))
            data = {
                'total_items': len(all_items),
                'total_pages': 1,
                'current_page': 0,
                'items': all_items
            }
            return JsonResponse(data, status=200, json_dumps_params={'ensure_ascii': False})

        elif page >= 1:
            # page가 1 이상이면 size 파라미터가 필수
            size_str = request.GET.get('size')
            if not size_str:
                return JsonResponse({'status': 'error', 'message': 'page가 1 이상일 경우 size는 필수 입력값입니다.'}, status=400)

            try:
                size = int(size_str)
                if size <= 0: raise ValueError
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'size는 0보다 큰 정수여야 합니다.'}, status=400)

            paginator = Paginator(purchased_numbers_qs, size)
            paginated_page = paginator.page(page)

            data = {
                'total_items': paginator.count,
                'total_pages': paginator.num_pages,
                'current_page': paginated_page.number,
                'items': list(paginated_page.object_list.values('id', 'rid', 'number1', 'number2', 'number3', 'number4', 'number5', 'number6', 'result', 'created_at'))
            }
            return JsonResponse(data, status=200, json_dumps_params={'ensure_ascii': False})

    except services.User.DoesNotExist as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=404)
    except EmptyPage:
        return JsonResponse({'status': 'error', 'message': '요청한 페이지가 존재하지 않습니다.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': '구매 번호 조회 중 예상치 못한 오류가 발생했습니다.'}, status=500)


# SHARED NUMBER


@require_POST
def add_shared_number(request):
    """
    사용자가 다음 회차에 대한 로또 번호를 공유하는 API 뷰.
    POST 요청으로 uid, numbers(JSON 배열 문자열), description을 받습니다.
    공유될 회차(rid)는 현재 DB에 저장된 마지막 회차의 다음 회차로 자동 설정됩니다.
    """
    uid = request.POST.get('uid')
    numbers_str = request.POST.get('numbers')
    description = request.POST.get('description')

    if not all([uid, numbers_str, description]):
        return JsonResponse({
            'status': 'error',
            'message': 'uid, numbers, description은 필수 입력값입니다.'
        }, status=400)

    try:
        numbers = json.loads(numbers_str)
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': '로또 번호 형식이 올바르지 않습니다. JSON 배열 형태여야 합니다.'
        }, status=400)

    try:
        # DB에서 마지막 회차 정보를 가져와 다음 회차 번호를 결정합니다.
        last_round = services.get_last_round()
        rid = (last_round.rid + 1) if last_round else 1

        new_shared_number = services.add_shared_number(uid, rid, numbers, description)

        data = model_to_dict(new_shared_number)
        data['user_nick'] = new_shared_number.user.nick # 응답에 사용자 닉네임 추가

        return JsonResponse({
            'status': 'success',
            'message': '로또 번호가 성공적으로 공유되었습니다.',
            'shared_number': data
        }, status=201, json_dumps_params={'ensure_ascii': False})

    except services.User.DoesNotExist as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=404)
    except ValidationError as e:
        # 서비스 레이어에서 발생한 유효성 검사 오류(중복 포함)를 처리합니다.
        return JsonResponse({'status': 'error', 'message': e.message}, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': '번호 공유 중 예상치 못한 오류가 발생했습니다.'
        }, status=500)


@require_POST
def del_shared_numbers(request):
    """
    사용자가 공유한 로또 번호를 삭제 처리하는 API 뷰.
    POST 요청으로 uid와 numbers(JSON 배열의 배열)를 받습니다.
    """
    uid = request.POST.get('uid')
    numbers_str = request.POST.get('numbers')

    if not uid or not numbers_str:
        return JsonResponse({'status': 'error', 'message': 'UID와 로또 번호는 필수 입력값입니다.'}, status=400)

    try:
        numbers = json.loads(numbers_str)
        if not isinstance(numbers, list):
            raise ValidationError("numbers는 배열 형태여야 합니다.")
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': '로또 번호 형식이 올바르지 않습니다. JSON 배열 형태여야 합니다.'
        }, status=400)
    except ValidationError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    try:
        deleted_count = services.del_shared_numbers(uid, numbers)
        return JsonResponse({'status': 'success', 'message': f'총 {deleted_count}개의 공유 번호가 성공적으로 삭제 처리되었습니다.'}, status=200)

    except services.User.DoesNotExist as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=404)
    except ValidationError as e:
        return JsonResponse({'status': 'error', 'message': e.message}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': '공유 번호 삭제 중 예상치 못한 오류가 발생했습니다.', 'detail': str(e)}, status=500)


@require_GET
def get_shared_numbers(request):
    """
    공유된 번호를 조회하는 API 뷰.
    GET 요청으로 uid, page를 받습니다. page=0이면 전체, page>=1이면 페이지네이션을 적용합니다.
    uid 파라미터로 필터링할 수 있습니다.
    """
    uid = request.GET.get('uid')
    page_str = request.GET.get('page')

    if page_str is None:
        return JsonResponse({'status': 'error', 'message': 'page는 필수 입력값입니다.'}, status=400)

    try:
        # 서비스 함수를 호출하여 기본 쿼리셋을 가져옵니다.
        shared_numbers_qs = services.get_shared_numbers()

        # uid 파라미터가 있으면 필터링합니다.
        if uid:
            shared_numbers_qs = shared_numbers_qs.filter(user__uid=uid)

        try:
            page = int(page_str)
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'page는 유효한 정수여야 합니다.'}, status=400)

        if page == 0:
            # page가 0이면 전체 항목을 페이지네이션 구조에 맞춰 반환
            all_items = list(shared_numbers_qs.values('id', 'rid', 'number1', 'number2', 'number3', 'number4', 'number5', 'number6', 'description', 'result', 'created_at', 'user__nick'))
            data = {
                'total_items': len(all_items),
                'total_pages': 1,
                'current_page': 0,
                'items': all_items
            }
            return JsonResponse(data, status=200, json_dumps_params={'ensure_ascii': False})

        elif page >= 1:
            # page가 1 이상이면 size 파라미터가 필수
            size_str = request.GET.get('size')
            if not size_str:
                return JsonResponse({'status': 'error', 'message': 'page가 1 이상일 경우 size는 필수 입력값입니다.'}, status=400)

            try:
                size = int(size_str)
                if size <= 0: raise ValueError
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'size는 0보다 큰 정수여야 합니다.'}, status=400)

            paginator = Paginator(shared_numbers_qs, size)
            try:
                paginated_page = paginator.page(page)
            except EmptyPage:
                return JsonResponse({'status': 'error', 'message': '요청한 페이지가 존재하지 않습니다.'}, status=404)

            data = {
                'total_items': paginator.count,
                'total_pages': paginator.num_pages,
                'current_page': paginated_page.number,
                'items': list(paginated_page.object_list.values('id', 'rid', 'number1', 'number2', 'number3', 'number4', 'number5', 'number6', 'description', 'result', 'created_at', 'user__nick'))
            }
            return JsonResponse(data, status=200, json_dumps_params={'ensure_ascii': False})

        else:
            # page가 음수인 경우
            return JsonResponse({'status': 'error', 'message': 'page는 0 또는 양의 정수여야 합니다.'}, status=400)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': '공유 번호 조회 중 예상치 못한 오류가 발생했습니다.'}, status=500)


@require_GET
def get_top_shared_numbers(request):
    """
    당첨 결과가 좋은 순서대로 공유 번호 목록을 조회하는 API 뷰.
    GET 요청으로 page를 받습니다. page=0이면 전체, page>=1이면 페이지네이션을 적용합니다.
    """
    page_str = request.GET.get('page')

    if page_str is None:
        return JsonResponse({'status': 'error', 'message': 'page는 필수 입력값입니다.'}, status=400)

    try:
        top_numbers_qs = services.get_top_shared_numbers()

        try:
            page = int(page_str)
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'page는 유효한 정수여야 합니다.'}, status=400)

        if page == 0:
            # page가 0이면 전체 항목을 페이지네이션 구조에 맞춰 반환
            all_items = list(top_numbers_qs.values('id', 'rid', 'number1', 'number2', 'number3', 'number4', 'number5', 'number6', 'description', 'result', 'created_at', 'user__nick'))
            data = {
                'total_items': len(all_items),
                'total_pages': 1,
                'current_page': 0,
                'items': all_items
            }
            return JsonResponse(data, status=200, json_dumps_params={'ensure_ascii': False})

        elif page >= 1:
            # page가 1 이상이면 size 파라미터가 필수
            size_str = request.GET.get('size')
            if not size_str:
                return JsonResponse({'status': 'error', 'message': 'page가 1 이상일 경우 size는 필수 입력값입니다.'}, status=400)

            try:
                size = int(size_str)
                if size <= 0: raise ValueError
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'size는 0보다 큰 정수여야 합니다.'}, status=400)

            paginator = Paginator(top_numbers_qs, size)
            try:
                paginated_page = paginator.page(page)
            except EmptyPage:
                return JsonResponse({'status': 'error', 'message': '요청한 페이지가 존재하지 않습니다.'}, status=404)

            data = {
                'total_items': paginator.count,
                'total_pages': paginator.num_pages,
                'current_page': paginated_page.number,
                'items': list(paginated_page.object_list.values('id', 'rid', 'number1', 'number2', 'number3', 'number4', 'number5', 'number6', 'description', 'result', 'created_at', 'user__nick'))
            }
            return JsonResponse(data, status=200, json_dumps_params={'ensure_ascii': False})

        else:
            # page가 음수인 경우
            return JsonResponse({'status': 'error', 'message': 'page는 0 또는 양의 정수여야 합니다.'}, status=400)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': '상위 공유 번호 조회 중 예상치 못한 오류가 발생했습니다.'}, status=500)


@require_GET
def get_top_shared_users(request):
    """
    당첨 횟수가 많은 순서대로 사용자 목록을 조회하는 API 뷰.
    GET 요청으로 page를 받습니다. page=0이면 전체, page>=1이면 페이지네이션을 적용합니다.
    """
    page_str = request.GET.get('page')

    if page_str is None:
        return JsonResponse({'status': 'error', 'message': 'page는 필수 입력값입니다.'}, status=400)

    try:
        top_users_qs = services.get_top_shared_users()

        try:
            page = int(page_str)
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'page는 유효한 정수여야 합니다.'}, status=400)

        if page == 0:
            # page가 0이면 전체 항목을 페이지네이션 구조에 맞춰 반환
            all_items = list(top_users_qs.values('uid', 'nick', 'matches1', 'matches2', 'matches3', 'created_at'))
            data = {
                'total_items': len(all_items),
                'total_pages': 1,
                'current_page': 0,
                'items': all_items
            }
            return JsonResponse(data, status=200, json_dumps_params={'ensure_ascii': False})

        elif page >= 1:
            # page가 1 이상이면 size 파라미터가 필수
            size_str = request.GET.get('size')
            if not size_str:
                return JsonResponse({'status': 'error', 'message': 'page가 1 이상일 경우 size는 필수 입력값입니다.'}, status=400)

            try:
                size = int(size_str)
                if size <= 0: raise ValueError
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'size는 0보다 큰 정수여야 합니다.'}, status=400)

            paginator = Paginator(top_users_qs, size)
            try:
                paginated_page = paginator.page(page)
            except EmptyPage:
                return JsonResponse({'status': 'error', 'message': '요청한 페이지가 존재하지 않습니다.'}, status=404)

            data = {
                'total_items': paginator.count,
                'total_pages': paginator.num_pages,
                'current_page': paginated_page.number,
                'items': list(paginated_page.object_list.values('uid', 'nick', 'matches1', 'matches2', 'matches3', 'created_at'))
            }
            return JsonResponse(data, status=200, json_dumps_params={'ensure_ascii': False})

        else:
            # page가 음수인 경우
            return JsonResponse({'status': 'error', 'message': 'page는 0 또는 양의 정수여야 합니다.'}, status=400)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': '상위 사용자 조회 중 예상치 못한 오류가 발생했습니다.'}, status=500)
