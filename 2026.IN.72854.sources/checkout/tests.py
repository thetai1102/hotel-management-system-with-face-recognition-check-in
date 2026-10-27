from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
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
    CheckoutForm,
    OnlineCheckoutForm,
)
from .models import (
    CheckOut,
    OnlineCheckOut,
    OnlinePayment,
    Payment,
)


# ============================================================
# BASE CHECKOUT TEST DATA
# DỮ LIỆU CƠ SỞ CHO TEST CHECKOUT
# ============================================================

class CheckoutBaseTestCase(TestCase):

    def setUp(self):
        """
        Create reusable users, customers and room data.
        Tạo dữ liệu user, customer và room dùng lại cho test.
        """

        self.User = (
            get_user_model()
        )

        self.receptionist_group = (
            Group.objects.create(
                name="Receptionist"
            )
        )

        self.staff_user = (
            self.User.objects.create_user(
                username="checkoutstaff",
                email="checkoutstaff@example.com",
                password="StrongPass!2026",
            )
        )

        self.staff_user.groups.add(
            self.receptionist_group
        )

        # Log in as authorized hotel staff.
        # Đăng nhập bằng tài khoản staff có quyền.
        self.client.force_login(
            self.staff_user
        )

        self.room_type = (
            RoomType.objects.create(
                name="Checkout Test Room",
                description="Room type for checkout tests.",
                price_per_night=Decimal("150.00"),
                capacity=2,
            )
        )

        self.staff_customer = (
            Customer.objects.create(
                full_name="Checkout Staff Guest",
                email="staff-guest@example.com",
                phone="+48111112222",
                id_card_number="CHECKOUT-STAFF-001",
            )
        )

        self.portal_user = (
            self.User.objects.create_user(
                username="checkoutguest@example.com",
                email="checkoutguest@example.com",
                password="StrongPass!2026",
            )
        )

        self.portal_profile = (
            CustomerProfile.objects.create(
                user=self.portal_user,
                full_name="Checkout Portal Guest",
                phone="+48222223333",
            )
        )

        # Use an actual configured payment method instead of
        # hard-coding a method that may later change.
        # Dùng payment method thực tế từ model thay vì
        # hard-code giá trị có thể thay đổi sau này.
        self.staff_payment_method = (
            Payment.PAYMENT_METHOD[0][0]
        )

        self.portal_payment_method = (
            OnlinePayment.PAYMENT_METHOD[0][0]
        )

        self.room_counter = 200

    def create_room(
        self,
        status="occupied",
    ):
        """
        Create a unique room for one checkout scenario.
        Tạo phòng riêng cho từng tình huống checkout.
        """

        self.room_counter += 1

        return Room.objects.create(
            room_number=(
                f"CO-{self.room_counter}"
            ),
            room_type=self.room_type,
            floor=2,
            status=status,
        )

    def create_checked_in_staff_booking(
        self,
        room=None,
    ):
        """
        Create a Checked In staff Booking.
        Tạo Booking staff ở trạng thái Checked In.
        """

        if room is None:
            room = self.create_room()

        today = (
            timezone.localdate()
        )

        return Booking.objects.create(
            customer=self.staff_customer,
            room=room,
            check_in_date=today,
            check_out_date=(
                today
                + timedelta(days=2)
            ),
            status=(
                Booking.STATUS_CHECKED_IN
            ),
            source=(
                Booking.SOURCE_RECEPTIONIST
            ),
        )

    def create_checked_in_portal_booking(
        self,
        room=None,
    ):
        """
        Create a Checked In CustomerBooking.
        Tạo CustomerBooking ở trạng thái Checked In.
        """

        if room is None:
            room = self.create_room()

        now = (
            timezone.now()
        )

        return CustomerBooking.objects.create(
            customer_user=self.portal_user,
            room=room,
            full_name=(
                self.portal_profile.full_name
            ),
            email=(
                self.portal_user.email
            ),
            phone=(
                self.portal_profile.phone
            ),
            check_in_at=(
                now
                - timedelta(hours=2)
            ),
            check_out_at=(
                now
                + timedelta(days=1)
            ),
            status=(
                CustomerBooking.STATUS_CHECKED_IN
            ),
        )


# ============================================================
# CHECKOUT FORM TESTS
# TEST FORM CHECKOUT
# ============================================================

