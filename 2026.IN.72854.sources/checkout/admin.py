from django.contrib import admin
from .models import CheckOut, Payment


@admin.register(CheckOut)
class CheckOutAdmin(admin.ModelAdmin):
    list_display = ('booking', 'check_out_time', 'final_amount', 'staff')
    search_fields = ('booking__customer__full_name',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('booking', 'amount', 'payment_method', 'status', 'payment_date')
    list_filter = ('status', 'payment_method')
    search_fields = ('booking__customer__full_name',)