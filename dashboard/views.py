from django.shortcuts import render

from accounts.decorators import group_required
from bookings.models import Booking
from customer_portal.models import (
    CustomerBooking,
    CustomerProfile,
)
from customers.models import Customer
from rooms.models import Room


# ============================================================
# CUSTOMER IDENTIFIER HELPERS
# HÀM HỖ TRỢ ĐỊNH DANH CUSTOMER
# ============================================================

def normalize_identifier(value):
    """
    Normalize a value before comparing customer identifiers.
    Chuẩn hóa giá trị trước khi so sánh định danh customer.
    """

    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
    )


def get_customer_identifiers(
    identity_number=None,
    email=None,
    phone=None,
):
    """
    Build identifiers used to recognize the same person
    across Customer and CustomerProfile.

    Tạo các định danh dùng để nhận biết cùng một người
    giữa Customer và CustomerProfile.
    """

    identifiers = set()

    normalized_identity = (
        normalize_identifier(
            identity_number
        )
    )

    normalized_email = (
        normalize_identifier(
            email
        )
    )

    normalized_phone = (
        normalize_identifier(
            phone
        )
    )

    if normalized_identity:
        identifiers.add(
            f"identity:{normalized_identity}"
        )

    if normalized_email:
        identifiers.add(
            f"email:{normalized_email}"
        )

    if normalized_phone:
        identifiers.add(
            f"phone:{normalized_phone}"
        )

    return identifiers


def merge_customer_identifiers(
    customer_groups,
    identifiers,
):
    """
    Merge identifiers into an existing customer group
    when at least one identifier matches.

    Gộp identifiers vào nhóm customer hiện có
    nếu ít nhất một định danh trùng khớp.
    """

    matched_indexes = []

    for index, group in enumerate(
        customer_groups
    ):
        if group.intersection(
            identifiers
        ):
            matched_indexes.append(
                index
            )

    if not matched_indexes:
        customer_groups.append(
            identifiers
        )
        return

    # Merge every connected group to preserve transitive matches.
    # Gộp toàn bộ nhóm liên quan để giữ quan hệ trùng bắc cầu.
    merged_group = set(
        identifiers
    )

    for index in reversed(
        matched_indexes
    ):
        merged_group.update(
            customer_groups.pop(
                index
            )
        )

    customer_groups.append(
        merged_group
    )


def count_unique_customers():
    """
    Estimate unique customers across Customer and CustomerProfile.

    Ước tính số customer duy nhất giữa Customer và CustomerProfile.

    Records are treated as the same person when at least one
    normalized identity number, email, or phone number connects them.

    Các record được xem là cùng một người nếu có ít nhất một
    identity number, email hoặc phone đã chuẩn hóa kết nối chúng.
    """

    customer_groups = []

    # ========================================================
    # STAFF-MANAGED CUSTOMERS
    # CUSTOMER ĐƯỢC STAFF QUẢN LÝ
    # ========================================================

    staff_customers = (
        Customer.objects.all()
    )

    for customer in staff_customers:

        identifiers = (
            get_customer_identifiers(
                identity_number=(
                    customer.id_card_number
                ),
                email=customer.email,
                phone=customer.phone,
            )
        )

        # Use a record-specific fallback when no reusable
        # customer identifier exists.
        #
        # Dùng fallback riêng cho record khi không có
        # định danh customer có thể đối chiếu.
        if not identifiers:
            identifiers.add(
                f"staff_customer:{customer.pk}"
            )

        merge_customer_identifiers(
            customer_groups,
            identifiers,
        )

    # ========================================================
    # CUSTOMER PORTAL ACCOUNTS
    # TÀI KHOẢN CUSTOMER PORTAL
    # ========================================================

    portal_customers = (
        CustomerProfile.objects
        .select_related(
            "user"
        )
        .all()
    )

    for profile in portal_customers:

        identifiers = (
            get_customer_identifiers(
                identity_number=(
                    profile.identity_number
                ),
                email=profile.user.email,
                phone=profile.phone,
            )
        )

        if not identifiers:
            identifiers.add(
                f"customer_profile:{profile.pk}"
            )

        merge_customer_identifiers(
            customer_groups,
            identifiers,
        )

    return len(
        customer_groups
    )


