from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render

from accounts.decorators import group_required
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
from rooms.models import Room


# ============================================================
# CUSTOMER IDENTIFIER HELPERS
# HÀM HỖ TRỢ ĐỊNH DANH CUSTOMER
# ============================================================

def normalize_identifier(value):
    """
    Normalize an identifier before comparison.
    Chuẩn hóa định danh trước khi so sánh.
    """

    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
    )


def build_customer_identifiers(
    identity_number=None,
    email=None,
    phone=None,
):
    """
    Build identifiers used to detect duplicate customers.
    Tạo định danh dùng để phát hiện customer trùng nhau.
    """

    identifiers = set()

    identity_number = (
        normalize_identifier(
            identity_number
        )
    )

    email = (
        normalize_identifier(
            email
        )
    )

    phone = (
        normalize_identifier(
            phone
        )
    )

    if identity_number:
        identifiers.add(
            f"identity:{identity_number}"
        )

    if email:
        identifiers.add(
            f"email:{email}"
        )

    if phone:
        identifiers.add(
            f"phone:{phone}"
        )

    return identifiers


def merge_customer_group(
    groups,
    identifiers,
):
    """
    Merge identifiers into an existing matching customer group.
    Gộp identifiers vào nhóm customer trùng khớp hiện có.
    """

    matched_indexes = []

    for index, group in enumerate(
        groups
    ):
        if group.intersection(
            identifiers
        ):
            matched_indexes.append(
                index
            )

    if not matched_indexes:
        groups.append(
            set(
                identifiers
            )
        )
        return

    # Merge all connected groups to preserve transitive matches.
    # Gộp toàn bộ nhóm liên quan để giữ quan hệ trùng bắc cầu.
    merged_group = set(
        identifiers
    )

    for index in reversed(
        matched_indexes
    ):
        merged_group.update(
            groups.pop(
                index
            )
        )

    groups.append(
        merged_group
    )


def count_unique_customers():
    """
    Estimate unique customers across Customer and CustomerProfile.
    Ước tính customer duy nhất giữa Customer và CustomerProfile.
    """

    groups = []

    # ========================================================
    # STAFF-MANAGED CUSTOMERS
    # CUSTOMER ĐƯỢC STAFF QUẢN LÝ
    # ========================================================

    for customer in (
        Customer.objects.all()
    ):
        identifiers = (
            build_customer_identifiers(
                identity_number=(
                    customer.id_card_number
                ),
                email=customer.email,
                phone=customer.phone,
            )
        )

        # Every record needs a fallback identifier when no
        # reusable identity/email/phone value exists.
        # Mỗi record cần fallback khi không có
        # identity/email/phone để đối chiếu.
        if not identifiers:
            identifiers = {
                f"customer:{customer.pk}"
            }

        merge_customer_group(
            groups,
            identifiers,
        )

    # ========================================================
    # CUSTOMER PORTAL ACCOUNTS
    # TÀI KHOẢN CUSTOMER PORTAL
    # ========================================================

    profiles = (
        CustomerProfile.objects
        .select_related(
            "user"
        )
        .all()
    )

    for profile in profiles:
        identifiers = (
            build_customer_identifiers(
                identity_number=(
                    profile.identity_number
                ),
                email=profile.user.email,
                phone=profile.phone,
            )
        )

        if not identifiers:
            identifiers = {
                f"profile:{profile.pk}"
            }

        merge_customer_group(
            groups,
            identifiers,
        )

    return len(
        groups
    )


# ============================================================
# REPORTS DASHBOARD
# DASHBOARD BÁO CÁO
# ============================================================

