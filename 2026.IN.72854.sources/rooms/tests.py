from decimal import Decimal

from django.db import (
    IntegrityError,
    transaction,
)
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from bookings.forms import BookingForm

from .forms import RoomForm
from .models import (
    Room,
    RoomType,
)


# ============================================================
# BASE ROOM TEST DATA
# DỮ LIỆU CƠ SỞ CHO TEST ROOM
# ============================================================

class RoomBaseTestCase(TestCase):

    def setUp(self):
        """
        Create a reusable RoomType for room tests.
        Tạo RoomType dùng lại cho các test phòng.
        """

        self.room_type = (
            RoomType.objects.create(
                name="Room Test Type",
                description="Room type used by automated tests.",
                price_per_night=Decimal("120.00"),
                capacity=2,
            )
        )

        self.room_counter = 100

    def create_room(
        self,
        status="available",
    ):
        """
        Create a unique room with the requested status.
        Tạo phòng duy nhất với status được yêu cầu.
        """

        self.room_counter += 1

        return Room.objects.create(
            room_number=(
                f"RT-{self.room_counter}"
            ),
            room_type=self.room_type,
            floor=1,
            status=status,
        )


# ============================================================
# ROOM MODEL TESTS
# TEST ROOM MODEL
# ============================================================

class RoomModelTests(
    RoomBaseTestCase
):

    def test_room_number_must_be_unique(
        self,
    ):
        """
        Two rooms must not share the same room number.
        Hai phòng không được có cùng room number.
        """

        Room.objects.create(
            room_number="UNIQUE-101",
            room_type=self.room_type,
            floor=1,
            status="available",
        )

        # Run the expected database error in a nested transaction
        # so the outer TestCase transaction remains usable.
        # Chạy lỗi database dự kiến trong transaction lồng nhau
        # để transaction chính của TestCase vẫn sử dụng được.
        with self.assertRaises(
            IntegrityError
        ):
            with transaction.atomic():
                Room.objects.create(
                    room_number="UNIQUE-101",
                    room_type=self.room_type,
                    floor=2,
                    status="available",
                )

        self.assertEqual(
            Room.objects.filter(
                room_number="UNIQUE-101"
            ).count(),
            1,
        )

    def test_room_type_cannot_be_deleted_while_rooms_reference_it(
        self,
    ):
        """
        RoomType must be protected when Room records reference it.
        RoomType phải được bảo vệ khi vẫn có Room tham chiếu tới nó.
        """

        self.create_room()

        with self.assertRaises(
            ProtectedError
        ):
            self.room_type.delete()

        self.assertTrue(
            RoomType.objects.filter(
                pk=self.room_type.pk
            ).exists()
        )

    def test_room_status_can_represent_reserved_state(
        self,
    ):
        """
        Room must support the current Reserved operational state.
        Room phải hỗ trợ trạng thái vận hành Reserved hiện tại.
        """

        room = (
            self.create_room(
                status="reserved"
            )
        )

        room.refresh_from_db()

        self.assertEqual(
            room.status,
            "reserved",
        )

    def test_room_status_can_represent_occupied_state(
        self,
    ):
        """
        Room must support the current Occupied operational state.
        Room phải hỗ trợ trạng thái vận hành Occupied hiện tại.
        """

        room = (
            self.create_room(
                status="occupied"
            )
        )

        room.refresh_from_db()

        self.assertEqual(
            room.status,
            "occupied",
        )


# ============================================================
# ROOM FORM STATUS TESTS
# TEST STATUS TRONG ROOM FORM
# ============================================================

