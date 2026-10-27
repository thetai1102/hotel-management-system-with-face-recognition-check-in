from django.conf import settings
from django.db import models

from bookings.models import Booking
from customer_portal.models import CustomerBooking


class CheckOut(models.Model):
    """
    Store checkout history for staff/manual bookings.
    Lưu lịch sử checkout cho booking staff/thủ công.
    """

    booking = models.OneToOneField(
        Booking,
        on_delete=models.PROTECT,
    )

    check_out_time = models.DateTimeField(
        auto_now_add=True
    )

    # Store the final amount at the moment of checkout.
    # Lưu số tiền cuối cùng tại thời điểm checkout.
    final_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    # Store the staff member who completed checkout.
    # Lưu nhân viên thực hiện checkout.
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    def __str__(self):
        return (
            f"Checkout: "
            f"{self.booking.customer.full_name}"
        )


class Payment(models.Model):
    PAYMENT_METHOD = [
        ("cash", "Cash"),
        ("card", "Card"),
        ("bank_transfer", "Bank Transfer"),
    ]

    PAYMENT_STATUS = [
        ("unpaid", "Unpaid"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    ]

    # Keep booking/payment history from being deleted accidentally.
    # Không cho xóa booking nếu đã có lịch sử thanh toán.
    booking = models.ForeignKey(
        Booking,
        on_delete=models.PROTECT,
        related_name="payments",
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD,
        default="cash",
    )

    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default="unpaid",
    )

    payment_date = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"Payment {self.amount} - "
            f"{self.status}"
        )


class OnlineCheckOut(models.Model):
    """
    Store checkout history for CustomerBooking.
    Lưu lịch sử checkout cho booking từ Customer Portal.
    """

    # Each online booking can only be checked out once.
    # Mỗi online booking chỉ được checkout một lần.
    booking = models.OneToOneField(
        CustomerBooking,
        on_delete=models.PROTECT,
        related_name="online_checkout",
    )

    check_out_time = models.DateTimeField(
        auto_now_add=True
    )

    # Snapshot the final amount at checkout time.
    # Chụp lại số tiền cuối cùng tại thời điểm checkout.
    final_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    # Store the staff member who performed checkout.
    # Lưu nhân viên thực hiện checkout.
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="online_checkouts",
    )

    def __str__(self):
        return (
            f"Online Checkout: "
            f"{self.booking.full_name} - "
            f"{self.booking.room}"
        )


class OnlinePayment(models.Model):
    """
    Store payment history for CustomerBooking.
    Lưu lịch sử thanh toán cho booking từ Customer Portal.
    """

    PAYMENT_METHOD = Payment.PAYMENT_METHOD
    PAYMENT_STATUS = Payment.PAYMENT_STATUS

    booking = models.ForeignKey(
        CustomerBooking,
        on_delete=models.PROTECT,
        related_name="online_payments",
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD,
        default="cash",
    )

    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default="unpaid",
    )

    payment_date = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"Online Payment {self.amount} - "
            f"{self.status}"
        )