class CheckoutFormTests(
    CheckoutBaseTestCase
):

    def test_staff_checked_in_booking_is_selectable(
        self,
    ):
        """
        Checked In staff Booking must appear in CheckoutForm.
        Booking staff Checked In phải xuất hiện trong CheckoutForm.
        """

        booking = (
            self.create_checked_in_staff_booking()
        )

        form = CheckoutForm()

        self.assertTrue(
            form.fields[
                "booking"
            ].queryset.filter(
                pk=booking.pk
            ).exists()
        )

    def test_checked_out_staff_booking_is_not_selectable(
        self,
    ):
        """
        Checked Out Booking must not enter checkout again.
        Booking Checked Out không được checkout lần nữa.
        """

        booking = (
            self.create_checked_in_staff_booking()
        )

        booking.status = (
            Booking.STATUS_CHECKED_OUT
        )

        booking.save(
            update_fields=[
                "status",
            ]
        )

        form = CheckoutForm()

        self.assertFalse(
            form.fields[
                "booking"
            ].queryset.filter(
                pk=booking.pk
            ).exists()
        )

    def test_staff_booking_with_checkout_record_is_not_selectable(
        self,
    ):
        """
        A Booking with CheckOut history must not be selectable again.
        Booking đã có lịch sử CheckOut không được chọn lại.
        """

        booking = (
            self.create_checked_in_staff_booking()
        )

        CheckOut.objects.create(
            booking=booking,
            final_amount=(
                booking.total_price
            ),
            staff=self.staff_user,
        )

        form = CheckoutForm()

        self.assertFalse(
            form.fields[
                "booking"
            ].queryset.filter(
                pk=booking.pk
            ).exists()
        )

    def test_portal_checked_in_booking_is_selectable(
        self,
    ):
        """
        Checked In CustomerBooking must appear in OnlineCheckoutForm.
        CustomerBooking Checked In phải xuất hiện trong OnlineCheckoutForm.
        """

        booking = (
            self.create_checked_in_portal_booking()
        )

        form = OnlineCheckoutForm()

        self.assertTrue(
            form.fields[
                "booking"
            ].queryset.filter(
                pk=booking.pk
            ).exists()
        )

    def test_portal_booking_with_checkout_record_is_not_selectable(
        self,
    ):
        """
        CustomerBooking with OnlineCheckOut must not be selectable again.
        CustomerBooking đã có OnlineCheckOut không được chọn lại.
        """

        booking = (
            self.create_checked_in_portal_booking()
        )

        OnlineCheckOut.objects.create(
            booking=booking,
            final_amount=(
                booking.total_price
            ),
            staff=self.staff_user,
        )

        form = OnlineCheckoutForm()

        self.assertFalse(
            form.fields[
                "booking"
            ].queryset.filter(
                pk=booking.pk
            ).exists()
        )


# ============================================================
# STAFF CHECKOUT WORKFLOW TESTS
# TEST WORKFLOW CHECKOUT STAFF
# ============================================================

