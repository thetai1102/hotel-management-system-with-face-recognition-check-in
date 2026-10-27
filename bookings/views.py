import logging

from django.contrib import messages
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import group_required
from customer_portal.models import CustomerBooking

from .forms import BookingForm
from .models import Booking


logger = logging.getLogger(__name__)


# ============================================================
# ROOM STATUS SERVICE
# DỊCH VỤ CẬP NHẬT TRẠNG THÁI PHÒNG
# ============================================================

def refresh_room_status(room):
    """
    Refresh the room's current operational status.
    Cập nhật trạng thái vận hành hiện tại của phòng.

    Future reservations do not automatically make a room
    reserved today. Future availability is determined by
    booking-date overlap validation.

    Booking trong tương lai không tự động làm phòng thành
    reserved hôm nay. Availability tương lai được xác định
    bằng validation khoảng thời gian booking.
    """

    # Maintenance and cleaning are explicit operational states
    # and must not be overwritten automatically.
    # Maintenance và cleaning là trạng thái vận hành chủ động
    # nên không được tự động ghi đè.
    if room.status in [
        "maintenance",
        "cleaning",
    ]:
        return

    today = timezone.localdate()

    # ========================================================
    # CURRENT OCCUPANCY
    # TRẠNG THÁI ĐANG CÓ KHÁCH
    # ========================================================

    # A checked-in staff booking means the room is occupied.
    # Booking staff đã check-in nghĩa là phòng đang occupied.
    staff_checked_in = (
        Booking.objects
        .filter(
            room=room,
            status=Booking.STATUS_CHECKED_IN,
        )
        .exists()
    )

    # A checked-in Customer Portal booking also occupies the room.
    # CustomerBooking đã check-in cũng làm phòng occupied.
    portal_checked_in = (
        CustomerBooking.objects
        .filter(
            room=room,
            status=CustomerBooking.STATUS_CHECKED_IN,
        )
        .exists()
    )

    if (
        staff_checked_in
        or portal_checked_in
    ):
        if room.status != "occupied":
            room.status = "occupied"

            room.save(
                update_fields=[
                    "status",
                ]
            )

        return

    # ========================================================
    # RESERVATION RELEVANT TO TODAY
    # RESERVATION LIÊN QUAN ĐẾN HÔM NAY
    # ========================================================

    # Only staff reservations whose stay includes today
    # affect the room's current Reserved status.
    # Chỉ booking staff có khoảng lưu trú chứa hôm nay
    # mới ảnh hưởng trạng thái Reserved hiện tại.
    staff_reserved_today = (
        Booking.objects
        .filter(
            room=room,
            status__in=[
                Booking.STATUS_PENDING_CONFIRMATION,
                Booking.STATUS_CONFIRMED,
            ],
            check_in_date__lte=today,
            check_out_date__gt=today,
        )
        .exists()
    )

    # Only Customer Portal reservations whose stay includes
    # today affect the current Reserved status.
    # Chỉ CustomerBooking có khoảng lưu trú chứa hôm nay
    # mới ảnh hưởng trạng thái Reserved hiện tại.
    portal_reserved_today = (
        CustomerBooking.objects
        .filter(
            room=room,
            status__in=[
                CustomerBooking.STATUS_PENDING,
                CustomerBooking.STATUS_CONFIRMED,
            ],
            check_in_at__date__lte=today,
            check_out_at__date__gt=today,
        )
        .exists()
    )

    if (
        staff_reserved_today
        or portal_reserved_today
    ):
        if room.status != "reserved":
            room.status = "reserved"

            room.save(
                update_fields=[
                    "status",
                ]
            )

        return

    # No current booking occupies or reserves the room.
    # Không có booking hiện tại đang chiếm hoặc giữ phòng.
    if room.status != "available":
        room.status = "available"

        room.save(
            update_fields=[
                "status",
            ]
        )


# ============================================================
# CUSTOMER PORTAL EMAIL
# EMAIL CUSTOMER PORTAL
# ============================================================

