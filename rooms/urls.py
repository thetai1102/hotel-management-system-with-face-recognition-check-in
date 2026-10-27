from django.urls import path
from . import views


urlpatterns = [
    # Room Type URLs
    path('types/', views.room_type_list, name='room_type_list'),
    path('types/add/', views.room_type_create, name='room_type_create'),
    path('types/<int:pk>/edit/', views.room_type_update, name='room_type_update'),
    path('types/<int:pk>/delete/', views.room_type_delete, name='room_type_delete'),

    # Room URLs
    path('', views.room_list, name='room_list'),
    path('add/', views.room_create, name='room_create'),
    path('<int:pk>/edit/', views.room_update, name='room_update'),
    path('<int:pk>/delete/', views.room_delete, name='room_delete'),
]