from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
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


# ============================================================
# BASE DASHBOARD TEST DATA
# DỮ LIỆU CƠ SỞ CHO TEST DASHBOARD
# ============================================================

class DashboardBaseTestCase(TestCase):

    def setUp(self):
        """
        Create reusable users, groups, customers and rooms.
        Tạo dữ liệu user, group, customer và room dùng lại cho test.
        """

        self.User = (
            get_user_model()
        )

        self.admin_group = (
            Group.objects.create(
                name="Admin"
            )
        )

        self.receptionist_group = (
            Group.objects.create(
                name="Receptionist"
            )
        )

        self.admin_user = (
            self.User.objects.create_user(
                username="dashboard-admin",
                email="dashboard-admin@example.com",
                password="StrongPass!2026",
            )
        )

        self.admin_user.groups.add(
            self.admin_group
        )

        self.receptionist_user = (
            self.User.objects.create_user(
                username="dashboard-receptionist",
                email="dashboard-receptionist@example.com",
                password="StrongPass!2026",
            )
        )

        self.receptionist_user.groups.add(
            self.receptionist_group
        )

        self.room_type = (
            RoomType.objects.create(
                name="Dashboard Test Room",
                description="Room type for dashboard tests.",
                price_per_night=Decimal("120.00"),
                capacity=2,
            )
        )

        self.room_counter = 300

    def create_room(
        self,
        status="available",
    ):
        """
        Create a unique room with the requested operational status.
        Tạo phòng duy nhất với trạng thái vận hành được yêu cầu.
        """

        self.room_counter += 1

        return Room.objects.create(
            room_number=(
                f"DB-{self.room_counter}"
            ),
            room_type=self.room_type,
            floor=3,
            status=status,
        )

    def create_staff_customer(
        self,
        suffix,
        email=None,
        phone=None,
        identity=None,
    ):
        """
        Create a staff-managed Customer.
        Tạo Customer được staff quản lý.
        """

        return Customer.objects.create(
            full_name=(
                f"Staff Customer {suffix}"
            ),
            email=(
                email
                or f"staff-{suffix}@example.com"
            ),
            phone=(
                phone
                or f"+4810000{suffix}"
            ),
            id_card_number=(
                identity
                or f"STAFF-{suffix}"
            ),
        )

    def create_portal_customer(
        self,
        suffix,
        email=None,
        phone=None,
        identity=None,
    ):
        """
        Create a Customer Portal account and profile.
        Tạo tài khoản và profile Customer Portal.
        """

        user = (
            self.User.objects.create_user(
                username=(
                    email
                    or f"portal-{suffix}@example.com"
                ),
                email=(
                    email
                    or f"portal-{suffix}@example.com"
                ),
                password="StrongPass!2026",
            )
        )

        profile = (
            CustomerProfile.objects.create(
                user=user,
                full_name=(
                    f"Portal Customer {suffix}"
                ),
                phone=(
                    phone
                    or f"+4820000{suffix}"
                ),
                identity_number=(
                    identity
                    or f"PORTAL-{suffix}"
                ),
            )
        )

        return user, profile


# ============================================================
# DASHBOARD ACCESS TESTS
# TEST QUYỀN TRUY CẬP DASHBOARD
# ============================================================

