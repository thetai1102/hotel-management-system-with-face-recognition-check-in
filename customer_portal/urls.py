from django.urls import path

from . import views

app_name = "customer_portal"

urlpatterns = [
    path("customer/register/", views.customer_register, name="customer_register"),
    path("customer/login/", views.customer_login, name="customer_login"),
    path("customer/logout/", views.customer_logout, name="customer_logout"),

    path("customer/dashboard/", views.customer_dashboard, name="customer_dashboard"),
    path("customer/profile/", views.customer_profile, name="customer_profile"),

    path("customer/rooms/", views.customer_room_list, name="customer_room_list"),
    path("customer/rooms/<int:room_id>/", views.customer_room_detail, name="customer_room_detail"),
    path("customer/rooms/<int:room_id>/book/", views.customer_book_room, name="customer_book_room"),

    path("customer/my-bookings/", views.customer_my_bookings, name="customer_my_bookings"),
]