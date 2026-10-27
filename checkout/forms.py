from django import forms

from bookings.models import Booking
from customer_portal.models import CustomerBooking

from .models import (
    OnlinePayment,
    Payment,
)


# ============================================================
# STAFF CHECKOUT FORM
# FORM CHECKOUT BOOKING STAFF
# ============================================================

class CheckoutForm(forms.Form):

    booking = forms.ModelChoiceField(
        queryset=Booking.objects.none(),
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
        label="Booking",
    )

    payment_method = forms.ChoiceField(
        choices=Payment.PAYMENT_METHOD,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
        label="Payment Method",
    )

    status = forms.ChoiceField(
        choices=Payment.PAYMENT_STATUS,
        initial="paid",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
        label="Payment Status",
    )

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        # Only Checked In bookings without a CheckOut record
        # may enter the checkout workflow.
        # Chỉ Booking Checked In chưa có bản ghi CheckOut
        # mới được vào workflow checkout.
        self.fields[
            "booking"
        ].queryset = (
            Booking.objects
            .filter(
                status=Booking.STATUS_CHECKED_IN,
                checkout__isnull=True,
            )
            .select_related(
                "customer",
                "room",
                "room__room_type",
            )
            .order_by(
                "-created_at"
            )
        )


# ============================================================
# CUSTOMER PORTAL CHECKOUT FORM
# FORM CHECKOUT CUSTOMER PORTAL
# ============================================================

class OnlineCheckoutForm(forms.Form):

    booking = forms.ModelChoiceField(
        queryset=CustomerBooking.objects.none(),
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
        label="Online Booking",
    )

    payment_method = forms.ChoiceField(
        choices=OnlinePayment.PAYMENT_METHOD,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
        label="Payment Method",
    )

    status = forms.ChoiceField(
        choices=OnlinePayment.PAYMENT_STATUS,
        initial="paid",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
        label="Payment Status",
    )

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        # Only Checked In CustomerBooking records without
        # an OnlineCheckOut record may be selected.
        # Chỉ CustomerBooking Checked In chưa có OnlineCheckOut
        # mới được phép chọn.
        self.fields[
            "booking"
        ].queryset = (
            CustomerBooking.objects
            .filter(
                status=(
                    CustomerBooking.STATUS_CHECKED_IN
                ),
                online_checkout__isnull=True,
            )
            .select_related(
                "customer_user",
                "room",
                "room__room_type",
            )
            .order_by(
                "-created_at"
            )
        )