class DashboardAccessTests(
    DashboardBaseTestCase
):

    def test_admin_can_access_dashboard(
        self,
    ):
        """
        Admin group members must be able to access Dashboard.
        Thành viên group Admin phải truy cập được Dashboard.
        """

        self.client.force_login(
            self.admin_user
        )

        response = self.client.get(
            reverse(
                "dashboard"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_receptionist_can_access_dashboard(
        self,
    ):
        """
        Receptionist group members must be able to access Dashboard.
        Thành viên group Receptionist phải truy cập được Dashboard.
        """

        self.client.force_login(
            self.receptionist_user
        )

        response = self.client.get(
            reverse(
                "dashboard"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )


# ============================================================
# UNIQUE CUSTOMER TESTS
# TEST ĐẾM CUSTOMER DUY NHẤT
# ============================================================

class DashboardCustomerStatisticsTests(
    DashboardBaseTestCase
):

    def test_same_person_in_two_customer_models_is_counted_once(
        self,
    ):
        """
        Matching identifiers across Customer and CustomerProfile
        must represent one estimated unique person.

        Định danh trùng giữa Customer và CustomerProfile
        phải được tính là một người duy nhất.
        """

        shared_email = (
            "same-person@example.com"
        )

        self.create_staff_customer(
            suffix="001",
            email=shared_email,
            phone="+48111111111",
            identity="SHARED-ID-001",
        )

        self.create_portal_customer(
            suffix="001",
            email=shared_email,
            phone="+48222222222",
            identity="PORTAL-DIFFERENT-ID",
        )

        self.client.force_login(
            self.admin_user
        )

        response = self.client.get(
            reverse(
                "dashboard"
            )
        )

        self.assertEqual(
            response.context[
                "staff_customers_count"
            ],
            1,
        )

        self.assertEqual(
            response.context[
                "online_customers_count"
            ],
            1,
        )

        # The two records share one email and therefore
        # represent one estimated unique customer.
        # Hai record dùng chung email nên được ước tính
        # là cùng một customer.
        self.assertEqual(
            response.context[
                "total_customers"
            ],
            1,
        )

    def test_distinct_people_are_counted_separately(
        self,
    ):
        """
        Unrelated Customer and CustomerProfile records must remain separate.
        Customer và CustomerProfile không liên quan phải được đếm riêng.
        """

        self.create_staff_customer(
            suffix="002",
        )

        self.create_portal_customer(
            suffix="002",
        )

        self.client.force_login(
            self.admin_user
        )

        response = self.client.get(
            reverse(
                "dashboard"
            )
        )

        self.assertEqual(
            response.context[
                "total_customers"
            ],
            2,
        )


# ============================================================
# BOOKING STATISTICS TESTS
# TEST THỐNG KÊ BOOKING
# ============================================================

class DashboardBookingStatisticsTests(
    DashboardBaseTestCase
):

    def setUp(self):
        """
        Extend base setup with reusable booking customers.
        Mở rộng dữ liệu cơ sở với customer dùng cho booking.
        """

        super().setUp()

        self.staff_customer = (
            self.create_staff_customer(
                suffix="010",
            )
        )

        (
            self.portal_user,
            self.portal_profile,
        ) = self.create_portal_customer(
            suffix="010",
        )

    def test_current_booking_total_excludes_legacy_public_booking(
        self,
    ):
        """
        Current workflow total must exclude legacy source='online' Booking.
        Tổng workflow hiện tại phải loại Booking legacy source='online'.
        """

        today = (
            timezone.localdate()
        )

        staff_room = (
            self.create_room()
        )

        legacy_room = (
            self.create_room()
        )

        portal_room = (
            self.create_room()
        )

        Booking.objects.create(
            customer=self.staff_customer,
            room=staff_room,
            check_in_date=(
                today
                + timedelta(days=5)
            ),
            check_out_date=(
                today
                + timedelta(days=7)
            ),
            status=(
                Booking.STATUS_CONFIRMED
            ),
            source=(
                Booking.SOURCE_RECEPTIONIST
            ),
        )

        Booking.objects.create(
            customer=self.staff_customer,
            room=legacy_room,
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
                Booking.SOURCE_ONLINE
            ),
        )

        now = (
            timezone.now()
        )

        CustomerBooking.objects.create(
            customer_user=self.portal_user,
            room=portal_room,
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
                + timedelta(days=20)
            ),
            check_out_at=(
                now
                + timedelta(days=22)
            ),
            status=(
                CustomerBooking.STATUS_PENDING
            ),
        )

        self.client.force_login(
            self.admin_user
        )

        response = self.client.get(
            reverse(
                "dashboard"
            )
        )

        self.assertEqual(
            response.context[
                "staff_bookings_count"
            ],
            1,
        )

        self.assertEqual(
            response.context[
                "portal_bookings_count"
            ],
            1,
        )

        self.assertEqual(
            response.context[
                "legacy_online_bookings_count"
            ],
            1,
        )

        # Current workflow = Receptionist Booking + CustomerBooking.
        # Workflow hiện tại = Receptionist Booking + CustomerBooking.
        self.assertEqual(
            response.context[
                "total_bookings"
            ],
            2,
        )

        # Every stored booking record still includes legacy history.
        # Toàn bộ record booking vẫn bao gồm lịch sử legacy.
        self.assertEqual(
            response.context[
                "all_booking_records_count"
            ],
            3,
        )

    def test_recent_staff_bookings_exclude_legacy_records(
        self,
    ):
        """
        Recent staff list must contain only Receptionist Booking records.
        Danh sách staff gần đây chỉ được chứa Receptionist Booking.
        """

        today = (
            timezone.localdate()
        )

        staff_booking = (
            Booking.objects.create(
                customer=self.staff_customer,
                room=self.create_room(),
                check_in_date=(
                    today
                    + timedelta(days=3)
                ),
                check_out_date=(
                    today
                    + timedelta(days=4)
                ),
                status=(
                    Booking.STATUS_CONFIRMED
                ),
                source=(
                    Booking.SOURCE_RECEPTIONIST
                ),
            )
        )

        legacy_booking = (
            Booking.objects.create(
                customer=self.staff_customer,
                room=self.create_room(),
                check_in_date=(
                    today
                    + timedelta(days=6)
                ),
                check_out_date=(
                    today
                    + timedelta(days=7)
                ),
                status=(
                    Booking.STATUS_CONFIRMED
                ),
                source=(
                    Booking.SOURCE_ONLINE
                ),
            )
        )

        self.client.force_login(
            self.admin_user
        )

        response = self.client.get(
            reverse(
                "dashboard"
            )
        )

        recent_ids = [
            booking.pk
            for booking in response.context[
                "recent_bookings"
            ]
        ]

        self.assertIn(
            staff_booking.pk,
            recent_ids,
        )

        self.assertNotIn(
            legacy_booking.pk,
            recent_ids,
        )


# ============================================================
# ROOM STATISTICS TESTS
# TEST THỐNG KÊ TRẠNG THÁI PHÒNG
# ============================================================

class DashboardRoomStatisticsTests(
    DashboardBaseTestCase
):

    def test_room_operational_status_counts_are_reported(
        self,
    ):
        """
        Dashboard must report each current Room.status separately.
        Dashboard phải thống kê riêng từng Room.status hiện tại.
        """

        self.create_room(
            status="available"
        )

        self.create_room(
            status="reserved"
        )

        self.create_room(
            status="occupied"
        )

        self.create_room(
            status="cleaning"
        )

        self.create_room(
            status="maintenance"
        )

        self.client.force_login(
            self.admin_user
        )

        response = self.client.get(
            reverse(
                "dashboard"
            )
        )

        self.assertEqual(
            response.context[
                "total_rooms"
            ],
            5,
        )

        self.assertEqual(
            response.context[
                "available_rooms"
            ],
            1,
        )

        self.assertEqual(
            response.context[
                "reserved_rooms"
            ],
            1,
        )

        self.assertEqual(
            response.context[
                "occupied_rooms"
            ],
            1,
        )

        self.assertEqual(
            response.context[
                "cleaning_rooms"
            ],
            1,
        )

        self.assertEqual(
            response.context[
                "maintenance_rooms"
            ],
            1,
        )