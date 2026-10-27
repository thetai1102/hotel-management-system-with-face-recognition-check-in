from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from rooms.models import (
    Room,
    RoomType,
)


# ============================================================
# BASE PUBLIC SITE TEST DATA
# DỮ LIỆU CƠ SỞ CHO TEST PUBLIC SITE
# ============================================================

class HotelSiteBaseTestCase(TestCase):

    def setUp(self):
        """
        Create reusable room data for public-site tests.
        Tạo dữ liệu phòng dùng lại cho test public site.
        """

        self.room_type = (
            RoomType.objects.create(
                name="Public Test Room",
                description=(
                    "Room type used by public-site tests."
                ),
                price_per_night=Decimal("120.00"),
                capacity=2,
            )
        )

        self.room_counter = 500

    def create_room(
        self,
        status="available",
    ):
        """
        Create a unique room with a current operational status.
        Tạo phòng duy nhất với trạng thái vận hành hiện tại.
        """

        self.room_counter += 1

        return Room.objects.create(
            room_number=(
                f"WEB-{self.room_counter}"
            ),
            room_type=self.room_type,
            floor=5,
            status=status,
        )


# ============================================================
# PUBLIC PAGE ACCESS TESTS
# TEST TRUY CẬP CÁC TRANG PUBLIC
# ============================================================

class PublicPageAccessTests(
    HotelSiteBaseTestCase
):

    def test_home_page_is_public(
        self,
    ):
        """
        Home page must be accessible without authentication.
        Trang chủ phải truy cập được mà không cần đăng nhập.
        """

        response = self.client.get(
            reverse(
                "hotel_site:home"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_public_room_page_is_public(
        self,
    ):
        """
        Public room inventory must be accessible to guests.
        Danh sách phòng public phải truy cập được với khách chưa đăng nhập.
        """

        response = self.client.get(
            reverse(
                "hotel_site:public_rooms"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_about_page_is_public(
        self,
    ):
        """
        About page must remain publicly accessible.
        Trang About phải tiếp tục truy cập công khai.
        """

        response = self.client.get(
            reverse(
                "hotel_site:about"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_contact_page_is_public(
        self,
    ):
        """
        Contact page must remain publicly accessible.
        Trang Contact phải tiếp tục truy cập công khai.
        """

        response = self.client.get(
            reverse(
                "hotel_site:contact"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )


# ============================================================
# PUBLIC ROOM INVENTORY TESTS
# TEST DANH SÁCH PHÒNG PUBLIC
# ============================================================

class PublicRoomInventoryTests(
    HotelSiteBaseTestCase
):

    def test_public_room_list_contains_all_operational_states(
        self,
    ):
        """
        Public inventory must not equate current Room.status
        with future booking availability.

        Inventory public không được xem Room.status hiện tại
        là availability cho mọi ngày tương lai.
        """

        available_room = (
            self.create_room(
                status="available"
            )
        )

        reserved_room = (
            self.create_room(
                status="reserved"
            )
        )

        occupied_room = (
            self.create_room(
                status="occupied"
            )
        )

        cleaning_room = (
            self.create_room(
                status="cleaning"
            )
        )

        maintenance_room = (
            self.create_room(
                status="maintenance"
            )
        )

        response = self.client.get(
            reverse(
                "hotel_site:public_rooms"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        room_ids = {
            room.pk
            for room in response.context[
                "rooms"
            ]
        }

        # Current operational status must not silently remove
        # a room from the public room inventory.
        # Trạng thái vận hành hiện tại không được âm thầm
        # loại phòng khỏi inventory public.
        self.assertIn(
            available_room.pk,
            room_ids,
        )

        self.assertIn(
            reserved_room.pk,
            room_ids,
        )

        self.assertIn(
            occupied_room.pk,
            room_ids,
        )

        self.assertIn(
            cleaning_room.pk,
            room_ids,
        )

        self.assertIn(
            maintenance_room.pk,
            room_ids,
        )


# ============================================================
# CUSTOMER PORTAL NAVIGATION TESTS
# TEST LIÊN KẾT CUSTOMER PORTAL
# ============================================================

class CustomerPortalNavigationTests(
    HotelSiteBaseTestCase
):

    def test_home_links_to_customer_registration(
        self,
    ):
        """
        Guests must be directed to Customer Portal registration.
        Khách phải được dẫn tới trang đăng ký Customer Portal.
        """

        response = self.client.get(
            reverse(
                "hotel_site:home"
            )
        )

        registration_url = reverse(
            "customer_portal:customer_register"
        )

        self.assertContains(
            response,
            registration_url,
        )

    def test_home_links_to_customer_login(
        self,
    ):
        """
        Guests must be directed to Customer Portal login.
        Khách phải được dẫn tới trang đăng nhập Customer Portal.
        """

        response = self.client.get(
            reverse(
                "hotel_site:home"
            )
        )

        login_url = reverse(
            "customer_portal:customer_login"
        )

        self.assertContains(
            response,
            login_url,
        )

    def test_contact_page_links_to_staff_login(
        self,
    ):
        """
        Contact page must use the named staff login URL.
        Trang Contact phải dùng named URL của staff login.
        """

        response = self.client.get(
            reverse(
                "hotel_site:contact"
            )
        )

        staff_login_url = (
            reverse("login")
        )

        self.assertContains(
            response,
            staff_login_url,
        )


# ============================================================
# LEGACY PUBLIC BOOKING ROUTE TESTS
# TEST ROUTE PUBLIC BOOKING LEGACY
# ============================================================

class LegacyPublicBookingRouteTests(
    HotelSiteBaseTestCase
):

    def test_legacy_public_online_path_returns_404(
        self,
    ):
        """
        Removed legacy public Booking endpoint must remain unavailable.
        Endpoint public Booking legacy đã xóa phải tiếp tục không tồn tại.
        """

        response = self.client.get(
            "/bookings/online/"
        )

        self.assertEqual(
            response.status_code,
            404,
        )