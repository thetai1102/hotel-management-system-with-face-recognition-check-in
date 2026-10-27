from django.contrib import admin
from .models import CheckIn


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = (
        'customer',
        'booking',
        'method',
        'check_in_time',
        'face_verified',
        'manual_verified',
        'staff',
    )
    list_filter = (
        'method',
        'face_verified',
        'manual_verified',
        'check_in_time',
    )
    search_fields = (
        'customer__full_name',
        'booking__booking_code',
        'booking__room__room_number',
    )