from datetime import timedelta
from decimal import Decimal

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


# ============================================================
# CUSTOMER PROFILE
# HỒ SƠ CUSTOMER
# ============================================================

class CustomerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )

    full_name = models.CharField(
        max_length=150
    )

    phone = models.CharField(
        max_length=30,
        unique=True,
    )

    identity_number = models.CharField(
        max_length=50,
        blank=True,
    )

    address = models.TextField(
        blank=True
    )

    id_document_image = models.ImageField(
        upload_to="customer_documents/",
        blank=True,
        null=True,
    )

    selfie_image = models.ImageField(
        upload_to="customer_selfies/",
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def clean(self):
        """
        Validate and normalize customer profile data.
        Kiểm tra và chuẩn hóa dữ liệu hồ sơ customer.
        """

        super().clean()

        # Normalize text values before validation.
        # Chuẩn hóa dữ liệu text trước khi validation.
        if self.full_name:
            self.full_name = (
                self.full_name.strip()
            )

        if self.phone:
            self.phone = (
                self.phone.strip()
            )

        if self.identity_number:
            self.identity_number = (
                self.identity_number
                .strip()
                .upper()
            )

        # Identity number is optional, but when provided
        # it should belong to only one CustomerProfile.
        # Identity number là tùy chọn, nhưng nếu có thì
        # chỉ nên thuộc về một CustomerProfile.
        if self.identity_number:
            duplicate_identity = (
                CustomerProfile.objects
                .filter(
                    identity_number__iexact=(
                        self.identity_number
                    )
                )
                .exclude(
                    pk=self.pk
                )
                .exists()
            )

            if duplicate_identity:
                raise ValidationError(
                    {
                        "identity_number": (
                            "This identity number is already "
                            "registered to another customer."
                        )
                    }
                )

    def __str__(self):
        return self.full_name


# ============================================================
# CUSTOMER BOOKING
# BOOKING CUSTOMER PORTAL
# ============================================================

class CustomerBooking(models.Model):

    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHECKED_IN = "checked_in"
    STATUS_CHECKED_OUT = "checked_out"

    STATUS_CHOICES = [
        (
            STATUS_PENDING,
            "Pending",
        ),
        (
            STATUS_CONFIRMED,
            "Confirmed",
        ),
        (
            STATUS_CANCELLED,
            "Cancelled",
        ),
        (
            STATUS_CHECKED_IN,
            "Checked in",
        ),
        (
            STATUS_CHECKED_OUT,
            "Checked out",
        ),
    ]

    # These statuses reserve or occupy the room.
    # Các trạng thái này giữ chỗ hoặc đang sử dụng phòng.
    ACTIVE_BOOKING_STATUSES = (
        STATUS_PENDING,
        STATUS_CONFIRMED,
        STATUS_CHECKED_IN,
    )

    customer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,

        # Preserve booking history when a customer account
        # already has booking records.
        # Bảo vệ lịch sử booking khi tài khoản customer
        # đã có bản ghi đặt phòng.
        on_delete=models.PROTECT,

        related_name="customer_bookings",
    )

    room = models.ForeignKey(
        "rooms.Room",
        on_delete=models.PROTECT,
        related_name="customer_portal_bookings",
    )

    # Snapshot customer information at booking time.
    # Lưu snapshot thông tin customer tại thời điểm booking.
    full_name = models.CharField(
        max_length=150
    )

    email = models.EmailField()

    phone = models.CharField(
        max_length=30
    )

    identity_number = models.CharField(
        max_length=50,
        blank=True,
    )

    address = models.TextField(
        blank=True
    )

    check_in_at = models.DateTimeField()

    check_out_at = models.DateTimeField()

    id_document_image = models.ImageField(
        upload_to="booking_documents/",
        blank=True,
        null=True,
    )

    selfie_image = models.ImageField(
        upload_to="booking_selfies/",
        blank=True,
        null=True,
    )

    note = models.TextField(
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    # Store the calculated booking total as a historical value.
    # Lưu tổng tiền booking như một giá trị lịch sử.
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    created_at = models.DateTimeField(
        default=timezone.now
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

    def __str__(self):
        return (
            f"{self.full_name} - "
            f"{self.room} - "
            f"{self.check_in_at}"
        )

    def clean(self):
        """
        Validate stay period and room conflicts.
        Kiểm tra thời gian lưu trú và xung đột phòng.
        """

        super().clean()

        # ====================================================
        # NORMALIZATION
        # CHUẨN HÓA DỮ LIỆU
        # ====================================================

        if self.full_name:
            self.full_name = (
                self.full_name.strip()
            )

        if self.email:
            self.email = (
                self.email
                .strip()
                .lower()
            )

        if self.phone:
            self.phone = (
                self.phone.strip()
            )

        if self.identity_number:
            self.identity_number = (
                self.identity_number
                .strip()
                .upper()
            )

        # Both datetime values are required before
        # stay-period validation can continue.
        # Cần đủ hai datetime trước khi tiếp tục
        # validation khoảng lưu trú.
        if (
            not self.check_in_at
            or not self.check_out_at
        ):
            return

        # Check-out must always occur after check-in.
        # Check-out luôn phải sau check-in.
        if (
            self.check_out_at
            <= self.check_in_at
        ):
            raise ValidationError(
                {
                    "check_out_at": (
                        "Check-out time must be later "
                        "than check-in time."
                    )
                }
            )

        # Cancelled and Checked Out bookings no longer
        # reserve or occupy room availability.
        # Cancelled và Checked Out không còn giữ
        # availability của phòng.
        if (
            self.status
            not in self.ACTIVE_BOOKING_STATUSES
        ):
            return

        if not self.room_id:
            return

        # ====================================================
        # CUSTOMER PORTAL BOOKING CONFLICT
        # XUNG ĐỘT CUSTOMER PORTAL BOOKING
        # ====================================================

        # CustomerBooking uses exact datetimes, therefore
        # normal datetime overlap rules can be used.
        # CustomerBooking dùng datetime chính xác nên có thể
        # dùng trực tiếp quy tắc overlap datetime.
        customer_booking_conflict = (
            CustomerBooking.objects
            .filter(
                room_id=self.room_id,
                status__in=(
                    self.ACTIVE_BOOKING_STATUSES
                ),
                check_in_at__lt=(
                    self.check_out_at
                ),
                check_out_at__gt=(
                    self.check_in_at
                ),
            )
            .exclude(
                pk=self.pk
            )
            .exists()
        )

        if customer_booking_conflict:
            raise ValidationError(
                {
                    "room": (
                        "This room already has another "
                        "online booking during the "
                        "selected period."
                    )
                }
            )

        # ====================================================
        # STAFF BOOKING CONFLICT
        # XUNG ĐỘT STAFF BOOKING
        # ====================================================

        # Use apps.get_model() to avoid circular imports
        # between bookings and customer_portal models.
        # Dùng apps.get_model() để tránh circular import
        # giữa bookings và customer_portal.
        Booking = apps.get_model(
            "bookings",
            "Booking",
        )

        # Staff Booking stores DateField values, while
        # CustomerBooking stores DateTimeField values.
        #
        # Booking staff dùng DateField, còn CustomerBooking
        # dùng DateTimeField.
        portal_start_date = (
            self.check_in_at.date()
        )

        portal_end_date = (
            self.check_out_at.date()
        )

        # A valid stay whose check-in and check-out occur
        # on the same calendar date still counts as one
        # occupied booking day when compared with Booking.
        #
        # Booking hợp lệ check-in/check-out cùng ngày vẫn
        # được tính là một ngày khi so với Booking dạng date.
        if (
            portal_end_date
            <= portal_start_date
        ):
            portal_end_date = (
                portal_start_date
                + timedelta(days=1)
            )

        staff_booking_conflict = (
            Booking.objects
            .filter(
                room_id=self.room_id,
                status__in=(
                    Booking.ACTIVE_BOOKING_STATUSES
                ),
                check_in_date__lt=(
                    portal_end_date
                ),
                check_out_date__gt=(
                    portal_start_date
                ),
            )
            .exists()
        )

        if staff_booking_conflict:
            raise ValidationError(
                {
                    "room": (
                        "This room already has another "
                        "staff booking during the "
                        "selected period."
                    )
                }
            )

    def get_number_of_nights(self):
        """
        Return the billable number of nights.
        Trả về số đêm dùng để tính tiền.
        """

        if (
            not self.check_in_at
            or not self.check_out_at
        ):
            return 0

        # Invalid time ranges must not silently
        # become one billable night.
        # Khoảng thời gian sai không được tự động
        # biến thành một đêm tính tiền.
        if (
            self.check_out_at
            <= self.check_in_at
        ):
            return 0

        difference = (
            self.check_out_at.date()
            - self.check_in_at.date()
        )

        nights = (
            difference.days
        )

        # A valid stay within the same calendar date
        # is charged as one night.
        # Lưu trú hợp lệ trong cùng ngày được tính một đêm.
        if nights < 1:
            return 1

        return nights

    def get_room_price_per_night(self):
        """
        Return the current RoomType rate used for initial
        or materially edited booking pricing.
        Lấy giá RoomType hiện tại khi tạo mới hoặc thay đổi
        thông tin ảnh hưởng đến giá booking.
        """

        if not self.room_id:
            return Decimal("0.00")

        if not self.room.room_type_id:
            return Decimal("0.00")

        return Decimal(
            str(
                self.room.room_type.price_per_night
            )
        )

    def calculate_total_price(self):
        """
        Calculate the booking total.
        Tính tổng tiền booking.
        """

        nights = (
            self.get_number_of_nights()
        )

        price_per_night = (
            self.get_room_price_per_night()
        )

        return (
            price_per_night
            * Decimal(nights)
        )

    def pricing_fields_changed(self):
        """
        Check whether room or stay period changed.
        Kiểm tra phòng hoặc thời gian lưu trú có thay đổi.
        """

        # A new booking always needs initial pricing.
        # Booking mới luôn cần tính giá ban đầu.
        if (
            self._state.adding
            or not self.pk
        ):
            return True

        previous_booking = (
            CustomerBooking.objects
            .filter(
                pk=self.pk
            )
            .values(
                "room_id",
                "check_in_at",
                "check_out_at",
            )
            .first()
        )

        if previous_booking is None:
            return True

        return (
            previous_booking[
                "room_id"
            ]
            != self.room_id

            or previous_booking[
                "check_in_at"
            ]
            != self.check_in_at

            or previous_booking[
                "check_out_at"
            ]
            != self.check_out_at
        )

    def save(
        self,
        *args,
        **kwargs,
    ):
        """
        Save booking while preserving historical total price.
        Lưu booking nhưng bảo toàn tổng giá lịch sử.
        """

        # Run business validation even for direct model saves.
        # Chạy validation nghiệp vụ kể cả khi save trực tiếp.
        self.clean()

        should_recalculate_price = (
            self.pricing_fields_changed()
        )

        # Recalculate only when first created or when room/stay
        # data that affects pricing has changed.
        # Chỉ tính lại khi tạo mới hoặc khi room/thời gian
        # ảnh hưởng đến giá đã thay đổi.
        if should_recalculate_price:

            self.total_price = (
                self.calculate_total_price()
            )

            # Include total_price when update_fields is supplied.
            # Thêm total_price khi save sử dụng update_fields.
            update_fields = (
                kwargs.get(
                    "update_fields"
                )
            )

            if update_fields is not None:

                update_fields = set(
                    update_fields
                )

                update_fields.add(
                    "total_price"
                )

                kwargs[
                    "update_fields"
                ] = update_fields

        super().save(
            *args,
            **kwargs,
        )