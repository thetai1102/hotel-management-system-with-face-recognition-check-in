from django.conf import settings
from django.db import models

from bookings.models import Booking
from customer_portal.models import CustomerBooking
from customers.models import Customer


CHECKIN_METHOD = [
    (
        "face_verification",
        "Face Verification",
    ),
    (
        "self_kiosk",
        "Self Kiosk",
    ),
    (
        "receptionist_manual",
        "Receptionist Manual",
    ),
]


class CheckIn(models.Model):
    # Staff booking linked to this check-in record.
    # Booking staff được liên kết với bản ghi check-in này.
    booking = models.OneToOneField(
        Booking,
        on_delete=models.PROTECT,
    )

    # Keep customer history even when a delete is attempted.
    # Giữ lịch sử customer, không cho xóa nếu đã có check-in.
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
    )

    method = models.CharField(
        max_length=30,
        choices=CHECKIN_METHOD,
        default="face_verification",
    )

    check_in_time = models.DateTimeField(
        auto_now_add=True
    )

    face_verified = models.BooleanField(
        default=False
    )

    manual_verified = models.BooleanField(
        default=False
    )

    # Store the image that was actually used at check-in.
    # Lưu ảnh thực tế được sử dụng khi check-in.
    verified_image = models.ImageField(
        upload_to="checkin_faces/",
        blank=True,
        null=True,
    )

    # Store the staff member who performed the check-in.
    # Lưu nhân viên thực hiện check-in.
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    def __str__(self):
        return (
            f"Check-in: "
            f"{self.customer.full_name} - "
            f"{self.method}"
        )


class OnlineCheckIn(models.Model):
    """
    Store face check-in history for CustomerBooking.
    Lưu lịch sử Face Check-in cho booking từ customer portal.
    """

    # Each online booking can be checked in only once.
    # Mỗi online booking chỉ có một bản ghi check-in.
    booking = models.OneToOneField(
        CustomerBooking,
        on_delete=models.PROTECT,
        related_name="online_checkin_record",
    )

    method = models.CharField(
        max_length=30,
        choices=CHECKIN_METHOD,
        default="face_verification",
    )

    check_in_time = models.DateTimeField(
        auto_now_add=True
    )

    face_verified = models.BooleanField(
        default=False
    )

    # Store the verified face image for audit history.
    # Lưu ảnh khuôn mặt đã xác minh để phục vụ lịch sử kiểm tra.
    verified_image = models.ImageField(
        upload_to="online_checkin_faces/",
        blank=True,
        null=True,
    )

    # Store the staff member who performed verification.
    # Lưu nhân viên đã thực hiện xác minh.
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    def __str__(self):
        return (
            f"Online Check-in: "
            f"{self.booking.full_name} - "
            f"{self.booking.room}"
        )