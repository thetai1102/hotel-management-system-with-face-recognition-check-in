from django.contrib import admin

from .models import CustomerBooking, CustomerProfile


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "phone",
        "user",
        "identity_number",
        "created_at",
    )

    search_fields = (
        "full_name",
        "phone",
        "user__email",
        "identity_number",
    )

    list_filter = (
        "created_at",
        "updated_at",
    )


@admin.register(CustomerBooking)
class CustomerBookingAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "email",
        "phone",
        "room",
        "check_in_at",
        "check_out_at",
        "status",
        "total_price",
        "created_at",
    )

    search_fields = (
        "full_name",
        "email",
        "phone",
        "identity_number",
    )

    list_filter = (
        "status",
        "created_at",
        "check_in_at",
        "check_out_at",
    )