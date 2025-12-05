from django.urls import path
from . import views

urlpatterns = [
    # 클라이언트가 '/api/lotto/' (이후 경로가 비어있을 때)로 접속하면 views.generate_numbers 함수 실행
    path('', views.generate_numbers, name='generate_numbers'),
    
    # 예시: '/api/lotto/history/'로 접속하면 views.history_list 함수 실행
    # path('history/', views.history_list, name='history_list'),
]