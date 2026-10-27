from django.urls import path
from . import views


urlpatterns = [
    path('', views.checkout_list, name='checkout_list'),
    path('new/', views.checkout_create, name='checkout_create'),
    path('invoice/<int:checkout_id>/', views.invoice_detail, name='invoice_detail'),

    path('online/', views.online_checkout_create, name='online_checkout'),
    path('online/invoice/<int:booking_id>/', views.online_invoice_detail, name='online_invoice_detail'),
]