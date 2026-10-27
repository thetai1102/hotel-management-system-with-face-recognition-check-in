from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from customers.models import Customer
from rooms.models import (
    Room,
    RoomType,
)

from .forms import BookingForm
from .models import Booking


# ============================================================
# BASE TEST DATA
# DỮ LIỆU CƠ SỞ CHO TEST
# ============================================================

class BookingBaseTestCase(TestCase):

    def setUp(self):
        """
        Create reusable room and customer data.
        Tạo dữ liệu room và customer dùng lại cho test.
        """

        self.room_type = (
            RoomType.objects.create(
                name="Standard Test",
                description="Test room type",
                price_per_night=Decimal("100.00"),
                capacity=2,
            )
        )

        self.room = (
            Room.objects.create(
                room_number="T101",
                room_type=self.room_type,
                floor=1,
                status="available",
            )
        )

        self.customer = (
            Customer.objects.create(
                full_name="Test Customer",
                email="testcustomer@example.com",
                phone="+48123456789",
                id_card_number="TEST-ID-001",
            )
        )

        self.check_in_date = (
            timezone.localdate()
            + timedelta(days=10)
        )

        self.check_out_date = (
            self.check_in_date
            + timedelta(days=2)
        )

    def create_booking(
        self,
        status=Booking.STATUS_PENDING_CONFIRMATION,
    ):
        """
        Create a reusable staff Booking.
        Tạo Booking staff dùng lại cho các test.
        """

        return Booking.objects.create(
            customer=self.customer,
            room=self.room,
            check_in_date=self.check_in_date,
            check_out_date=self.check_out_date,
            status=status,
            source=Booking.SOURCE_RECEPTIONIST,
        )


# ============================================================
# BOOKING MODEL TESTS
# TEST BOOKING MODEL
# ============================================================

class BookingModelTests(
    BookingBaseTestCase
):

    def test_new_booking_defaults_to_receptionist_source(
        self,
    ):
        """
        New Booking records must default to Receptionist.
        Booking mới phải mặc định thuộc source Receptionist.
        """

        booking = Booking.objects.create(
            customer=self.customer,
            room=self.room,
            check_in_date=self.check_in_date,
            check_out_date=self.check_out_date,
        )

        self.assertEqual(
            booking.source,
            Booking.SOURCE_RECEPTIONIST,
        )

    def test_initial_total_price_is_calculated(
        self,
    ):
        """
        Initial booking price must use room rate and stay length.
        Giá ban đầu phải dựa trên giá phòng và số đêm lưu trú.
        """

        booking = self.create_booking()

        self.assertEqual(
            booking.total_price,
            Decimal("200.00"),
        )

    def test_status_change_preserves_historical_total_price(
        self,
    ):
        """
        Changing only status must not recalculate historical price.
        Chỉ đổi status không được tính lại giá lịch sử.
        """

        booking = self.create_booking()

        original_total = (
            booking.total_price
        )

        # Change the current RoomType price after booking creation.
        # Thay đổi giá RoomType hiện tại sau khi Booking đã được tạo.
        self.room_type.price_per_night = (
            Decimal("999.00")
        )

        self.room_type.save(
            update_fields=[
                "price_per_night",
            ]
        )

        booking.status = (
            Booking.STATUS_CONFIRMED
        )

        booking.save(
            update_fields=[
                "status",
            ]
        )

        booking.refresh_from_db()

        self.assertEqual(
            booking.total_price,
            original_total,
        )

        self.assertEqual(
            booking.total_price,
            Decimal("200.00"),
        )

    def test_stay_date_change_recalculates_total_price(
        self,
    ):
        """
        Material stay-date changes must recalculate price.
        Thay đổi ngày lưu trú phải tính lại tổng giá.
        """

        booking = self.create_booking()

        # Change current room rate before materially editing the stay.
        # Đổi giá phòng hiện tại trước khi chỉnh sửa khoảng lưu trú.
        self.room_type.price_per_night = (
            Decimal("150.00")
        )

        self.room_type.save(
            update_fields=[
                "price_per_night",
            ]
        )

        booking.check_out_date = (
            booking.check_in_date
            + timedelta(days=3)
        )

        booking.save(
            update_fields=[
                "check_out_date",
            ]
        )

        booking.refresh_from_db()

        self.assertEqual(
            booking.total_price,
            Decimal("450.00"),
        )

    def test_confirm_booking_changes_pending_to_confirmed(
        self,
    ):
        """
        confirm_booking() must perform Pending -> Confirmed.
        confirm_booking() phải chuyển Pending -> Confirmed.
        """

        booking = self.create_booking(
            status=(
                Booking.STATUS_PENDING_CONFIRMATION
            )
        )

        original_total = (
            booking.total_price
        )

        result = (
            booking.confirm_booking()
        )

        booking.refresh_from_db()

        self.assertTrue(
            result
        )

        self.assertEqual(
            booking.status,
            Booking.STATUS_CONFIRMED,
        )

        self.assertIsNotNone(
            booking.confirmed_at
        )

        # Confirmation must not change historical price.
        # Xác nhận Booking không được thay đổi giá lịch sử.
        self.assertEqual(
            booking.total_price,
            original_total,
        )

    def test_confirm_booking_rejects_non_pending_booking(
        self,
    ):
        """
        confirm_booking() must reject non-pending states.
        confirm_booking() phải từ chối trạng thái không phải Pending.
        """

        booking = self.create_booking(
            status=(
                Booking.STATUS_CONFIRMED
            )
        )

        result = (
            booking.confirm_booking()
        )

        self.assertFalse(
            result
        )

        booking.refresh_from_db()

        self.assertEqual(
            booking.status,
            Booking.STATUS_CONFIRMED,
        )


