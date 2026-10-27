from datetime import (
    datetime,
    time,
    timedelta,
)

from django.contrib.auth import (
    authenticate,
    get_user_model,
)
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking
from customers.models import Customer
from rooms.models import (
    Room,
    RoomType,
)

from .models import (
    CustomerBooking,
    CustomerProfile,
)


# ============================================================
# BASE TEST DATA
# DỮ LIỆU CƠ SỞ CHO TEST
# ============================================================

class CustomerPortalBaseTestCase(TestCase):

    def setUp(self):
        """
        Create reusable customer, room and account test data.
        Tạo dữ liệu customer, room và account dùng lại cho test.
        """

        self.User = (
            get_user_model()
        )

        self.room_type = (
            RoomType.objects.create(
                name="Deluxe",
                description="Test room type",
                price_per_night="120.00",
                capacity=2,
            )
        )

        self.room = (
            Room.objects.create(
                room_number="101",
                room_type=self.room_type,
                floor=1,
                status="available",
            )
        )

        self.portal_user = (
            self.User.objects.create_user(
                username="guest@example.com",
                email="guest@example.com",
                password="StrongPass!2026",
            )
        )

        self.profile = (
            CustomerProfile.objects.create(
                user=self.portal_user,
                full_name="Portal Guest",
                phone="+48111111111",

                # File names are sufficient for these logic tests.
                # Tên file là đủ cho các test logic này.
                id_document_image=(
                    "customer_documents/test-id.jpg"
                ),
                selfie_image=(
                    "customer_selfies/test-selfie.jpg"
                ),
            )
        )

        self.staff_customer = (
            Customer.objects.create(
                full_name="Staff Customer",
                email="staffcustomer@example.com",
                phone="+48222222222",
                id_card_number="PASS-001",
            )
        )

    def make_local_datetime(
        self,
        target_date,
        hour,
        minute=0,
    ):
        """
        Create an aware datetime in the project's local timezone.
        Tạo datetime aware theo timezone local của project.
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


# ============================================================
# CUSTOMER REGISTRATION TESTS
# TEST ĐĂNG KÝ CUSTOMER
# ============================================================

class CustomerRegistrationTests(
    CustomerPortalBaseTestCase
):

    def test_customer_registration_creates_user_and_profile(
        self,
    ):
        """
        Registration must create both User and CustomerProfile.
        Đăng ký phải tạo cả User và CustomerProfile.
        """

        response = self.client.post(
            reverse(
                "customer_portal:customer_register"
            ),
            {
                "full_name": "New Guest",
                "email": "newguest@example.com",
                "phone": "+48333333333",
                "password1": "VeryStrongPass!2026",
                "password2": "VeryStrongPass!2026",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "customer_portal:customer_login"
            ),
        )

        user = (
            self.User.objects.get(
                username="newguest@example.com"
            )
        )

        self.assertEqual(
            user.email,
            "newguest@example.com",
        )

        self.assertTrue(
            hasattr(
                user,
                "customer_profile",
            )
        )

        self.assertEqual(
            user.customer_profile.full_name,
            "New Guest",
        )

        self.assertEqual(
            user.customer_profile.phone,
            "+48333333333",
        )

    def test_registration_rejects_duplicate_email(
        self,
    ):
        """
        Registration must reject an email already used by a User.
        Đăng ký phải từ chối email đã được một User sử dụng.
        """

        self.User.objects.create_user(
            username="different-username",
            email="duplicate@example.com",
            password="StrongPass!2026",
        )

        response = self.client.post(
            reverse(
                "customer_portal:customer_register"
            ),
            {
                "full_name": "Duplicate Guest",
                "email": "DUPLICATE@example.com",
                "phone": "+48444444444",
                "password1": "VeryStrongPass!2026",
                "password2": "VeryStrongPass!2026",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "This email is already registered.",
        )

        self.assertFalse(
            self.User.objects.filter(
                username="duplicate@example.com"
            ).exists()
        )


# ============================================================
# CUSTOMER AUTHENTICATION TESTS
# TEST XÁC THỰC CUSTOMER
# ============================================================

class CustomerAuthenticationTests(
    CustomerPortalBaseTestCase
):

    def test_customer_can_authenticate_with_phone(
        self,
    ):
        """
        Customer Portal users must be able to authenticate by phone.
        User Customer Portal phải đăng nhập được bằng phone.
        """

        user = authenticate(
            username=self.profile.phone,
            password="StrongPass!2026",
        )

        self.assertIsNotNone(
            user
        )

        self.assertEqual(
            user.pk,
            self.portal_user.pk,
        )

    def test_staff_user_without_profile_is_not_customer(
        self,
    ):
        """
        A staff-style User without CustomerProfile must not be
        authenticated by the customer phone/email backend.

        User kiểu staff không có CustomerProfile không được
        backend customer xem là tài khoản customer.
        """

        staff_user = (
            self.User.objects.create_user(
                username="staffuser",
                email="staff@example.com",
                password="StrongPass!2026",
            )
        )

        user = authenticate(
            username="staff@example.com",
            password="StrongPass!2026",
        )

        # ModelBackend may authenticate the username only when
        # the supplied identifier matches username, not this email.
        # ModelBackend chỉ có thể xác thực username khi identifier
        # khớp username, không phải email này.
        self.assertIsNone(
            user
        )

        self.assertFalse(
            hasattr(
                staff_user,
                "customer_profile",
            )
        )


# ============================================================
# CROSS-MODEL BOOKING CONFLICT TESTS
# TEST XUNG ĐỘT BOOKING GIỮA HAI MODEL
# ============================================================

class CrossModelBookingConflictTests(
    CustomerPortalBaseTestCase
):

    def test_same_day_portal_booking_conflicts_with_staff_booking(
        self,
    ):
        """
        A same-day CustomerBooking must conflict with an
        overlapping date-based staff Booking.

        CustomerBooking cùng ngày phải conflict với
        Booking staff dạng DateField bị overlap.
        """

        stay_date = (
            timezone.localdate()
            + timedelta(days=10)
        )

        Booking.objects.create(
            customer=self.staff_customer,
            room=self.room,
            check_in_date=stay_date,
            check_out_date=(
                stay_date
                + timedelta(days=1)
            ),
            status=Booking.STATUS_CONFIRMED,
            source=Booking.SOURCE_RECEPTIONIST,
        )

        portal_booking = (
            CustomerBooking(
                customer_user=self.portal_user,
                room=self.room,
                full_name="Portal Guest",
                email="guest@example.com",
                phone="+48111111111",
                check_in_at=(
                    self.make_local_datetime(
                        stay_date,
                        10,
                    )
                ),
                check_out_at=(
                    self.make_local_datetime(
                        stay_date,
                        18,
                    )
                ),
                status=(
                    CustomerBooking.STATUS_PENDING
                ),
            )
        )

        with self.assertRaises(
            ValidationError
        ):
            portal_booking.save()

    def test_staff_booking_conflicts_with_same_day_portal_booking(
        self,
    ):
        """
        A staff Booking must also detect the same-day
        CustomerBooking in the opposite validation direction.

        Booking staff cũng phải phát hiện CustomerBooking
        cùng ngày theo chiều validation ngược lại.
        """

        stay_date = (
            timezone.localdate()
            + timedelta(days=20)
        )

        CustomerBooking.objects.create(
            customer_user=self.portal_user,
            room=self.room,
            full_name="Portal Guest",
            email="guest@example.com",
            phone="+48111111111",
            check_in_at=(
                self.make_local_datetime(
                    stay_date,
                    9,
                )
            ),
            check_out_at=(
                self.make_local_datetime(
                    stay_date,
                    16,
                )
            ),
            status=(
                CustomerBooking.STATUS_CONFIRMED
            ),
        )

        staff_booking = (
            Booking(
                customer=self.staff_customer,
                room=self.room,
                check_in_date=stay_date,
                check_out_date=(
                    stay_date
                    + timedelta(days=1)
                ),
                status=(
                    Booking.STATUS_CONFIRMED
                ),
                source=(
                    Booking.SOURCE_RECEPTIONIST
                ),
            )
        )

        with self.assertRaises(
            ValidationError
        ):
            staff_booking.save()

    def test_non_overlapping_staff_and_portal_bookings_are_allowed(
        self,
    ):
        """
        Non-overlapping stays must remain valid.
        Các khoảng lưu trú không overlap phải vẫn hợp lệ.
        """

        first_date = (
            timezone.localdate()
            + timedelta(days=30)
        )

        second_date = (
            first_date
            + timedelta(days=2)
        )

        Booking.objects.create(
            customer=self.staff_customer,
            room=self.room,
            check_in_date=first_date,
            check_out_date=(
                first_date
                + timedelta(days=1)
            ),
            status=Booking.STATUS_CONFIRMED,
            source=Booking.SOURCE_RECEPTIONIST,
        )

        portal_booking = (
            CustomerBooking.objects.create(
                customer_user=self.portal_user,
                room=self.room,
                full_name="Portal Guest",
                email="guest@example.com",
                phone="+48111111111",
                check_in_at=(
                    self.make_local_datetime(
                        second_date,
                        14,
                    )
                ),
                check_out_at=(
                    self.make_local_datetime(
                        second_date
                        + timedelta(days=1),
                        10,
                    )
                ),
                status=(
                    CustomerBooking.STATUS_PENDING
                ),
            )
        )

        self.assertIsNotNone(
            portal_booking.pk
        )