from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'rooms', views.ChatRoomViewSet, basename='chatroom')

urlpatterns = [
    path('', include(router.urls)),
    path('my-invites/', views.my_invites, name='my_invites'),
    path('my-rooms/', views.my_rooms, name='my_rooms'),
    path('join-by-id/', views.join_room_by_id, name='join_room_by_id'),
]