# ============================================================
# BOOKING FORM WORKFLOW TESTS
# TEST WORKFLOW BOOKING FORM
# ============================================================

class BookingFormWorkflowTests(
    BookingBaseTestCase
):

    def test_new_booking_form_allows_only_pending_or_confirmed(
        self,
    ):
        """
        New staff Booking form must not expose operational states.
        Form Booking staff mới không được cho chọn trạng thái vận hành.
        """

        form = BookingForm()

        status_values = [
            value
            for value, label
            in form.fields[
                "status"
            ].choices
        ]

        self.assertEqual(
            status_values,
            [
                Booking.STATUS_PENDING_CONFIRMATION,
                Booking.STATUS_CONFIRMED,
            ],
        )

        self.assertNotIn(
            Booking.STATUS_CHECKED_IN,
            status_values,
        )

        self.assertNotIn(
            Booking.STATUS_CHECKED_OUT,
            status_values,
        )

    def test_confirmed_booking_form_does_not_allow_checked_in(
        self,
    ):
        """
        Confirmed Booking cannot become Checked In through BookingForm.
        Booking Confirmed không thể thành Checked In qua BookingForm.
        """

        booking = self.create_booking(
            status=(
                Booking.STATUS_CONFIRMED
            )
        )

        form = BookingForm(
            instance=booking
        )

        status_values = [
            value
            for value, label
            in form.fields[
                "status"
            ].choices
        ]

        self.assertEqual(
            status_values,
            [
                Booking.STATUS_CONFIRMED,
                Booking.STATUS_CANCELLED,
            ],
        )

        self.assertNotIn(
            Booking.STATUS_CHECKED_IN,
            status_values,
        )

    def test_posting_checked_in_to_confirmed_form_is_invalid(
        self,
    ):
        """
        A crafted POST must not bypass the Face Check-in workflow.
        POST giả mạo không được bypass workflow Face Check-in.
        """

        booking = self.create_booking(
            status=(
                Booking.STATUS_CONFIRMED
            )
        )

        form = BookingForm(
            data={
                "customer": self.customer.pk,
                "room": self.room.pk,
                "check_in_date": (
                    booking.check_in_date
                    .isoformat()
                ),
                "check_out_date": (
                    booking.check_out_date
                    .isoformat()
                ),
                "status": (
                    Booking.STATUS_CHECKED_IN
                ),
            },
            instance=booking,
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "status",
            form.errors,
        )

    def test_checked_in_booking_fields_are_disabled(
        self,
    ):
        """
        Checked In Booking must be locked in the generic form.
        Booking Checked In phải bị khóa trong form chỉnh sửa chung.
        """

        booking = self.create_booking(
            status=(
                Booking.STATUS_CHECKED_IN
            )
        )

        form = BookingForm(
            instance=booking
        )

        locked_fields = [
            "customer",
            "room",
            "check_in_date",
            "check_out_date",
            "status",
        ]

        for field_name in locked_fields:
            self.assertTrue(
                form.fields[
                    field_name
                ].disabled
            )

    def test_checked_out_booking_fields_are_disabled(
        self,
    ):
        """
        Checked Out Booking must be historical and read-only here.
        Booking Checked Out phải là dữ liệu lịch sử và chỉ đọc tại đây.
        """

        booking = self.create_booking(
            status=(
                Booking.STATUS_CHECKED_OUT
            )
        )

        form = BookingForm(
            instance=booking
        )

        for field_name in [
            "customer",
            "room",
            "check_in_date",
            "check_out_date",
            "status",
        ]:
            self.assertTrue(
                form.fields[
                    field_name
                ].disabled
            )

    def test_cancelled_booking_fields_are_disabled(
        self,
    ):
        """
        Cancelled Booking must also be locked in the generic form.
        Booking Cancelled cũng phải bị khóa trong form chỉnh sửa chung.
        """

        booking = self.create_booking(
            status=(
                Booking.STATUS_CANCELLED
            )
        )

        form = BookingForm(
            instance=booking
        )

        for field_name in [
            "customer",
            "room",
            "check_in_date",
            "check_out_date",
            "status",
        ]:
            self.assertTrue(
                form.fields[
                    field_name
                ].disabled
            )