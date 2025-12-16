from django.urls import path
from . import views

urlpatterns = [
    # ROUND
    path('rounds/all', views.get_all_rounds, name='get_all_rounds'), # GET
    path('rounds/last', views.get_last_round, name='get_last_round'), # GET
    path('round/get', views.get_round, name='get_round'), # GET ? rid=XX # TEST

    # STORE
    path('regions', views.get_regions, name='get_regions'), # GET ? (addr1=XX) & (addr2=XX)
    path('stores/region', views.get_stores_by_region, name='get_stores_by_region'), # GET ? (addr1=XX) & (addr2=XX) & (addr3=XX) & page=XX & (size=XX)
    path('stores/nearby', views.get_nearby_stores, name='get_nearby_stores'), # GET ? geo_e=XX & geo_n=XX
    path('stores/round', views.get_round_stores, name='get_round_stores'), # GET ? rid=XX
    path('stores/top', views.get_top_stores, name='get_top_stores'), # GET ? page=XX & (size=XX)
    path('store', views.get_store, name='get_store'), # GET ? sid=XX # TEST

    # USER
    path('user/register', views.register_user, name='register_user'), # POST
    path('user/nick/set', views.set_user_nick, name='set_user_nick'), # POST ? uid=XX & nick=XX

    # USER NUMBER
    path('numbers/user/add', views.add_user_numbers, name='add_user_numbers'), # POST ? uid=XX & numbers=[[1,2,3,4,5,6],..]
    path('numbers/user/del', views.del_user_numbers, name='del_user_numbers'), # POST ? uid=XX & numbers=[[1,2,3,4,5,6],..]
    path('numbers/user/get', views.get_user_numbers, name='get_user_numbers'), # GET ? uid=XX & page=XX & (size=XX)

    # PURCHASED NUMBER
    path('numbers/purchased/add', views.add_purchased_numbers, name='add_purchased_numbers'), # POST ? uid=XX & numbers=[[1,2,3,4,5,6],..]
    path('numbers/purchased/del', views.del_purchased_numbers, name='del_purchased_numbers'), # POST ? uid=XX & numbers=[[1,2,3,4,5,6],..]
    path('numbers/purchased/get', views.get_purchased_numbers, name='get_purchased_numbers'), # GET ? uid=XX & page=XX & (size=XX)

    # SHARED NUMBER
    path('number/shared/add', views.add_shared_number, name='add_shared_number'), # POST ? uid=XX & numbers=[1,2,3,4,5,6] & description=XX
    path('numbers/shared/del', views.del_shared_numbers, name='del_shared_numbers'), # POST ? uid=XX & numbers=[[1,2,3,4,5,6],..]
    path('numbers/shared/get', views.get_shared_numbers, name='get_shared_numbers'), # GET ? (uid=XX) & page=XX & (size=XX)
    path('numbers/shared/top', views.get_top_shared_numbers, name='get_top_shared_numbers'), # GET ? page=XX & size=XX
    path('users/shared/top', views.get_top_shared_users, name='get_top_shared_users'), # GET ? page=XX & size=XX
]
