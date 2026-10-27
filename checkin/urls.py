from django.urls import path
from . import views


urlpatterns = [
    path('', views.face_checkin_view, name='face_checkin'),
    path('success/<int:checkin_id>/', views.checkin_success_view, name='checkin_success'),
    path('history/', views.checkin_history_view, name='checkin_history'),

    path('online/', views.online_face_checkin_view, name='online_face_checkin'),
    path('online/success/<int:booking_id>/', views.online_checkin_success_view, name='online_checkin_success'),
]