def send_booking_status_email(
    booking,
    subject,
    message,
):
    """
    Send Customer Portal booking status email.
    Gửi email thông báo trạng thái Customer Portal booking.
    """

    try:
        booking.customer_user.email_user(
            subject=subject,
            message=message,
        )

    except Exception:
        # Email failure must not roll back the booking status.
        # Lỗi email không được rollback trạng thái booking.
        logger.exception(
            "Unable to send Customer Portal booking status email "
            "for booking id=%s.",
            booking.pk,
        )


# ============================================================
# STAFF BOOKING LIST
# DANH SÁCH BOOKING STAFF
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def booking_list(request):
    """
    Display staff-managed bookings.
    Hiển thị các booking do staff quản lý.
    """

    bookings = (
        Booking.objects
        .select_related(
            "customer",
            "room",
            "room__room_type",
        )
        .order_by(
            "-created_at"
        )
    )

    return render(
        request,
        "bookings/booking_list.html",
        {
            "bookings": bookings,
        },
    )


# ============================================================
# STAFF BOOKING CREATE
# TẠO BOOKING STAFF
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def booking_create(request):
    """
    Create a receptionist/staff booking.
    Tạo booking từ receptionist/staff.
    """

    if request.method == "POST":

        form = BookingForm(
            request.POST
        )

        if form.is_valid():

            booking = form.save(
                commit=False
            )

            # A booking created from this interface is a
            # receptionist/staff booking.
            # Booking tạo từ giao diện này là booking staff.
            booking.source = (
                Booking.SOURCE_RECEPTIONIST
            )

            booking.save()

            # Refresh only the current operational state.
            # Chỉ cập nhật trạng thái vận hành hiện tại.
            refresh_room_status(
                booking.room
            )

            messages.success(
                request,
                "Booking created successfully.",
            )

            return redirect(
                "bookings:booking_detail",
                pk=booking.pk,
            )

    else:

        form = BookingForm()

    return render(
        request,
        "bookings/booking_form.html",
        {
            "form": form,
            "title": "Add Booking",
        },
    )


# ============================================================
# STAFF BOOKING DETAIL
# CHI TIẾT BOOKING STAFF
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def booking_detail(
    request,
    pk,
):
    """
    Display a staff booking.
    Hiển thị chi tiết booking staff.
    """

    booking = get_object_or_404(
        Booking.objects
        .select_related(
            "customer",
            "room",
            "room__room_type",
        ),
        pk=pk,
    )

    return render(
        request,
        "bookings/booking_detail.html",
        {
            "booking": booking,
        },
    )


# ============================================================
# STAFF BOOKING UPDATE
# CẬP NHẬT BOOKING STAFF
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def booking_update(
    request,
    pk,
):
    """
    Update an editable staff booking.
    Cập nhật booking staff còn được phép chỉnh sửa.
    """

    booking = get_object_or_404(
        Booking.objects
        .select_related(
            "customer",
            "room",
            "room__room_type",
        ),
        pk=pk,
    )

    # Keep the original room id so both rooms can be refreshed
    # if the booking is moved.
    # Giữ ID phòng cũ để refresh cả hai phòng nếu booking đổi phòng.
    old_room = booking.room
    old_room_id = booking.room_id

    if request.method == "POST":

        form = BookingForm(
            request.POST,
            instance=booking,
        )

        if form.is_valid():

            updated_booking = (
                form.save()
            )

            # Always refresh the original room.
            # Luôn refresh phòng ban đầu.
            refresh_room_status(
                old_room
            )

            # Refresh the new room only when the room changed.
            # Chỉ refresh phòng mới khi booking thực sự đổi phòng.
            if (
                updated_booking.room_id
                != old_room_id
            ):
                refresh_room_status(
                    updated_booking.room
                )

            messages.success(
                request,
                "Booking updated successfully.",
            )

            return redirect(
                "bookings:booking_detail",
                pk=updated_booking.pk,
            )

    else:

        form = BookingForm(
            instance=booking
        )

    return render(
        request,
        "bookings/booking_form.html",
        {
            "form": form,
            "title": "Edit Booking",
        },
    )