class StaffCheckoutWorkflowTests(
    CheckoutBaseTestCase
):

    def test_paid_payment_completes_staff_checkout(
        self,
    ):
        """
        Paid payment must create CheckOut and mark Booking Checked Out.
        Payment Paid phải tạo CheckOut và chuyển Booking thành Checked Out.
        """

        booking = (
            self.create_checked_in_staff_booking()
        )

        original_total = (
            booking.total_price
        )

        response = self.client.post(
            reverse(
                "checkout_create"
            ),
            {
                "booking": booking.pk,
                "payment_method": (
                    self.staff_payment_method
                ),
                "status": "paid",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        booking.refresh_from_db()

        self.assertEqual(
            booking.status,
            Booking.STATUS_CHECKED_OUT,
        )

        self.assertTrue(
            CheckOut.objects.filter(
                booking=booking
            ).exists()
        )

        payment = (
            Payment.objects.get(
                booking=booking
            )
        )

        self.assertEqual(
            payment.status,
            "paid",
        )

        self.assertEqual(
            payment.amount,
            original_total,
        )

        checkout = (
            CheckOut.objects.get(
                booking=booking
            )
        )

        self.assertEqual(
            checkout.final_amount,
            original_total,
        )

        # Checkout must not change the historical booking price.
        # Checkout không được thay đổi total_price lịch sử.
        self.assertEqual(
            booking.total_price,
            original_total,
        )

    def test_unpaid_payment_does_not_complete_staff_checkout(
        self,
    ):
        """
        Unpaid payment must be recorded but must not complete checkout.
        Payment Unpaid phải được lưu nhưng không được hoàn tất checkout.
        """

        booking = (
            self.create_checked_in_staff_booking()
        )

        response = self.client.post(
            reverse(
                "checkout_create"
            ),
            {
                "booking": booking.pk,
                "payment_method": (
                    self.staff_payment_method
                ),
                "status": "unpaid",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        booking.refresh_from_db()

        self.assertEqual(
            booking.status,
            Booking.STATUS_CHECKED_IN,
        )

        self.assertFalse(
            CheckOut.objects.filter(
                booking=booking
            ).exists()
        )

        self.assertEqual(
            Payment.objects.filter(
                booking=booking,
                status="unpaid",
            ).count(),
            1,
        )

    def test_failed_payment_does_not_complete_staff_checkout(
        self,
    ):
        """
        Failed payment must remain in history without creating CheckOut.
        Payment Failed phải được lưu lịch sử nhưng không tạo CheckOut.
        """

        booking = (
            self.create_checked_in_staff_booking()
        )

        response = self.client.post(
            reverse(
                "checkout_create"
            ),
            {
                "booking": booking.pk,
                "payment_method": (
                    self.staff_payment_method
                ),
                "status": "failed",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        booking.refresh_from_db()

        self.assertEqual(
            booking.status,
            Booking.STATUS_CHECKED_IN,
        )

        self.assertFalse(
            CheckOut.objects.filter(
                booking=booking
            ).exists()
        )

        self.assertEqual(
            Payment.objects.filter(
                booking=booking,
                status="failed",
            ).count(),
            1,
        )

    def test_multiple_failed_payment_attempts_are_preserved(
        self,
    ):
        """
        Every unsuccessful payment attempt must remain in history.
        Mỗi lần payment thất bại phải được giữ lại trong lịch sử.
        """

        booking = (
            self.create_checked_in_staff_booking()
        )

        self.client.post(
            reverse(
                "checkout_create"
            ),
            {
                "booking": booking.pk,
                "payment_method": (
                    self.staff_payment_method
                ),
                "status": "unpaid",
            },
        )

        self.client.post(
            reverse(
                "checkout_create"
            ),
            {
                "booking": booking.pk,
                "payment_method": (
                    self.staff_payment_method
                ),
                "status": "failed",
            },
        )

        booking.refresh_from_db()

        self.assertEqual(
            booking.status,
            Booking.STATUS_CHECKED_IN,
        )

        self.assertEqual(
            Payment.objects.filter(
                booking=booking
            ).count(),
            2,
        )

        self.assertTrue(
            Payment.objects.filter(
                booking=booking,
                status="unpaid",
            ).exists()
        )

        self.assertTrue(
            Payment.objects.filter(
                booking=booking,
                status="failed",
            ).exists()
        )

        self.assertFalse(
            CheckOut.objects.filter(
                booking=booking
            ).exists()
        )


# ============================================================
# CUSTOMER PORTAL CHECKOUT WORKFLOW TESTS
# TEST WORKFLOW CHECKOUT CUSTOMER PORTAL
# ============================================================

class PortalCheckoutWorkflowTests(
    CheckoutBaseTestCase
):

    def test_paid_payment_completes_portal_checkout(
        self,
    ):
        """
        Paid portal payment must create OnlineCheckOut.
        Payment Paid của portal phải tạo OnlineCheckOut.
        """

        booking = (
            self.create_checked_in_portal_booking()
        )

        original_total = (
            booking.total_price
        )

        response = self.client.post(
            reverse(
                "online_checkout"
            ),
            {
                "booking": booking.pk,
                "payment_method": (
                    self.portal_payment_method
                ),
                "status": "paid",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        booking.refresh_from_db()

        self.assertEqual(
            booking.status,
            CustomerBooking.STATUS_CHECKED_OUT,
        )

        self.assertTrue(
            OnlineCheckOut.objects.filter(
                booking=booking
            ).exists()
        )

        payment = (
            OnlinePayment.objects.get(
                booking=booking
            )
        )

        self.assertEqual(
            payment.status,
            "paid",
        )

        self.assertEqual(
            payment.amount,
            original_total,
        )

        online_checkout = (
            OnlineCheckOut.objects.get(
                booking=booking
            )
        )

        self.assertEqual(
            online_checkout.final_amount,
            original_total,
        )

        # Historical booking price must remain unchanged.
        # Giá lịch sử của booking phải được giữ nguyên.
        self.assertEqual(
            booking.total_price,
            original_total,
        )

    def test_unpaid_portal_payment_does_not_checkout(
        self,
    ):
        """
        Unpaid OnlinePayment must not create OnlineCheckOut.
        OnlinePayment Unpaid không được tạo OnlineCheckOut.
        """

        booking = (
            self.create_checked_in_portal_booking()
        )

        response = self.client.post(
            reverse(
                "online_checkout"
            ),
            {
                "booking": booking.pk,
                "payment_method": (
                    self.portal_payment_method
                ),
                "status": "unpaid",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        booking.refresh_from_db()

        self.assertEqual(
            booking.status,
            CustomerBooking.STATUS_CHECKED_IN,
        )

        self.assertFalse(
            OnlineCheckOut.objects.filter(
                booking=booking
            ).exists()
        )

        self.assertEqual(
            OnlinePayment.objects.filter(
                booking=booking,
                status="unpaid",
            ).count(),
            1,
        )

    def test_failed_portal_payment_does_not_checkout(
        self,
    ):
        """
        Failed OnlinePayment must be stored without completing checkout.
        OnlinePayment Failed phải được lưu nhưng không hoàn tất checkout.
        """

        booking = (
            self.create_checked_in_portal_booking()
        )

        response = self.client.post(
            reverse(
                "online_checkout"
            ),
            {
                "booking": booking.pk,
                "payment_method": (
                    self.portal_payment_method
                ),
                "status": "failed",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        booking.refresh_from_db()

        self.assertEqual(
            booking.status,
            CustomerBooking.STATUS_CHECKED_IN,
        )

        self.assertFalse(
            OnlineCheckOut.objects.filter(
                booking=booking
            ).exists()
        )

        self.assertEqual(
            OnlinePayment.objects.filter(
                booking=booking,
                status="failed",
            ).count(),
            1,
        )

    def test_multiple_portal_payment_attempts_are_preserved(
        self,
    ):
        """
        Every unsuccessful portal payment attempt must be preserved.
        Mọi lần payment portal chưa thành công phải được giữ lại.
        """

        booking = (
            self.create_checked_in_portal_booking()
        )

        self.client.post(
            reverse(
                "online_checkout"
            ),
            {
                "booking": booking.pk,
                "payment_method": (
                    self.portal_payment_method
                ),
                "status": "unpaid",
            },
        )

        self.client.post(
            reverse(
                "online_checkout"
            ),
            {
                "booking": booking.pk,
                "payment_method": (
                    self.portal_payment_method
                ),
                "status": "failed",
            },
        )

        booking.refresh_from_db()

        self.assertEqual(
            booking.status,
            CustomerBooking.STATUS_CHECKED_IN,
        )

        self.assertEqual(
            OnlinePayment.objects.filter(
                booking=booking
            ).count(),
            2,
        )

        self.assertFalse(
            OnlineCheckOut.objects.filter(
                booking=booking
            ).exists()
        )


# ============================================================
# DUPLICATE CHECKOUT PROTECTION TESTS
# TEST BẢO VỆ CHECKOUT TRÙNG
# ============================================================

class DuplicateCheckoutProtectionTests(
    CheckoutBaseTestCase
):

    def test_staff_booking_cannot_have_two_checkout_records(
        self,
    ):
        """
        One Booking must have at most one CheckOut record.
        Một Booking chỉ được có tối đa một CheckOut record.
        """

        booking = (
            self.create_checked_in_staff_booking()
        )

        CheckOut.objects.create(
            booking=booking,
            final_amount=(
                booking.total_price
            ),
            staff=self.staff_user,
        )

        # OneToOneField must also protect the database layer.
        # OneToOneField cũng phải bảo vệ ở tầng database.
        with self.assertRaises(
            IntegrityError
        ):
            with transaction.atomic():
                CheckOut.objects.create(
                    booking=booking,
                    final_amount=(
                        booking.total_price
                    ),
                    staff=self.staff_user,
                )

        self.assertEqual(
            CheckOut.objects.filter(
                booking=booking
            ).count(),
            1,
        )

    def test_portal_booking_cannot_have_two_checkout_records(
        self,
    ):
        """
        One CustomerBooking must have at most one OnlineCheckOut.
        Một CustomerBooking chỉ được có tối đa một OnlineCheckOut.
        """

        booking = (
            self.create_checked_in_portal_booking()
        )

        OnlineCheckOut.objects.create(
            booking=booking,
            final_amount=(
                booking.total_price
            ),
            staff=self.staff_user,
        )

        with self.assertRaises(
            IntegrityError
        ):
            with transaction.atomic():
                OnlineCheckOut.objects.create(
                    booking=booking,
                    final_amount=(
                        booking.total_price
                    ),
                    staff=self.staff_user,
                )

        self.assertEqual(
            OnlineCheckOut.objects.filter(
                booking=booking
            ).count(),
            1,
        )