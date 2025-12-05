from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.utils import timezone
import random

# require_GET 데코레이터를 사용하여 GET 요청만 허용합니다.
@require_GET
def generate_numbers(request):
    """
    랜덤 로또 번호 6개를 생성하여 JSON 형태로 응답하는 API 뷰.
    """
    try:
        # 1. 로또 번호 생성 로직 (1부터 45 중 중복 없이 6개)
        # random.sample()을 사용하여 중복 없는 샘플을 추출
        numbers = sorted(random.sample(range(1, 46), 6))
        
        # 2. JSON 데이터 구성
        data = {
            'status': 'success',
            'message': 'Lotto numbers generated successfully',
            'numbers': numbers,
            'timestamp': timezone.now().isoformat() # ISO 8601 형식의 현재 시간 추가
        }
        
        # 3. HTTP 200 OK와 함께 JSON 응답 반환
        return JsonResponse(data, status=200)
        
    except Exception as e:
        # 오류 발생 시 500 Internal Server Error 응답
        return JsonResponse({
            'status': 'error',
            'message': 'An unexpected error occurred during number generation.',
            'detail': str(e)
        }, status=500)
