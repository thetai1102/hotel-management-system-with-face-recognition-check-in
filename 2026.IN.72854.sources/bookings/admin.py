from django.contrib import admin
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('customer', 'room', 'check_in_date', 'check_out_date', 'status', 'total_price')
    list_filter = ('status', 'check_in_date', 'check_out_date')
    search_fields = ('customer__full_name', 'room__room_number')