from datetime import (
    datetime,
    time,
    timedelta,
)

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from bookings.models import Booking
from customer_portal.models import (
    CustomerBooking,
    CustomerProfile,
)
from customers.models import Customer
from rooms.models import (
    Room,
    RoomType,
)

from .forms import (
    FaceCheckInForm,
    OnlineFaceCheckInForm,
)


# ============================================================
# BASE TEST DATA
# DỮ LIỆU CƠ SỞ CHO TEST
# ============================================================

class FaceCheckInBaseTestCase(TestCase):

    def setUp(self):
        """
        Create reusable customer, room and account data.
        Tạo dữ liệu customer, room và account dùng lại cho test.
        """

        self.User = (
            get_user_model()
        )

        self.room_type = (
            RoomType.objects.create(
                name="Check-in Test Room",
                description="Room type used by check-in tests.",
                price_per_night="120.00",
                capacity=2,
            )
        )

        self.staff_customer = (
            Customer.objects.create(
                full_name="Staff Booking Guest",
                email="staffguest@example.com",
                phone="+48111110000",
                id_card_number="CHECKIN-STAFF-001",
                address="Rzeszów, Poland",
            )
        )

        self.portal_user = (
            self.User.objects.create_user(
                username="portal-checkin@example.com",
                email="portal-checkin@example.com",
                password="StrongPass!2026",
            )
        )

        self.portal_profile = (
            CustomerProfile.objects.create(
                user=self.portal_user,
                full_name="Portal Booking Guest",
                phone="+48222220000",
            )
        )

        self.room_counter = 100

    def create_room(
        self,
        status="available",
    ):
        """
        Create a unique room for one test scenario.
        Tạo một phòng riêng cho từng tình huống test.
        """

        self.room_counter += 1

        return Room.objects.create(
            room_number=(
                f"CI-{self.room_counter}"
            ),
            room_type=self.room_type,
            floor=1,
            status=status,
        )

    def make_local_datetime(
        self,
        target_date,
        hour,
        minute=0,
    ):
        """
        Create a timezone-aware hotel-local datetime.
        Tạo datetime aware theo timezone local của khách sạn.
        """

        naive_datetime = (
            datetime.combine(
                target_date,
                time(
                    hour=hour,
                    minute=minute,
                ),
            )
        )

        return timezone.make_aware(
            naive_datetime,
            timezone.get_current_timezone(),
        )

    def create_staff_booking(
        self,
        room,
        check_in_date,
        check_out_date,
        status=Booking.STATUS_CONFIRMED,
    ):
        """
        Create a staff Booking for check-in tests.
        Tạo Booking staff dùng cho test check-in.
        """

        return Booking.objects.create(
            customer=self.staff_customer,
            room=room,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            status=status,
            source=Booking.SOURCE_RECEPTIONIST,
        )

    def create_portal_booking(
        self,
        room,
        check_in_at,
        check_out_at,
        status=CustomerBooking.STATUS_CONFIRMED,
    ):
        """
        Create a Customer Portal booking for check-in tests.
        Tạo CustomerBooking dùng cho test check-in.
        """

        return CustomerBooking.objects.create(
            customer_user=self.portal_user,
            room=room,
            full_name=self.portal_profile.full_name,
            email=self.portal_user.email,
            phone=self.portal_profile.phone,
            check_in_at=check_in_at,
            check_out_at=check_out_at,
            status=status,
        )


# ============================================================
# STAFF FACE CHECK-IN FORM TESTS
# TEST FORM FACE CHECK-IN BOOKING STAFF
# ============================================================