# ============================================================
# STAFF BOOKING DELETE
# XÓA BOOKING STAFF
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def booking_delete(
    request,
    pk,
):
    """
    Delete an unprotected staff booking.
    Xóa booking staff chưa có lịch sử được bảo vệ.
    """

    booking = get_object_or_404(
        Booking.objects
        .select_related(
            "customer",
            "room",
        ),
        pk=pk,
    )

    if request.method == "POST":

        # Completed operational history must not be removed
        # through normal staff actions.
        # Lịch sử nghiệp vụ đã thực hiện không được xóa
        # bằng thao tác staff thông thường.
        if booking.status in [
            Booking.STATUS_CHECKED_IN,
            Booking.STATUS_CHECKED_OUT,
        ]:

            messages.error(
                request,
                "A checked-in or checked-out booking "
                "cannot be deleted.",
            )

            return redirect(
                "bookings:booking_detail",
                pk=booking.pk,
            )

        room = booking.room

        try:
            booking.delete()

        except ProtectedError:
            # PROTECT preserves CheckIn, CheckOut, and Payment history.
            # PROTECT bảo vệ lịch sử CheckIn, CheckOut và Payment.
            messages.error(
                request,
                "This booking cannot be deleted because "
                "it already has protected check-in, "
                "checkout, or payment history.",
            )

            return redirect(
                "bookings:booking_detail",
                pk=booking.pk,
            )

        refresh_room_status(
            room
        )

        messages.success(
            request,
            "Booking deleted successfully.",
        )

        return redirect(
            "bookings:booking_list"
        )

    return render(
        request,
        "bookings/booking_confirm_delete.html",
        {
            "booking": booking,
        },
    )


# ============================================================
# CUSTOMER PORTAL ONLINE BOOKING REQUESTS
# REQUEST BOOKING TỪ CUSTOMER PORTAL
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def online_booking_requests(request):
    """
    Display Customer Portal booking requests.
    Hiển thị các booking request từ Customer Portal.
    """

    status_filter = (
        request.GET.get(
            "status",
            "",
        )
    )

    bookings = (
        CustomerBooking.objects
        .select_related(
            "customer_user",
            "room",
            "room__room_type",
        )
        .all()
    )

    valid_statuses = dict(
        CustomerBooking.STATUS_CHOICES
    )

    if status_filter in valid_statuses:
        bookings = bookings.filter(
            status=status_filter
        )

    return render(
        request,
        "bookings/online_requests.html",
        {
            "bookings": bookings,
            "status_filter": status_filter,
            "status_choices": (
                CustomerBooking.STATUS_CHOICES
            ),
        },
    )


# ============================================================
# CUSTOMER PORTAL BOOKING DETAIL
# CHI TIẾT CUSTOMER PORTAL BOOKING
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def online_booking_detail(
    request,
    booking_id,
):
    """
    Display a Customer Portal booking request.
    Hiển thị chi tiết booking request từ Customer Portal.
    """

    booking = get_object_or_404(
        CustomerBooking.objects
        .select_related(
            "customer_user",
            "room",
            "room__room_type",
        ),
        id=booking_id,
    )

    return render(
        request,
        "bookings/online_request_detail.html",
        {
            "booking": booking,
        },
    )


