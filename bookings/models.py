import uuid
from datetime import timedelta
from decimal import Decimal

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from customers.models import Customer
from rooms.models import Room


class Booking(models.Model):
    STATUS_PENDING_CONFIRMATION = (
        "pending_confirmation"
    )
    STATUS_CONFIRMED = "confirmed"
    STATUS_CHECKED_IN = "checked_in"
    STATUS_CHECKED_OUT = "checked_out"
    STATUS_CANCELLED = "cancelled"

    BOOKING_STATUS = [
        (
            STATUS_PENDING_CONFIRMATION,
            "Pending Confirmation",
        ),
        (
            STATUS_CONFIRMED,
            "Confirmed",
        ),
        (
            STATUS_CHECKED_IN,
            "Checked In",
        ),
        (
            STATUS_CHECKED_OUT,
            "Checked Out",
        ),
        (
            STATUS_CANCELLED,
            "Cancelled",
        ),
    ]

    SOURCE_ONLINE = "online"
    SOURCE_RECEPTIONIST = "receptionist"

    BOOKING_SOURCE = [
        (
            SOURCE_ONLINE,
            "Legacy Online Booking",
        ),
        (
            SOURCE_RECEPTIONIST,
            "Receptionist",
        ),
    ]

    # These states reserve or currently occupy the room.
    # Các trạng thái này giữ chỗ hoặc đang sử dụng phòng.
    ACTIVE_BOOKING_STATUSES = (
        STATUS_PENDING_CONFIRMATION,
        STATUS_CONFIRMED,
        STATUS_CHECKED_IN,
    )

    customer = models.ForeignKey(
        Customer,

        # Preserve booking history when customer records exist.
        # Bảo vệ lịch sử booking khi đã có dữ liệu customer.
        on_delete=models.PROTECT,

        related_name="bookings",
    )

    room = models.ForeignKey(
        Room,

        # Prevent deletion of rooms with booking history.
        # Không cho xóa phòng đã có lịch sử booking.
        on_delete=models.PROTECT,

        related_name="bookings",
    )

    booking_code = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        null=True,
    )

    # Kept for compatibility with historical legacy bookings.
    # Giữ lại để tương thích với các legacy booking cũ.
    confirmation_token = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
    )

    confirmed_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    check_in_date = models.DateField()

    check_out_date = models.DateField()

    status = models.CharField(
        max_length=30,
        choices=BOOKING_STATUS,
        default=STATUS_PENDING_CONFIRMATION,
    )

    # New Booking records now belong to the staff workflow.
    # Booking mới hiện thuộc workflow staff.
    #
    # SOURCE_ONLINE remains in choices only for historical
    # legacy Booking records already stored in the database.
    # SOURCE_ONLINE chỉ còn để đọc các legacy Booking
    # đã tồn tại trong database.
    source = models.CharField(
        max_length=30,
        choices=BOOKING_SOURCE,
        default=SOURCE_RECEPTIONIST,
    )

    # Store the booking total as historical booking data.
    # Lưu tổng giá như dữ liệu lịch sử của booking.
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    # Staff member who performed manual verification.
    # Nhân viên thực hiện xác minh thủ công.
    manual_verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name=(
            "manual_verified_bookings"
        ),
    )

    manual_verified_at = (
        models.DateTimeField(
            blank=True,
            null=True,
        )
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

    def __str__(self):
        return (
            f"{self.booking_code} | "
            f"{self.customer.full_name} | "
            f"Room {self.room.room_number} | "
            f"{self.get_status_display()}"
        )

    def generate_booking_code(self):
        """
        Generate a human-readable booking code.
        Tạo mã booking dễ đọc.
        """

        return (
            f"BK-"
            f"{uuid.uuid4().hex[:8].upper()}"
        )

    def generate_confirmation_token(self):
        """
        Generate a legacy-compatible confirmation token.
        Tạo confirmation token để tương thích dữ liệu legacy.
        """

        return uuid.uuid4().hex

    @staticmethod
    def get_local_date(datetime_value):
        """
        Convert a datetime to the hotel's local calendar date.
        Chuyển datetime thành ngày địa phương của khách sạn.
        """

        if timezone.is_aware(
            datetime_value
        ):
            return (
                timezone.localtime(
                    datetime_value
                )
                .date()
            )

        return datetime_value.date()

    def clean(self):
        """
        Validate booking dates and room conflicts.
        Kiểm tra ngày booking và xung đột lịch phòng.
        """

        super().clean()

        if (
            not self.check_in_date
            or not self.check_out_date
        ):
            return

        # Check-out must always be after check-in.
        # Check-out luôn phải sau check-in.
        if (
            self.check_out_date
            <= self.check_in_date
        ):
            raise ValidationError(
                {
                    "check_out_date": (
                        "Check-out date must be later "
                        "than check-in date."
                    )
                }
            )

        # Cancelled and Checked Out bookings no longer
        # block room availability.
        # Cancelled và Checked Out không còn giữ phòng.
        if (
            self.status
            not in self.ACTIVE_BOOKING_STATUSES
        ):
            return

        if not self.room_id:
            return

        # ====================================================
        # STAFF BOOKING CONFLICT
        # XUNG ĐỘT BOOKING STAFF
        # ====================================================

        staff_conflict = (
            Booking.objects
            .filter(
                room_id=self.room_id,
                status__in=(
                    self.ACTIVE_BOOKING_STATUSES
                ),
                check_in_date__lt=(
                    self.check_out_date
                ),
                check_out_date__gt=(
                    self.check_in_date
                ),
            )
            .exclude(
                pk=self.pk
            )
            .exists()
        )

        if staff_conflict:
            raise ValidationError(
                {
                    "room": (
                        "This room already has "
                        "another booking during "
                        "the selected period."
                    )
                }
            )

        # ====================================================
        # CUSTOMER PORTAL BOOKING CONFLICT
        # XUNG ĐỘT CUSTOMER PORTAL BOOKING
        # ====================================================

        # Use apps.get_model() to avoid circular imports.
        # Dùng apps.get_model() để tránh circular import.
        CustomerBooking = (
            apps.get_model(
                "customer_portal",
                "CustomerBooking",
            )
        )

        # Fetch active CustomerBooking records for this room
        # and convert their datetime ranges to the same
        # calendar-day representation used by Booking.
        #
        # Lấy CustomerBooking active của phòng rồi chuyển
        # datetime thành cùng cách biểu diễn calendar-day
        # mà Booking đang sử dụng.
        portal_bookings = (
            CustomerBooking.objects
            .filter(
                room_id=self.room_id,
                status__in=(
                    CustomerBooking
                    .ACTIVE_BOOKING_STATUSES
                ),
            )
            .only(
                "check_in_at",
                "check_out_at",
            )
        )

        portal_conflict = False

        for portal_booking in portal_bookings:

            portal_start_date = (
                self.get_local_date(
                    portal_booking.check_in_at
                )
            )

            portal_end_date = (
                self.get_local_date(
                    portal_booking.check_out_at
                )
            )

            # A valid same-day CustomerBooking still occupies
            # one calendar booking day when compared with the
            # date-based Booking model.
            #
            # CustomerBooking hợp lệ trong cùng ngày vẫn
            # chiếm một ngày khi so với Booking dùng DateField.
            if (
                portal_end_date
                <= portal_start_date
            ):
                portal_end_date = (
                    portal_start_date
                    + timedelta(days=1)
                )

            # Standard half-open interval overlap:
            # [start, end)
            #
            # Quy tắc overlap khoảng nửa mở:
            # [start, end)
            if (
                portal_start_date
                < self.check_out_date
                and portal_end_date
                > self.check_in_date
            ):
                portal_conflict = True
                break

        if portal_conflict:
            raise ValidationError(
                {
                    "room": (
                        "This room already has "
                        "an online booking during "
                        "the selected period."
                    )
                }
            )

    def get_number_of_nights(self):
        """
        Return the number of billable nights.
        Trả về số đêm dùng để tính tiền.
        """

        if (
            not self.check_in_date
            or not self.check_out_date
        ):
            return 0

        number_of_nights = (
            self.check_out_date
            - self.check_in_date
        ).days

        # Invalid dates must not silently become one night.
        # Ngày sai không được tự động thành một đêm.
        if number_of_nights <= 0:
            return 0

        return number_of_nights

    def get_room_price_per_night(self):
        """
        Return the current RoomType rate when pricing
        a new or materially edited booking.
        Lấy giá RoomType hiện tại khi tính giá booking mới
        hoặc booking thay đổi thông tin ảnh hưởng đến giá.
        """

        if not self.room_id:
            return Decimal(
                "0.00"
            )

        return Decimal(
            str(
                self.room
                .room_type
                .price_per_night
            )
        )

    def calculate_total_price(self):
        """
        Calculate total booking price.
        Tính tổng tiền booking.
        """

        number_of_nights = (
            self.get_number_of_nights()
        )

        price_per_night = (
            self.get_room_price_per_night()
        )

        return (
            Decimal(
                number_of_nights
            )
            * price_per_night
        )

    def pricing_fields_changed(self):
        """
        Check whether room or stay dates changed.
        Kiểm tra phòng hoặc ngày lưu trú có thay đổi.
        """

        # A new booking always needs initial pricing.
        # Booking mới luôn cần tính giá ban đầu.
        if (
            self._state.adding
            or not self.pk
        ):
            return True

        previous_booking = (
            Booking.objects
            .filter(
                pk=self.pk
            )
            .values(
                "room_id",
                "check_in_date",
                "check_out_date",
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
                "check_in_date"
            ]
            != self.check_in_date

            or previous_booking[
                "check_out_date"
            ]
            != self.check_out_date
        )

    def confirm_booking(self):
        """
        Confirm a pending historical/staff Booking.
        Xác nhận Booking pending lịch sử/staff.
        """

        if (
            self.status
            != self.STATUS_PENDING_CONFIRMATION
        ):
            return False

        self.status = (
            self.STATUS_CONFIRMED
        )

        self.confirmed_at = (
            timezone.now()
        )

        self.save(
            update_fields=[
                "status",
                "confirmed_at",
            ]
        )

        return True

    def save(
        self,
        *args,
        **kwargs,
    ):
        """
        Save Booking without changing Room.status automatically.
        Lưu Booking nhưng không tự động thay đổi Room.status.
        """

        # Generate identifiers when necessary.
        # Tạo mã và token khi chưa tồn tại.
        generated_fields = []

        if not self.booking_code:
            self.booking_code = (
                self.generate_booking_code()
            )

            generated_fields.append(
                "booking_code"
            )

        # Keep generating the legacy-compatible token because
        # the field remains part of historical Booking data.
        # Tiếp tục tạo token tương thích legacy vì field vẫn
        # còn là một phần dữ liệu Booking lịch sử.
        if not self.confirmation_token:
            self.confirmation_token = (
                self.generate_confirmation_token()
            )

            generated_fields.append(
                "confirmation_token"
            )

        # Run model-level business validation.
        # Chạy validation nghiệp vụ ở tầng model.
        self.clean()

        # Recalculate only when a booking is created or
        # room/stay dates actually change.
        # Chỉ tính lại khi tạo booking hoặc phòng/ngày
        # lưu trú thực sự thay đổi.
        should_recalculate_price = (
            self.pricing_fields_changed()
        )

        if should_recalculate_price:
            self.total_price = (
                self.calculate_total_price()
            )

        # Respect update_fields while ensuring generated and
        # recalculated values are persisted.
        # Tôn trọng update_fields nhưng vẫn lưu các giá trị
        # vừa được tạo hoặc tính lại.
        update_fields = (
            kwargs.get(
                "update_fields"
            )
        )

        if update_fields is not None:

            update_fields = set(
                update_fields
            )

            for field_name in generated_fields:
                update_fields.add(
                    field_name
                )

            if should_recalculate_price:
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

        # IMPORTANT:
        # Room.status is intentionally NOT changed here.
        # Current room state is handled by booking/check-in/
        # checkout workflow views instead of model.save().
        #
        # QUAN TRỌNG:
        # Không thay đổi Room.status tại đây.
        # Trạng thái phòng hiện tại được xử lý bởi workflow
        # booking/check-in/checkout thay vì model.save().