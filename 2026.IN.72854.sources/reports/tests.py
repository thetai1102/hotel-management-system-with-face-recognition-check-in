from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import (
    RequestFactory,
    TestCase,
)
from django.utils import timezone

from bookings.models import Booking
from checkin.models import (
    CheckIn,
    OnlineCheckIn,
)
from checkout.models import (
    CheckOut,
    OnlineCheckOut,
    OnlinePayment,
    Payment,
)
from customer_portal.models import (
    CustomerBooking,
    CustomerProfile,
)
from customers.models import Customer
from rooms.models import (
    Room,
    RoomType,
)

from .views import reports_dashboard


# ============================================================
# BASE REPORT TEST DATA
# DỮ LIỆU CƠ SỞ CHO TEST REPORT
# ============================================================

class ReportsBaseTestCase(TestCase):

    def setUp(self):
        """
        Create reusable users, customers and rooms.
        Tạo dữ liệu user, customer và room dùng lại cho test.
        """

        self.factory = (
            RequestFactory()
        )

        self.User = (
            get_user_model()
        )

        self.admin_group = (
            Group.objects.create(
                name="Admin"
            )
        )

        self.admin_user = (
            self.User.objects.create_user(
                username="reports-admin",
                email="reports-admin@example.com",
                password="StrongPass!2026",
            )
        )

        self.admin_user.groups.add(
            self.admin_group
        )

        self.room_type = (
            RoomType.objects.create(
                name="Reports Test Room",
                description="Room type for report tests.",
                price_per_night=Decimal("100.00"),
                capacity=2,
            )
        )

        self.staff_customer = (
            Customer.objects.create(
                full_name="Reports Staff Guest",
                email="reports-staff@example.com",
                phone="+48111110001",
                id_card_number="REPORT-STAFF-001",
            )
        )

        self.portal_user = (
            self.User.objects.create_user(
                username="reports-portal@example.com",
                email="reports-portal@example.com",
                password="StrongPass!2026",
            )
        )

        self.portal_profile = (
            CustomerProfile.objects.create(
                user=self.portal_user,
                full_name="Reports Portal Guest",
                phone="+48222220001",
            )
        )

        self.room_counter = 400

        # Use valid payment choices from the model itself.
        # Dùng payment choice hợp lệ trực tiếp từ model.
        self.staff_payment_method = (
            Payment.PAYMENT_METHOD[0][0]
        )

        self.portal_payment_method = (
            OnlinePayment.PAYMENT_METHOD[0][0]
        )

    def create_room(
        self,
        status="available",
    ):
        """
        Create a unique room for one report scenario.
        Tạo phòng riêng cho từng tình huống report.
        """

        self.room_counter += 1

        return Room.objects.create(
            room_number=(
                f"RP-{self.room_counter}"
            ),
            room_type=self.room_type,
            floor=4,
            status=status,
        )

    def create_staff_booking(
        self,
        source=Booking.SOURCE_RECEPTIONIST,
        status=Booking.STATUS_CHECKED_OUT,
        room=None,
    ):
        """
        Create a staff-domain Booking.
        Tạo Booking thuộc domain staff.
        """

        if room is None:
            room = self.create_room()

        today = (
            timezone.localdate()
        )

        return Booking.objects.create(
            customer=self.staff_customer,
            room=room,
            check_in_date=(
                today
                - timedelta(days=2)
            ),
            check_out_date=(
                today
                - timedelta(days=1)
            ),
            status=status,
            source=source,
        )

    def create_portal_booking(
        self,
        status=CustomerBooking.STATUS_CHECKED_OUT,
        room=None,
    ):
        """
        Create a Customer Portal booking.
        Tạo CustomerBooking thuộc Customer Portal.
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
                - timedelta(days=2)
            ),
            check_out_at=(
                now
                - timedelta(days=1)
            ),
            status=status,
        )

    def get_report_context(self):
        """
        Execute the Admin report view and capture its context.
        Chạy report view bằng Admin và lấy context trả về.
        """

        request = (
            self.factory.get(
                "/reports/"
            )
        )

        request.user = (
            self.admin_user
        )

        # Patch render so tests can inspect context without
        # depending on a particular URL configuration.
        #
        # Mock render để test đọc context mà không phụ thuộc
        # vào cấu hình URL cụ thể.
        with patch(
            "reports.views.render"
        ) as mocked_render:

            mocked_render.side_effect = (
                lambda request, template, context: context
            )

            return reports_dashboard(
                request
            )


# ============================================================
# BOOKING KPI TESTS
# TEST KPI BOOKING
# ============================================================

class ReportsBookingStatisticsTests(
    ReportsBaseTestCase
):

    def test_current_booking_total_excludes_legacy_records(
        self,
    ):
        """
        Current booking KPI must exclude legacy public Booking.
        KPI booking hiện tại phải loại public Booking legacy.
        """

        self.create_staff_booking(
            source=(
                Booking.SOURCE_RECEPTIONIST
            )
        )

        self.create_staff_booking(
            source=(
                Booking.SOURCE_ONLINE
            )
        )

        self.create_portal_booking()

        context = (
            self.get_report_context()
        )

        self.assertEqual(
            context[
                "staff_bookings_count"
            ],
            1,
        )

        self.assertEqual(
            context[
                "portal_bookings_count"
            ],
            1,
        )

        self.assertEqual(
            context[
                "legacy_online_bookings_count"
            ],
            1,
        )

        # Current workflow intentionally excludes legacy.
        # Workflow hiện tại chủ động loại legacy.
        self.assertEqual(
            context[
                "total_bookings"
            ],
            2,
        )

        # Historical database total still includes it.
        # Tổng record lịch sử trong database vẫn bao gồm legacy.
        self.assertEqual(
            context[
                "all_booking_records_count"
            ],
            3,
        )


# ============================================================
# CHECK-IN / CHECKOUT KPI TESTS
# TEST KPI CHECK-IN / CHECKOUT
# ============================================================

class ReportsCheckInOutStatisticsTests(
    ReportsBaseTestCase
):

    def test_current_checkin_total_excludes_legacy_checkin(
        self,
    ):
        """
        Current check-in KPI must exclude legacy Booking check-ins.
        KPI check-in hiện tại phải loại check-in của Booking legacy.
        """

        staff_booking = (
            self.create_staff_booking(
                source=(
                    Booking.SOURCE_RECEPTIONIST
                )
            )
        )

        legacy_booking = (
            self.create_staff_booking(
                source=(
                    Booking.SOURCE_ONLINE
                )
            )
        )

        portal_booking = (
            self.create_portal_booking()
        )

        CheckIn.objects.create(
            booking=staff_booking,
            customer=self.staff_customer,
            method="face_verification",
            face_verified=True,
            manual_verified=False,
            staff=self.admin_user,
        )

        CheckIn.objects.create(
            booking=legacy_booking,
            customer=self.staff_customer,
            method="face_verification",
            face_verified=True,
            manual_verified=False,
            staff=self.admin_user,
        )

        OnlineCheckIn.objects.create(
            booking=portal_booking,
            method="face_verification",
            face_verified=True,
            staff=self.admin_user,
        )

        context = (
            self.get_report_context()
        )

        self.assertEqual(
            context[
                "staff_checkins_count"
            ],
            1,
        )

        self.assertEqual(
            context[
                "portal_online_checkins_count"
            ],
            1,
        )

        self.assertEqual(
            context[
                "legacy_online_checkins_count"
            ],
            1,
        )

        self.assertEqual(
            context[
                "total_checkins"
            ],
            2,
        )

        self.assertEqual(
            context[
                "all_checkin_records_count"
            ],
            3,
        )

    def test_current_checkout_total_excludes_legacy_checkout(
        self,
    ):
        """
        Current checkout KPI must exclude legacy Booking checkout.
        KPI checkout hiện tại phải loại checkout của Booking legacy.
        """

        staff_booking = (
            self.create_staff_booking(
                source=(
                    Booking.SOURCE_RECEPTIONIST
                )
            )
        )

        legacy_booking = (
            self.create_staff_booking(
                source=(
                    Booking.SOURCE_ONLINE
                )
            )
        )

        portal_booking = (
            self.create_portal_booking()
        )

        CheckOut.objects.create(
            booking=staff_booking,
            final_amount=Decimal("200.00"),
            staff=self.admin_user,
        )

        CheckOut.objects.create(
            booking=legacy_booking,
            final_amount=Decimal("300.00"),
            staff=self.admin_user,
        )

        OnlineCheckOut.objects.create(
            booking=portal_booking,
            final_amount=Decimal("400.00"),
            staff=self.admin_user,
        )

        context = (
            self.get_report_context()
        )

        self.assertEqual(
            context[
                "staff_checkouts_count"
            ],
            1,
        )

        self.assertEqual(
            context[
                "portal_online_checkouts_count"
            ],
            1,
        )

        self.assertEqual(
            context[
                "legacy_online_checkouts_count"
            ],
            1,
        )

        self.assertEqual(
            context[
                "total_checkouts"
            ],
            2,
        )

        self.assertEqual(
            context[
                "all_checkout_records_count"
            ],
            3,
        )


# ============================================================
# REVENUE TESTS
# TEST DOANH THU
# ============================================================

class ReportsRevenueTests(
    ReportsBaseTestCase
):

    def test_current_revenue_excludes_legacy_and_unpaid_records(
        self,
    ):
        """
        Current revenue must include only paid current-workflow records.
        Revenue hiện tại chỉ được tính payment paid của workflow hiện tại.
        """

        staff_booking = (
            self.create_staff_booking(
                source=(
                    Booking.SOURCE_RECEPTIONIST
                )
            )
        )

        legacy_booking = (
            self.create_staff_booking(
                source=(
                    Booking.SOURCE_ONLINE
                )
            )
        )

        portal_booking = (
            self.create_portal_booking()
        )

        # Current staff revenue.
        # Doanh thu staff hiện tại.
        Payment.objects.create(
            booking=staff_booking,
            amount=Decimal("100.00"),
            payment_method=(
                self.staff_payment_method
            ),
            status="paid",
        )

        # Unpaid current staff record must not count.
        # Payment staff Unpaid không được tính.
        Payment.objects.create(
            booking=staff_booking,
            amount=Decimal("999.00"),
            payment_method=(
                self.staff_payment_method
            ),
            status="unpaid",
        )

        # Historical legacy paid revenue.
        # Doanh thu paid thuộc legacy lịch sử.
        Payment.objects.create(
            booking=legacy_booking,
            amount=Decimal("300.00"),
            payment_method=(
                self.staff_payment_method
            ),
            status="paid",
        )

        # Current Customer Portal revenue.
        # Doanh thu Customer Portal hiện tại.
        OnlinePayment.objects.create(
            booking=portal_booking,
            amount=Decimal("200.00"),
            payment_method=(
                self.portal_payment_method
            ),
            status="paid",
        )

        # Failed portal record must not count.
        # Payment portal Failed không được tính.
        OnlinePayment.objects.create(
            booking=portal_booking,
            amount=Decimal("888.00"),
            payment_method=(
                self.portal_payment_method
            ),
            status="failed",
        )

        context = (
            self.get_report_context()
        )

        self.assertEqual(
            context[
                "staff_revenue"
            ],
            Decimal("100.00"),
        )

        self.assertEqual(
            context[
                "portal_online_revenue"
            ],
            Decimal("200.00"),
        )

        self.assertEqual(
            context[
                "legacy_online_revenue"
            ],
            Decimal("300.00"),
        )

        # Current workflow = staff paid + portal paid.
        # Workflow hiện tại = staff paid + portal paid.
        self.assertEqual(
            context[
                "total_revenue"
            ],
            Decimal("300.00"),
        )

        # Historical aggregate includes current + legacy.
        # Tổng lịch sử bao gồm current + legacy.
        self.assertEqual(
            context[
                "all_recorded_revenue"
            ],
            Decimal("600.00"),
        )

    def test_monthly_revenue_chart_excludes_legacy_payment(
        self,
    ):
        """
        Monthly revenue chart must exclude legacy paid Payment records.
        Biểu đồ monthly revenue phải loại Payment paid thuộc legacy.
        """

        staff_booking = (
            self.create_staff_booking(
                source=(
                    Booking.SOURCE_RECEPTIONIST
                )
            )
        )

        legacy_booking = (
            self.create_staff_booking(
                source=(
                    Booking.SOURCE_ONLINE
                )
            )
        )

        portal_booking = (
            self.create_portal_booking()
        )

        Payment.objects.create(
            booking=staff_booking,
            amount=Decimal("125.00"),
            payment_method=(
                self.staff_payment_method
            ),
            status="paid",
        )

        Payment.objects.create(
            booking=legacy_booking,
            amount=Decimal("900.00"),
            payment_method=(
                self.staff_payment_method
            ),
            status="paid",
        )

        OnlinePayment.objects.create(
            booking=portal_booking,
            amount=Decimal("75.00"),
            payment_method=(
                self.portal_payment_method
            ),
            status="paid",
        )

        context = (
            self.get_report_context()
        )

        current_month = (
            timezone.localtime(
                timezone.now()
            )
            .strftime(
                "%Y-%m"
            )
        )

        self.assertIn(
            current_month,
            context[
                "revenue_labels"
            ],
        )

        month_index = (
            context[
                "revenue_labels"
            ].index(
                current_month
            )
        )

        # 125 staff + 75 portal = 200.
        # 900 legacy must not enter the chart.
        # 125 staff + 75 portal = 200.
        # 900 legacy không được vào biểu đồ.
        self.assertEqual(
            context[
                "revenue_values"
            ][month_index],
            200.0,
        )


# ============================================================
# OCCUPANCY TESTS
# TEST TỶ LỆ OCCUPIED HIỆN TẠI
# ============================================================

class ReportsOccupancyTests(
    ReportsBaseTestCase
):

    def test_occupancy_rate_uses_current_room_status(
        self,
    ):
        """
        Occupancy ratio must use current Occupied Room.status only.
        Tỷ lệ occupancy phải dựa trên Room.status Occupied hiện tại.
        """

        self.create_room(
            status="occupied"
        )

        self.create_room(
            status="available"
        )

        self.create_room(
            status="reserved"
        )

        self.create_room(
            status="maintenance"
        )

        context = (
            self.get_report_context()
        )

        self.assertEqual(
            context[
                "total_rooms"
            ],
            4,
        )

        self.assertEqual(
            context[
                "occupied_rooms"
            ],
            1,
        )

        self.assertEqual(
            context[
                "occupancy_rate"
            ],
            25.0,
        )