class StaffFaceCheckInFormTests(
    FaceCheckInBaseTestCase
):

    def test_confirmed_booking_for_today_is_selectable(
        self,
    ):
        """
        A Confirmed Booking whose stay includes today must be selectable.
        Booking Confirmed có stay bao gồm hôm nay phải được phép chọn.
        """

        today = (
            timezone.localdate()
        )

        room = (
            self.create_room()
        )

        booking = (
            self.create_staff_booking(
                room=room,
                check_in_date=today,
                check_out_date=(
                    today
                    + timedelta(days=1)
                ),
            )
        )

        form = (
            FaceCheckInForm()
        )

        self.assertTrue(
            form.fields[
                "booking"
            ].queryset.filter(
                pk=booking.pk
            ).exists()
        )

    def test_future_booking_is_not_selectable(
        self,
    ):
        """
        A staff Booking must not be checked in before its start date.
        Booking staff không được check-in trước ngày bắt đầu.
        """

        today = (
            timezone.localdate()
        )

        room = (
            self.create_room()
        )

        booking = (
            self.create_staff_booking(
                room=room,
                check_in_date=(
                    today
                    + timedelta(days=1)
                ),
                check_out_date=(
                    today
                    + timedelta(days=2)
                ),
            )
        )

        form = (
            FaceCheckInForm()
        )

        self.assertFalse(
            form.fields[
                "booking"
            ].queryset.filter(
                pk=booking.pk
            ).exists()
        )

    def test_expired_booking_is_not_selectable(
        self,
    ):
        """
        A Booking must not be selectable on or after its checkout date.
        Booking không được chọn khi đã tới hoặc qua ngày checkout.
        """

        today = (
            timezone.localdate()
        )

        room = (
            self.create_room()
        )

        booking = (
            self.create_staff_booking(
                room=room,
                check_in_date=(
                    today
                    - timedelta(days=2)
                ),
                check_out_date=today,
            )
        )

        form = (
            FaceCheckInForm()
        )

        self.assertFalse(
            form.fields[
                "booking"
            ].queryset.filter(
                pk=booking.pk
            ).exists()
        )

    def test_checked_in_booking_is_not_selectable(
        self,
    ):
        """
        A Checked In Booking must not re-enter Face Check-in.
        Booking Checked In không được vào lại Face Check-in.
        """

        today = (
            timezone.localdate()
        )

        room = (
            self.create_room()
        )

        booking = (
            self.create_staff_booking(
                room=room,
                check_in_date=today,
                check_out_date=(
                    today
                    + timedelta(days=1)
                ),
                status=(
                    Booking.STATUS_CHECKED_IN
                ),
            )
        )

        form = (
            FaceCheckInForm()
        )

        self.assertFalse(
            form.fields[
                "booking"
            ].queryset.filter(
                pk=booking.pk
            ).exists()
        )

    def test_maintenance_room_booking_is_not_selectable(
        self,
    ):
        """
        A room under Maintenance must block Face Check-in.
        Phòng Maintenance phải chặn Face Check-in.
        """

        today = (
            timezone.localdate()
        )

        room = (
            self.create_room(
                status="maintenance"
            )
        )

        booking = (
            self.create_staff_booking(
                room=room,
                check_in_date=today,
                check_out_date=(
                    today
                    + timedelta(days=1)
                ),
            )
        )

        form = (
            FaceCheckInForm()
        )

        self.assertFalse(
            form.fields[
                "booking"
            ].queryset.filter(
                pk=booking.pk
            ).exists()
        )

    def test_cleaning_room_booking_is_not_selectable(
        self,
    ):
        """
        A room under Cleaning must block Face Check-in.
        Phòng Cleaning phải chặn Face Check-in.
        """

        today = (
            timezone.localdate()
        )

        room = (
            self.create_room(
                status="cleaning"
            )
        )

        booking = (
            self.create_staff_booking(
                room=room,
                check_in_date=today,
                check_out_date=(
                    today
                    + timedelta(days=1)
                ),
            )
        )

        form = (
            FaceCheckInForm()
        )

        self.assertFalse(
            form.fields[
                "booking"
            ].queryset.filter(
                pk=booking.pk
            ).exists()
        )

    def test_form_accepts_camera_capture_for_valid_booking(
        self,
    ):
        """
        Camera capture data must satisfy the image-source requirement.
        Dữ liệu camera phải đáp ứng yêu cầu nguồn ảnh của form.
        """

        today = (
            timezone.localdate()
        )

        room = (
            self.create_room()
        )

        booking = (
            self.create_staff_booking(
                room=room,
                check_in_date=today,
                check_out_date=(
                    today
                    + timedelta(days=1)
                ),
            )
        )

        form = FaceCheckInForm(
            data={
                "booking": booking.pk,
                "captured_image": (
                    "camera-capture-data"
                ),
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors.as_text(),
        )

    def test_form_requires_face_image_source(
        self,
    ):
        """
        Face Check-in must require upload or camera capture.
        Face Check-in phải yêu cầu ảnh upload hoặc camera.
        """

        today = (
            timezone.localdate()
        )

        room = (
            self.create_room()
        )

        booking = (
            self.create_staff_booking(
                room=room,
                check_in_date=today,
                check_out_date=(
                    today
                    + timedelta(days=1)
                ),
            )
        )

        form = FaceCheckInForm(
            data={
                "booking": booking.pk,
                "captured_image": "",
            }
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "Please upload an image or capture",
            form.non_field_errors()[0],
        )


# ============================================================
# CUSTOMER PORTAL FACE CHECK-IN FORM TESTS
# TEST FORM FACE CHECK-IN CUSTOMER PORTAL
# ============================================================

class PortalFaceCheckInFormTests(
    FaceCheckInBaseTestCase
):

    def test_confirmed_booking_inside_datetime_window_is_selectable(
        self,
    ):
        """
        Confirmed CustomerBooking inside its exact stay window
        must be selectable.

        CustomerBooking Confirmed đang nằm trong đúng time window
        phải được phép chọn.
        """

        now = (
            timezone.now()
        )

        room = (
            self.create_room()
        )

        booking = (
            self.create_portal_booking(
                room=room,
                check_in_at=(
                    now
                    - timedelta(hours=1)
                ),
                check_out_at=(
                    now
                    + timedelta(hours=2)
                ),
            )
        )

        form = (
            OnlineFaceCheckInForm()
        )

        self.assertTrue(
            form.fields[
                "booking"
            ].queryset.filter(
                pk=booking.pk
            ).exists()
        )

    def test_portal_booking_before_checkin_time_is_not_selectable(
        self,
    ):
        """
        Customer Portal check-in must not occur before check_in_at.
        Customer Portal không được check-in trước check_in_at.
        """

        now = (
            timezone.now()
        )

        room = (
            self.create_room()
        )

        booking = (
            self.create_portal_booking(
                room=room,
                check_in_at=(
                    now
                    + timedelta(hours=2)
                ),
                check_out_at=(
                    now
                    + timedelta(hours=5)
                ),
            )
        )

        form = (
            OnlineFaceCheckInForm()
        )

        self.assertFalse(
            form.fields[
                "booking"
            ].queryset.filter(
                pk=booking.pk
            ).exists()
        )

    def test_expired_portal_booking_is_not_selectable(
        self,
    ):
        """
        Customer Portal booking must expire at check_out_at.
        CustomerBooking phải hết quyền check-in tại check_out_at.
        """

        now = (
            timezone.now()
        )

        room = (
            self.create_room()
        )

        booking = (
            self.create_portal_booking(
                room=room,
                check_in_at=(
                    now
                    - timedelta(hours=5)
                ),
                check_out_at=(
                    now
                    - timedelta(hours=1)
                ),
            )
        )

        form = (
            OnlineFaceCheckInForm()
        )

        self.assertFalse(
            form.fields[
                "booking"
            ].queryset.filter(
                pk=booking.pk
            ).exists()
        )

    def test_checked_in_portal_booking_is_not_selectable(
        self,
    ):
        """
        Checked In CustomerBooking must not re-enter Face Check-in.
        CustomerBooking Checked In không được vào lại Face Check-in.
        """

        now = (
            timezone.now()
        )

        room = (
            self.create_room()
        )

        booking = (
            self.create_portal_booking(
                room=room,
                check_in_at=(
                    now
                    - timedelta(hours=1)
                ),
                check_out_at=(
                    now
                    + timedelta(hours=2)
                ),
                status=(
                    CustomerBooking.STATUS_CHECKED_IN
                ),
            )
        )

        form = (
            OnlineFaceCheckInForm()
        )

        self.assertFalse(
            form.fields[
                "booking"
            ].queryset.filter(
                pk=booking.pk
            ).exists()
        )

    def test_maintenance_room_blocks_portal_face_checkin(
        self,
    ):
        """
        Maintenance room must block Customer Portal Face Check-in.
        Phòng Maintenance phải chặn Face Check-in Customer Portal.
        """

        now = (
            timezone.now()
        )

        room = (
            self.create_room(
                status="maintenance"
            )
        )

        booking = (
            self.create_portal_booking(
                room=room,
                check_in_at=(
                    now
                    - timedelta(hours=1)
                ),
                check_out_at=(
                    now
                    + timedelta(hours=2)
                ),
            )
        )

        form = (
            OnlineFaceCheckInForm()
        )

        self.assertFalse(
            form.fields[
                "booking"
            ].queryset.filter(
                pk=booking.pk
            ).exists()
        )

    def test_cleaning_room_blocks_portal_face_checkin(
        self,
    ):
        """
        Cleaning room must block Customer Portal Face Check-in.
        Phòng Cleaning phải chặn Face Check-in Customer Portal.
        """

        now = (
            timezone.now()
        )

        room = (
            self.create_room(
                status="cleaning"
            )
        )

        booking = (
            self.create_portal_booking(
                room=room,
                check_in_at=(
                    now
                    - timedelta(hours=1)
                ),
                check_out_at=(
                    now
                    + timedelta(hours=2)
                ),
            )
        )

        form = (
            OnlineFaceCheckInForm()
        )

        self.assertFalse(
            form.fields[
                "booking"
            ].queryset.filter(
                pk=booking.pk
            ).exists()
        )

    def test_portal_form_accepts_camera_capture(
        self,
    ):
        """
        Valid CustomerBooking may use camera capture as current image.
        CustomerBooking hợp lệ có thể dùng ảnh hiện tại từ camera.
        """

        now = (
            timezone.now()
        )

        room = (
            self.create_room()
        )

        booking = (
            self.create_portal_booking(
                room=room,
                check_in_at=(
                    now
                    - timedelta(hours=1)
                ),
                check_out_at=(
                    now
                    + timedelta(hours=2)
                ),
            )
        )

        form = OnlineFaceCheckInForm(
            data={
                "booking": booking.pk,
                "captured_image": (
                    "camera-capture-data"
                ),
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors.as_text(),
        )

    def test_portal_form_requires_face_image_source(
        self,
    ):
        """
        Customer Portal Face Check-in requires current face data.
        Face Check-in Customer Portal phải có dữ liệu khuôn mặt hiện tại.
        """

        now = (
            timezone.now()
        )

        room = (
            self.create_room()
        )

        booking = (
            self.create_portal_booking(
                room=room,
                check_in_at=(
                    now
                    - timedelta(hours=1)
                ),
                check_out_at=(
                    now
                    + timedelta(hours=2)
                ),
            )
        )

        form = OnlineFaceCheckInForm(
            data={
                "booking": booking.pk,
                "captured_image": "",
            }
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "Please upload an image or capture",
            form.non_field_errors()[0],
        )