@group_required("Admin")
def reports_dashboard(request):

    # ========================================================
    # CUSTOMER STATISTICS
    # THỐNG KÊ CUSTOMER
    # ========================================================

    staff_customers_count = (
        Customer.objects.count()
    )

    portal_customers_count = (
        CustomerProfile.objects.count()
    )

    # Estimate unique people rather than directly adding
    # the two independent customer tables.
    # Ước tính số người duy nhất thay vì cộng trực tiếp
    # hai bảng customer độc lập.
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

    # The current staff workflow uses Booking records
    # created by Receptionist.
    # Workflow staff hiện tại dùng Booking
    # được tạo bởi Receptionist.
    staff_booking_queryset = (
        Booking.objects
        .filter(
            source=(
                Booking.SOURCE_RECEPTIONIST
            )
        )
    )

    staff_bookings_count = (
        staff_booking_queryset.count()
    )

    # The current online workflow uses CustomerBooking.
    # Workflow online hiện tại dùng CustomerBooking.
    portal_bookings_count = (
        CustomerBooking.objects.count()
    )

    # Current workflow total intentionally excludes
    # the removed legacy public Booking flow.
    # Tổng workflow hiện tại chủ động không tính
    # public Booking legacy đã bị loại bỏ.
    total_bookings = (
        staff_bookings_count
        + portal_bookings_count
    )

    # ========================================================
    # LEGACY BOOKING HISTORY
    # LỊCH SỬ BOOKING LEGACY
    # ========================================================

    legacy_booking_queryset = (
        Booking.objects
        .filter(
            source=(
                Booking.SOURCE_ONLINE
            )
        )
    )

    legacy_online_bookings_count = (
        legacy_booking_queryset.count()
    )

    # Count every booking record still stored in the database.
    # Đếm toàn bộ booking record vẫn còn lưu trong database.
    all_booking_records_count = (
        total_bookings
        + legacy_online_bookings_count
    )

    # ========================================================
    # CURRENT CHECK-IN STATISTICS
    # THỐNG KÊ CHECK-IN HIỆN TẠI
    # ========================================================

    staff_checkins_count = (
        CheckIn.objects
        .filter(
            booking__source=(
                Booking.SOURCE_RECEPTIONIST
            )
        )
        .count()
    )

    portal_checkins_count = (
        OnlineCheckIn.objects.count()
    )

    # Current workflow total.
    # Tổng workflow hiện tại.
    total_checkins = (
        staff_checkins_count
        + portal_checkins_count
    )

    # ========================================================
    # LEGACY CHECK-IN HISTORY
    # LỊCH SỬ CHECK-IN LEGACY
    # ========================================================

    legacy_online_checkins_count = (
        CheckIn.objects
        .filter(
            booking__source=(
                Booking.SOURCE_ONLINE
            )
        )
        .count()
    )

    all_checkin_records_count = (
        total_checkins
        + legacy_online_checkins_count
    )

    # ========================================================
    # CURRENT CHECKOUT STATISTICS
    # THỐNG KÊ CHECKOUT HIỆN TẠI
    # ========================================================

    staff_checkouts_count = (
        CheckOut.objects
        .filter(
            booking__source=(
                Booking.SOURCE_RECEPTIONIST
            )
        )
        .count()
    )

    portal_checkouts_count = (
        OnlineCheckOut.objects.count()
    )

    total_checkouts = (
        staff_checkouts_count
        + portal_checkouts_count
    )

    # ========================================================
    # LEGACY CHECKOUT HISTORY
    # LỊCH SỬ CHECKOUT LEGACY
    # ========================================================

    legacy_online_checkouts_count = (
        CheckOut.objects
        .filter(
            booking__source=(
                Booking.SOURCE_ONLINE
            )
        )
        .count()
    )

    all_checkout_records_count = (
        total_checkouts
        + legacy_online_checkouts_count
    )

    # ========================================================
    # CURRENT WORKFLOW REVENUE
    # DOANH THU WORKFLOW HIỆN TẠI
    # ========================================================

    # Payment records are manual/simulated payment records.
    # Payment record là dữ liệu thanh toán thủ công/mô phỏng.
    staff_revenue = (
        Payment.objects
        .filter(
            status="paid",
            booking__source=(
                Booking.SOURCE_RECEPTIONIST
            ),
        )
        .aggregate(
            total=Sum(
                "amount"
            )
        )["total"]
        or Decimal("0.00")
    )

    portal_revenue = (
        OnlinePayment.objects
        .filter(
            status="paid"
        )
        .aggregate(
            total=Sum(
                "amount"
            )
        )["total"]
        or Decimal("0.00")
    )

    # Current workflow revenue excludes legacy public bookings.
    # Doanh thu workflow hiện tại không tính public booking legacy.
    total_revenue = (
        staff_revenue
        + portal_revenue
    )

    # ========================================================
    # LEGACY REVENUE HISTORY
    # LỊCH SỬ DOANH THU LEGACY
    # ========================================================

    legacy_online_revenue = (
        Payment.objects
        .filter(
            status="paid",
            booking__source=(
                Booking.SOURCE_ONLINE
            ),
        )
        .aggregate(
            total=Sum(
                "amount"
            )
        )["total"]
        or Decimal("0.00")
    )

    # Every paid record still stored in the database.
    # Toàn bộ payment paid còn lưu trong database.
    all_recorded_revenue = (
        total_revenue
        + legacy_online_revenue
    )

    # ========================================================
    # CURRENT OCCUPANCY RATE
    # TỶ LỆ PHÒNG ĐANG SỬ DỤNG HIỆN TẠI
    # ========================================================

    # This is a point-in-time operational occupancy ratio,
    # not a historical occupancy KPI over a date range.
    #
    # Đây là tỷ lệ occupied tại thời điểm hiện tại,
    # không phải KPI occupancy lịch sử theo khoảng thời gian.
    if total_rooms:
        occupancy_rate = round(
            (
                occupied_rooms
                / total_rooms
            )
            * 100,
            2,
        )

    else:
        occupancy_rate = 0

    # ========================================================
    # STAFF BOOKING STATUS
    # TRẠNG THÁI BOOKING STAFF
    # ========================================================

    pending_bookings = (
        staff_booking_queryset
        .filter(
            status=(
                Booking
                .STATUS_PENDING_CONFIRMATION
            )
        )
        .count()
    )

    confirmed_bookings = (
        staff_booking_queryset
        .filter(
            status=(
                Booking.STATUS_CONFIRMED
            )
        )
        .count()
    )

    checked_in_bookings = (
        staff_booking_queryset
        .filter(
            status=(
                Booking.STATUS_CHECKED_IN
            )
        )
        .count()
    )

    checked_out_bookings = (
        staff_booking_queryset
        .filter(
            status=(
                Booking.STATUS_CHECKED_OUT
            )
        )
        .count()
    )

    cancelled_bookings = (
        staff_booking_queryset
        .filter(
            status=(
                Booking.STATUS_CANCELLED
            )
        )
        .count()
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
    # CURRENT MONTHLY REVENUE
    # DOANH THU HIỆN TẠI THEO THÁNG
    # ========================================================

    # Include only Receptionist Booking payments in the
    # current staff-workflow revenue chart.
    #
    # Chỉ tính Payment của Receptionist Booking trong
    # biểu đồ doanh thu workflow staff hiện tại.
    staff_monthly_revenue = (
        Payment.objects
        .filter(
            status="paid",
            booking__source=(
                Booking.SOURCE_RECEPTIONIST
            ),
        )
        .annotate(
            month=TruncMonth(
                "payment_date"
            )
        )
        .values(
            "month"
        )
        .annotate(
            total=Sum(
                "amount"
            )
        )
        .order_by(
            "month"
        )
    )

    # Include Customer Portal payment records.
    # Tính các payment record của Customer Portal.
    portal_monthly_revenue = (
        OnlinePayment.objects
        .filter(
            status="paid"
        )
        .annotate(
            month=TruncMonth(
                "payment_date"
            )
        )
        .values(
            "month"
        )
        .annotate(
            total=Sum(
                "amount"
            )
        )
        .order_by(
            "month"
        )
    )

    revenue_by_month = {}

    for item in staff_monthly_revenue:

        if not item["month"]:
            continue

        month_label = (
            item["month"]
            .strftime(
                "%Y-%m"
            )
        )

        revenue_by_month[
            month_label
        ] = (
            revenue_by_month.get(
                month_label,
                0.0,
            )
            + float(
                item["total"]
                or 0
            )
        )

    for item in portal_monthly_revenue:

        if not item["month"]:
            continue

        month_label = (
            item["month"]
            .strftime(
                "%Y-%m"
            )
        )

        revenue_by_month[
            month_label
        ] = (
            revenue_by_month.get(
                month_label,
                0.0,
            )
            + float(
                item["total"]
                or 0
            )
        )

    # Show at most six recent months that contain
    # current-workflow paid payment records.
    #
    # Chỉ hiển thị tối đa sáu tháng gần nhất có
    # payment paid thuộc workflow hiện tại.
    revenue_labels = (
        sorted(
            revenue_by_month.keys()
        )[-6:]
    )

    revenue_values = [
        revenue_by_month[
            month
        ]
        for month in revenue_labels
    ]

    # ========================================================
    # RECENT CURRENT-WORKFLOW PAYMENTS
    # PAYMENT GẦN ĐÂY CỦA WORKFLOW HIỆN TẠI
    # ========================================================

    recent_payments = (
        Payment.objects
        .filter(
            booking__source=(
                Booking.SOURCE_RECEPTIONIST
            )
        )
        .select_related(
            "booking",
            "booking__customer",
            "booking__room",
        )
        .order_by(
            "-payment_date"
        )[:10]
    )

    recent_online_payments = (
        OnlinePayment.objects
        .select_related(
            "booking",
            "booking__customer_user",
            "booking__room",
        )
        .order_by(
            "-payment_date"
        )[:10]
    )

    # ========================================================
    # RECENT CUSTOMER PORTAL BOOKINGS
    # CUSTOMER PORTAL BOOKING GẦN ĐÂY
    # ========================================================

    recent_online_bookings = (
        CustomerBooking.objects
        .select_related(
            "customer_user",
            "room",
            "room__room_type",
        )
        .order_by(
            "-created_at"
        )[:10]
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

        # Room operational status.
        # Trạng thái vận hành phòng.
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

        # Legacy booking history.
        # Lịch sử booking legacy.
        "legacy_online_bookings_count": (
            legacy_online_bookings_count
        ),
        "all_booking_records_count": (
            all_booking_records_count
        ),

        # Current check-in workflow.
        # Workflow check-in hiện tại.
        "total_checkins": (
            total_checkins
        ),
        "staff_checkins_count": (
            staff_checkins_count
        ),
        "online_checkins_count": (
            portal_checkins_count
        ),
        "portal_online_checkins_count": (
            portal_checkins_count
        ),

        # Legacy check-in history.
        # Lịch sử check-in legacy.
        "legacy_online_checkins_count": (
            legacy_online_checkins_count
        ),
        "all_checkin_records_count": (
            all_checkin_records_count
        ),

        # Current checkout workflow.
        # Workflow checkout hiện tại.
        "total_checkouts": (
            total_checkouts
        ),
        "staff_checkouts_count": (
            staff_checkouts_count
        ),
        "online_checkouts_count": (
            portal_checkouts_count
        ),
        "portal_online_checkouts_count": (
            portal_checkouts_count
        ),

        # Legacy checkout history.
        # Lịch sử checkout legacy.
        "legacy_online_checkouts_count": (
            legacy_online_checkouts_count
        ),
        "all_checkout_records_count": (
            all_checkout_records_count
        ),

        # Current workflow revenue.
        # Doanh thu workflow hiện tại.
        "staff_revenue": (
            staff_revenue
        ),
        "portal_online_revenue": (
            portal_revenue
        ),
        "online_revenue": (
            portal_revenue
        ),
        "total_revenue": (
            total_revenue
        ),

        # Legacy/historical revenue.
        # Doanh thu legacy/lịch sử.
        "legacy_online_revenue": (
            legacy_online_revenue
        ),
        "all_recorded_revenue": (
            all_recorded_revenue
        ),

        # Current operational occupancy ratio.
        # Tỷ lệ occupied vận hành hiện tại.
        "occupancy_rate": (
            occupancy_rate
        ),

        # Staff Booking statuses.
        # Trạng thái Booking staff.
        "pending_bookings": (
            pending_bookings
        ),
        "confirmed_bookings": (
            confirmed_bookings
        ),
        "checked_in_bookings": (
            checked_in_bookings
        ),
        "checked_out_bookings": (
            checked_out_bookings
        ),
        "cancelled_bookings": (
            cancelled_bookings
        ),

        # Customer Portal booking statuses.
        # Trạng thái Customer Portal booking.
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

        # Recent current-workflow data.
        # Dữ liệu workflow hiện tại gần đây.
        "recent_payments": (
            recent_payments
        ),
        "recent_online_payments": (
            recent_online_payments
        ),
        "recent_online_bookings": (
            recent_online_bookings
        ),

        # Current-workflow revenue chart.
        # Biểu đồ doanh thu workflow hiện tại.
        "revenue_labels": (
            revenue_labels
        ),
        "revenue_values": (
            revenue_values
        ),
    }

    return render(
        request,
        "reports/reports_dashboard.html",
        context,
    )