# ============================================================
# STAFF DASHBOARD
# DASHBOARD STAFF
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def dashboard_view(request):

    # ========================================================
    # CUSTOMER STATISTICS
    # THỐNG KÊ CUSTOMER
    # ========================================================

    # Customer records maintained by staff.
    # Record customer được staff quản lý.
    staff_customers_count = (
        Customer.objects.count()
    )

    # Registered Customer Portal accounts.
    # Tài khoản đã đăng ký trong Customer Portal.
    portal_customers_count = (
        CustomerProfile.objects.count()
    )

    # Estimate unique people instead of directly adding
    # two separate customer tables.
    #
    # Ước tính số người duy nhất thay vì cộng trực tiếp
    # hai bảng customer riêng biệt.
    total_customers = (
        count_unique_customers()
    )

    # ========================================================
    # ROOM OPERATIONAL STATUS
    # TRẠNG THÁI VẬN HÀNH PHÒNG
    # ========================================================

    total_rooms = (
        Room.objects.count()
    )

    available_rooms = (
        Room.objects
        .filter(
            status="available"
        )
        .count()
    )

    reserved_rooms = (
        Room.objects
        .filter(
            status="reserved"
        )
        .count()
    )

    occupied_rooms = (
        Room.objects
        .filter(
            status="occupied"
        )
        .count()
    )

    cleaning_rooms = (
        Room.objects
        .filter(
            status="cleaning"
        )
        .count()
    )

    maintenance_rooms = (
        Room.objects
        .filter(
            status="maintenance"
        )
        .count()
    )

    # ========================================================
    # CURRENT BOOKING WORKFLOWS
    # WORKFLOW BOOKING HIỆN TẠI
    # ========================================================

    # Current staff workflow uses Booking with
    # source == Receptionist.
    #
    # Workflow staff hiện tại dùng Booking với
    # source == Receptionist.
    staff_bookings_count = (
        Booking.objects
        .filter(
            source=(
                Booking.SOURCE_RECEPTIONIST
            )
        )
        .count()
    )

    # Current online workflow uses CustomerBooking.
    # Workflow online hiện tại dùng CustomerBooking.
    portal_bookings_count = (
        CustomerBooking.objects.count()
    )

    # Current workflow total intentionally excludes
    # legacy public Booking records.
    #
    # Tổng workflow hiện tại chủ động không tính
    # các public Booking legacy.
    total_bookings = (
        staff_bookings_count
        + portal_bookings_count
    )

    # ========================================================
    # LEGACY BOOKING HISTORY
    # LỊCH SỬ BOOKING LEGACY
    # ========================================================

    # These records belong to the removed legacy public
    # booking workflow and are retained only as history.
    #
    # Các record này thuộc public booking workflow cũ
    # đã bị loại bỏ và chỉ được giữ làm lịch sử.
    legacy_online_bookings_count = (
        Booking.objects
        .filter(
            source=(
                Booking.SOURCE_ONLINE
            )
        )
        .count()
    )

    # Include this only when a view/report needs to describe
    # every historical booking record stored in the database.
    #
    # Chỉ dùng số này khi cần mô tả toàn bộ record booking
    # lịch sử hiện còn lưu trong database.
    all_booking_records_count = (
        Booking.objects.count()
        + portal_bookings_count
    )

    # ========================================================
    # CUSTOMER PORTAL BOOKING STATUS
    # TRẠNG THÁI CUSTOMER PORTAL BOOKING
    # ========================================================

    pending_online_bookings = (
        CustomerBooking.objects
        .filter(
            status=(
                CustomerBooking.STATUS_PENDING
            )
        )
        .count()
    )

    confirmed_online_bookings = (
        CustomerBooking.objects
        .filter(
            status=(
                CustomerBooking.STATUS_CONFIRMED
            )
        )
        .count()
    )

    checked_in_online_bookings = (
        CustomerBooking.objects
        .filter(
            status=(
                CustomerBooking.STATUS_CHECKED_IN
            )
        )
        .count()
    )

    checked_out_online_bookings = (
        CustomerBooking.objects
        .filter(
            status=(
                CustomerBooking.STATUS_CHECKED_OUT
            )
        )
        .count()
    )

    cancelled_online_bookings = (
        CustomerBooking.objects
        .filter(
            status=(
                CustomerBooking.STATUS_CANCELLED
            )
        )
        .count()
    )

    # ========================================================
    # RECENT CURRENT-WORKFLOW BOOKINGS
    # BOOKING GẦN ĐÂY CỦA WORKFLOW HIỆN TẠI
    # ========================================================

    # Do not mix legacy public Booking records into
    # the recent staff booking list.
    #
    # Không trộn public Booking legacy vào danh sách
    # booking staff gần đây.
    recent_bookings = (
        Booking.objects
        .filter(
            source=(
                Booking.SOURCE_RECEPTIONIST
            )
        )
        .select_related(
            "customer",
            "room",
            "room__room_type",
        )
        .order_by(
            "-created_at"
        )[:5]
    )

    recent_online_bookings = (
        CustomerBooking.objects
        .select_related(
            "customer_user",
            "room",
            "room__room_type",
        )
        .order_by(
            "-created_at"
        )[:5]
    )

    # ========================================================
    # TEMPLATE CONTEXT
    # CONTEXT CHO TEMPLATE
    # ========================================================

    context = {
        # Customer statistics.
        # Thống kê customer.
        "total_customers": (
            total_customers
        ),
        "staff_customers_count": (
            staff_customers_count
        ),
        "online_customers_count": (
            portal_customers_count
        ),
        "portal_customers_count": (
            portal_customers_count
        ),

        # Current room operational state.
        # Trạng thái vận hành hiện tại của phòng.
        "total_rooms": (
            total_rooms
        ),
        "available_rooms": (
            available_rooms
        ),
        "reserved_rooms": (
            reserved_rooms
        ),
        "occupied_rooms": (
            occupied_rooms
        ),
        "cleaning_rooms": (
            cleaning_rooms
        ),
        "maintenance_rooms": (
            maintenance_rooms
        ),

        # Current booking workflows.
        # Workflow booking hiện tại.
        "total_bookings": (
            total_bookings
        ),
        "staff_bookings_count": (
            staff_bookings_count
        ),
        "online_bookings_count": (
            portal_bookings_count
        ),
        "portal_bookings_count": (
            portal_bookings_count
        ),

        # Historical legacy records.
        # Record legacy lịch sử.
        "legacy_online_bookings_count": (
            legacy_online_bookings_count
        ),
        "all_booking_records_count": (
            all_booking_records_count
        ),

        # Customer Portal booking statuses.
        # Trạng thái booking Customer Portal.
        "pending_online_bookings": (
            pending_online_bookings
        ),
        "confirmed_online_bookings": (
            confirmed_online_bookings
        ),
        "checked_in_online_bookings": (
            checked_in_online_bookings
        ),
        "checked_out_online_bookings": (
            checked_out_online_bookings
        ),
        "cancelled_online_bookings": (
            cancelled_online_bookings
        ),

        # Recent current-workflow bookings.
        # Booking gần đây của workflow hiện tại.
        "recent_bookings": (
            recent_bookings
        ),
        "recent_online_bookings": (
            recent_online_bookings
        ),
    }

    return render(
        request,
        "dashboard/index.html",
        context,
    )