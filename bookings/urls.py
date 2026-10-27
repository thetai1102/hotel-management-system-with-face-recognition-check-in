from django.urls import path

from . import views


app_name = "bookings"


urlpatterns = [
    # Staff booking management.
    # Quản lý booking của staff.
    path(
        "",
        views.booking_list,
        name="booking_list",
    ),
    path(
        "add/",
        views.booking_create,
        name="booking_create",
    ),
    path(
        "<int:pk>/",
        views.booking_detail,
        name="booking_detail",
    ),
    path(
        "<int:pk>/edit/",
        views.booking_update,
        name="booking_update",
    ),
    path(
        "<int:pk>/delete/",
        views.booking_delete,
        name="booking_delete",
    ),

    # Customer Portal booking requests handled by staff.
    # Các booking request từ Customer Portal do staff xử lý.
    path(
        "online-requests/",
        views.online_booking_requests,
        name="online_booking_requests",
    ),
    path(
        "online-requests/<int:booking_id>/",
        views.online_booking_detail,
        name="online_booking_detail",
    ),
    path(
        "online-requests/<int:booking_id>/confirm/",
        views.confirm_online_booking,
        name="confirm_online_booking",
    ),
    path(
        "online-requests/<int:booking_id>/cancel/",
        views.cancel_online_booking,
        name="cancel_online_booking",
    ),
]