# ============================================================
# CONFIRM CUSTOMER PORTAL BOOKING
# XÁC NHẬN CUSTOMER PORTAL BOOKING
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
@require_POST
def confirm_online_booking(
    request,
    booking_id,
):
    """
    Confirm a pending Customer Portal booking.
    Xác nhận Customer Portal booking đang Pending.
    """

    with transaction.atomic():

        booking = get_object_or_404(
            CustomerBooking.objects
            .select_for_update()
            .select_related(
                "customer_user",
                "room",
                "room__room_type",
            ),
            id=booking_id,
        )

        # Confirmed is an idempotent case.
        # Confirmed là trường hợp không cần thực hiện lại.
        if (
            booking.status
            == CustomerBooking.STATUS_CONFIRMED
        ):

            messages.info(
                request,
                "This booking has already been confirmed.",
            )

            return redirect(
                "bookings:online_booking_detail",
                booking_id=booking.id,
            )

        # Only Pending may transition to Confirmed.
        # Chỉ Pending mới được chuyển sang Confirmed.
        if (
            booking.status
            != CustomerBooking.STATUS_PENDING
        ):

            messages.error(
                request,
                "Only pending bookings can be confirmed.",
            )

            return redirect(
                "bookings:online_booking_detail",
                booking_id=booking.id,
            )

        booking.status = (
            CustomerBooking.STATUS_CONFIRMED
        )

        # Preserve the historical total price.
        # Giữ nguyên tổng giá lịch sử.
        booking.save(
            update_fields=[
                "status",
            ]
        )

        refresh_room_status(
            booking.room
        )

    subject = (
        "Your room booking has been confirmed"
    )

    message = (
        f"Hello {booking.full_name},\n\n"
        "Your room booking has been confirmed by the hotel.\n\n"
        f"Room: {booking.room}\n"
        f"Check-in time: {booking.check_in_at}\n"
        f"Check-out time: {booking.check_out_at}\n"
        f"Total price: {booking.total_price}\n"
        f"Booking status: {booking.get_status_display()}\n\n"
        "Please bring your identity document when you arrive "
        "at the hotel.\n\n"
        "Hotel Management System"
    )

    send_booking_status_email(
        booking,
        subject,
        message,
    )

    messages.success(
        request,
        "Booking has been confirmed successfully.",
    )

    return redirect(
        "bookings:online_booking_detail",
        booking_id=booking.id,
    )


# ============================================================
# CANCEL CUSTOMER PORTAL BOOKING
# HỦY CUSTOMER PORTAL BOOKING
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
@require_POST
def cancel_online_booking(
    request,
    booking_id,
):
    """
    Cancel a Customer Portal booking before check-in.
    Hủy Customer Portal booking trước khi check-in.
    """

    with transaction.atomic():

        booking = get_object_or_404(
            CustomerBooking.objects
            .select_for_update()
            .select_related(
                "customer_user",
                "room",
                "room__room_type",
            ),
            id=booking_id,
        )

        # Checked In and Checked Out bookings cannot be cancelled.
        # Booking Checked In hoặc Checked Out không được cancel.
        if booking.status in [
            CustomerBooking.STATUS_CHECKED_IN,
            CustomerBooking.STATUS_CHECKED_OUT,
        ]:

            messages.error(
                request,
                "A checked-in or checked-out booking "
                "cannot be cancelled.",
            )

            return redirect(
                "bookings:online_booking_detail",
                booking_id=booking.id,
            )

        # Cancelled is an idempotent case.
        # Cancelled là trường hợp không cần thực hiện lại.
        if (
            booking.status
            == CustomerBooking.STATUS_CANCELLED
        ):

            messages.info(
                request,
                "This booking has already been cancelled.",
            )

            return redirect(
                "bookings:online_booking_detail",
                booking_id=booking.id,
            )

        booking.status = (
            CustomerBooking.STATUS_CANCELLED
        )

        # Keep the historical total unchanged.
        # Giữ nguyên tổng giá lịch sử.
        booking.save(
            update_fields=[
                "status",
            ]
        )

        refresh_room_status(
            booking.room
        )

    subject = (
        "Your room booking has been cancelled"
    )

    message = (
        f"Hello {booking.full_name},\n\n"
        "Your room booking has been cancelled by the hotel.\n\n"
        f"Room: {booking.room}\n"
        f"Check-in time: {booking.check_in_at}\n"
        f"Check-out time: {booking.check_out_at}\n"
        f"Booking status: {booking.get_status_display()}\n\n"
        "Please contact the hotel if you need more information.\n\n"
        "Hotel Management System"
    )

    send_booking_status_email(
        booking,
        subject,
        message,
    )

    messages.warning(
        request,
        "Booking has been cancelled.",
    )

    return redirect(
        "bookings:online_booking_detail",
        booking_id=booking.id,
    )