class RoomFormStatusTests(
    RoomBaseTestCase
):

    def test_new_room_form_exposes_only_manual_operational_statuses(
        self,
    ):
        """
        New Room form must not allow manual Reserved or Occupied status.
        Form Room mới không được cho chọn Reserved hoặc Occupied thủ công.
        """

        form = (
            RoomForm()
        )

        status_values = [
            value
            for value, label
            in form.fields[
                "status"
            ].choices
        ]

        self.assertIn(
            "available",
            status_values,
        )

        self.assertIn(
            "cleaning",
            status_values,
        )

        self.assertIn(
            "maintenance",
            status_values,
        )

        self.assertNotIn(
            "reserved",
            status_values,
        )

        self.assertNotIn(
            "occupied",
            status_values,
        )

    def test_reserved_room_status_is_locked_in_room_form(
        self,
    ):
        """
        Reserved status must be controlled by booking workflow.
        Status Reserved phải được kiểm soát bởi workflow booking.
        """

        room = (
            self.create_room(
                status="reserved"
            )
        )

        form = RoomForm(
            instance=room
        )

        self.assertTrue(
            form.fields[
                "status"
            ].disabled
        )

    def test_occupied_room_status_is_locked_in_room_form(
        self,
    ):
        """
        Occupied status must be controlled by check-in workflow.
        Status Occupied phải được kiểm soát bởi workflow check-in.
        """

        room = (
            self.create_room(
                status="occupied"
            )
        )

        form = RoomForm(
            instance=room
        )

        self.assertTrue(
            form.fields[
                "status"
            ].disabled
        )

    def test_available_room_status_remains_editable(
        self,
    ):
        """
        Available room may still be managed through RoomForm.
        Phòng Available vẫn có thể được quản lý qua RoomForm.
        """

        room = (
            self.create_room(
                status="available"
            )
        )

        form = RoomForm(
            instance=room
        )

        self.assertFalse(
            form.fields[
                "status"
            ].disabled
        )


# ============================================================
# FUTURE AVAILABILITY TESTS
# TEST AVAILABILITY CHO BOOKING TƯƠNG LAI
# ============================================================

class RoomFutureAvailabilityTests(
    RoomBaseTestCase
):

    def test_reserved_room_is_not_globally_removed_from_booking_form(
        self,
    ):
        """
        Current Reserved status must not automatically mean
        the room is unavailable for every future stay.

        Status Reserved hiện tại không được tự động có nghĩa
        phòng không thể đặt cho mọi khoảng thời gian tương lai.
        """

        room = (
            self.create_room(
                status="reserved"
            )
        )

        form = (
            BookingForm()
        )

        self.assertTrue(
            form.fields[
                "room"
            ].queryset.filter(
                pk=room.pk
            ).exists()
        )

    def test_occupied_room_is_not_globally_removed_from_booking_form(
        self,
    ):
        """
        Current Occupied status must not block all future booking dates.
        Status Occupied hiện tại không được chặn mọi ngày booking tương lai.
        """

        room = (
            self.create_room(
                status="occupied"
            )
        )

        form = (
            BookingForm()
        )

        self.assertTrue(
            form.fields[
                "room"
            ].queryset.filter(
                pk=room.pk
            ).exists()
        )

    def test_cleaning_room_can_still_appear_for_future_booking(
        self,
    ):
        """
        Current Cleaning status does not by itself determine
        future-date availability.

        Status Cleaning hiện tại không tự quyết định
        availability cho ngày tương lai.
        """

        room = (
            self.create_room(
                status="cleaning"
            )
        )

        form = (
            BookingForm()
        )

        self.assertTrue(
            form.fields[
                "room"
            ].queryset.filter(
                pk=room.pk
            ).exists()
        )

    def test_maintenance_room_is_excluded_from_new_booking_form(
        self,
    ):
        """
        Maintenance is explicitly excluded from new booking creation.
        Maintenance được chủ động loại khỏi việc tạo booking mới.
        """

        room = (
            self.create_room(
                status="maintenance"
            )
        )

        form = (
            BookingForm()
        )

        self.assertFalse(
            form.fields[
                "room"
            ].queryset.filter(
                pk=room.pk
            ).exists()
        )