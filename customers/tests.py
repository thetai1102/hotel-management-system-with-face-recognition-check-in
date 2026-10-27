from datetime import timedelta
from decimal import Decimal

from django.db import (
    IntegrityError,
    transaction,
)
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from bookings.models import Booking
from rooms.models import (
    Room,
    RoomType,
)

from .forms import CustomerForm
from .models import Customer


# ============================================================
# BASE CUSTOMER TEST DATA
# DỮ LIỆU CƠ SỞ CHO TEST CUSTOMER
# ============================================================

class CustomerBaseTestCase(TestCase):

    def setUp(self):
        """
        Create reusable customer and room data.
        Tạo dữ liệu customer và room dùng lại cho test.
        """

        self.customer = (
            Customer.objects.create(
                full_name="Existing Customer",
                email="existing@example.com",
                phone="+48111111111",
                id_card_number="PASS-001",
                address="Rzeszów, Poland",
            )
        )

        self.room_type = (
            RoomType.objects.create(
                name="Customer Test Room",
                description="Room type for customer tests.",
                price_per_night=Decimal("100.00"),
                capacity=2,
            )
        )

        self.room = (
            Room.objects.create(
                room_number="CU-101",
                room_type=self.room_type,
                floor=1,
                status="available",
            )
        )


# ============================================================
# CUSTOMER MODEL TESTS
# TEST CUSTOMER MODEL
# ============================================================

class CustomerModelTests(
    CustomerBaseTestCase
):

    def test_id_card_number_is_unique_at_database_level(
        self,
    ):
        """
        Exact duplicate identity numbers must fail at database level.
        Số giấy tờ trùng chính xác phải bị chặn ở tầng database.
        """

        with self.assertRaises(
            IntegrityError
        ):
            # Use a nested transaction so the outer test transaction
            # remains usable after the expected database error.
            # Dùng transaction lồng để transaction chính của test
            # vẫn sử dụng được sau lỗi database dự kiến.
            with transaction.atomic():
                Customer.objects.create(
                    full_name="Duplicate Customer",
                    email="duplicate@example.com",
                    phone="+48222222222",
                    id_card_number="PASS-001",
                )

        self.assertEqual(
            Customer.objects.filter(
                id_card_number="PASS-001"
            ).count(),
            1,
        )

    def test_selfie_is_preferred_reference_face(
        self,
    ):
        """
        Selfie must be preferred over the legacy face image.
        Selfie phải được ưu tiên hơn ảnh face_image legacy.
        """

        self.customer.face_image = (
            "customer_faces/legacy-face.jpg"
        )

        self.customer.selfie_image = (
            "customer_selfies/current-selfie.jpg"
        )

        self.customer.save(
            update_fields=[
                "face_image",
                "selfie_image",
            ]
        )

        reference_face = (
            self.customer.get_reference_face()
        )

        self.assertIsNotNone(
            reference_face
        )

        self.assertEqual(
            reference_face.name,
            "customer_selfies/current-selfie.jpg",
        )

    def test_legacy_face_image_is_used_as_fallback(
        self,
    ):
        """
        Legacy face_image must remain usable when no selfie exists.
        face_image legacy vẫn phải dùng được khi chưa có selfie.
        """

        self.customer.face_image = (
            "customer_faces/legacy-face.jpg"
        )

        self.customer.selfie_image = None

        self.customer.save(
            update_fields=[
                "face_image",
                "selfie_image",
            ]
        )

        reference_face = (
            self.customer.get_reference_face()
        )

        self.assertIsNotNone(
            reference_face
        )

        self.assertEqual(
            reference_face.name,
            "customer_faces/legacy-face.jpg",
        )

    def test_reference_face_is_empty_when_no_face_exists(
        self,
    ):
        """
        Customer without selfie or legacy face must have no reference face.
        Customer không có selfie hoặc face legacy thì không có ảnh tham chiếu.
        """

        self.customer.face_image = None
        self.customer.selfie_image = None

        self.customer.save(
            update_fields=[
                "face_image",
                "selfie_image",
            ]
        )

        self.assertFalse(
            self.customer.get_reference_face()
        )


# ============================================================
# CUSTOMER FORM TESTS
# TEST CUSTOMER FORM
# ============================================================

class CustomerFormTests(
    CustomerBaseTestCase
):

    def test_form_rejects_case_insensitive_duplicate_id(
        self,
    ):
        """
        Staff form must reject identity numbers regardless of letter case.
        Form staff phải chặn số giấy tờ trùng dù khác chữ hoa/thường.
        """

        form = CustomerForm(
            data={
                "full_name": "Another Customer",
                "email": "another@example.com",
                "phone": "+48333333333",
                "id_card_number": "pass-001",
                "address": "Rzeszów, Poland",
            }
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "id_card_number",
            form.errors,
        )

    def test_form_normalizes_identity_number_to_uppercase(
        self,
    ):
        """
        New identity numbers must be normalized consistently.
        Số giấy tờ mới phải được chuẩn hóa nhất quán.
        """

        form = CustomerForm(
            data={
                "full_name": "New Customer",
                "email": "NEWCUSTOMER@example.com",
                "phone": "+48444444444",
                "id_card_number": "  passport-999  ",
                "address": "Rzeszów, Poland",
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors.as_text(),
        )

        customer = (
            form.save()
        )

        self.assertEqual(
            customer.id_card_number,
            "PASSPORT-999",
        )

        self.assertEqual(
            customer.email,
            "newcustomer@example.com",
        )

        self.assertEqual(
            customer.full_name,
            "New Customer",
        )


# ============================================================
# CUSTOMER HISTORY PROTECTION TESTS
# TEST BẢO VỆ LỊCH SỬ CUSTOMER
# ============================================================

class CustomerHistoryProtectionTests(
    CustomerBaseTestCase
):

    def test_customer_with_booking_history_cannot_be_deleted(
        self,
    ):
        """
        Customer referenced by Booking must be protected from deletion.
        Customer đã được Booking tham chiếu phải được bảo vệ khi xóa.
        """

        today = (
            timezone.localdate()
        )

        booking = (
            Booking.objects.create(
                customer=self.customer,
                room=self.room,
                check_in_date=(
                    today
                    + timedelta(days=10)
                ),
                check_out_date=(
                    today
                    + timedelta(days=12)
                ),
                status=(
                    Booking.STATUS_CONFIRMED
                ),
                source=(
                    Booking.SOURCE_RECEPTIONIST
                ),
            )
        )

        self.assertIsNotNone(
            booking.pk
        )

        with self.assertRaises(
            ProtectedError
        ):
            self.customer.delete()

        self.assertTrue(
            Customer.objects.filter(
                pk=self.customer.pk
            ).exists()
        )

        self.assertTrue(
            Booking.objects.filter(
                pk=booking.pk
            ).exists()
        )

    def test_customer_without_history_can_be_deleted(
        self,
    ):
        """
        Customer without protected history may be deleted normally.
        Customer chưa có lịch sử được bảo vệ có thể xóa bình thường.
        """

        customer = (
            Customer.objects.create(
                full_name="Temporary Customer",
                email="temporary@example.com",
                phone="+48555555555",
                id_card_number="TEMP-001",
            )
        )

        customer_id = (
            customer.pk
        )

        customer.delete()

        self.assertFalse(
            Customer.objects.filter(
                pk=customer_id
            ).exists()
        )