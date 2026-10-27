import logging
from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login,
    logout,
)
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import require_POST

from bookings.models import Booking
from bookings.views import refresh_room_status
from rooms.models import Room

from .forms import (
    CustomerBookingForm,
    CustomerLoginForm,
    CustomerProfileForm,
    CustomerRegistrationForm,
)
from .models import CustomerBooking


logger = logging.getLogger(__name__)


# ============================================================
# CUSTOMER ACCESS CONTROL
# KIỂM SOÁT QUYỀN TRUY CẬP CUSTOMER
# ============================================================

def customer_required(view_func):
    """
    Allow only authenticated Customer Portal accounts.
    Chỉ cho phép tài khoản Customer Portal đã đăng nhập.
    """

    @wraps(view_func)
    def wrapper(
        request,
        *args,
        **kwargs,
    ):
        if not request.user.is_authenticated:
            return redirect(
                "customer_portal:customer_login"
            )

        # A valid Customer Portal account must have a profile.
        # Tài khoản Customer Portal hợp lệ phải có profile.
        if not hasattr(
            request.user,
            "customer_profile",
        ):
            messages.error(
                request,
                "This page is only for customer accounts.",
            )

            return redirect(
                "dashboard"
            )

        return view_func(
            request,
            *args,
            **kwargs,
        )

    return wrapper


# ============================================================
# EMAIL HELPERS
# HÀM HỖ TRỢ EMAIL
# ============================================================

def send_customer_registration_email(user):
    """
    Send account creation notification.
    Gửi thông báo tạo tài khoản customer.
    """

    subject = (
        "Your customer account has been created successfully"
    )

    message = (
        "Hello,\n\n"
        "Your customer account has been created successfully.\n\n"
        f"Login email: {user.email}\n\n"
        "You can now log in, update your personal information, "
        "browse rooms, and make room bookings.\n\n"
        "Hotel Management System"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[
            user.email,
        ],
        fail_silently=False,
    )


def send_customer_booking_email(booking):
    """
    Send booking submission notification.
    Gửi thông báo customer đã gửi booking request.
    """

    subject = (
        "Your room booking has been submitted successfully"
    )

    room_number = (
        booking.room.room_number
    )

    room_type = (
        booking.room.room_type.name
    )

    message = (
        f"Hello {booking.full_name},\n\n"
        "Your room booking has been submitted successfully.\n\n"
        f"Room: {room_number}\n"
        f"Room type: {room_type}\n"
        f"Check-in time: {booking.check_in_at}\n"
        f"Check-out time: {booking.check_out_at}\n"
        f"Total price: {booking.total_price}\n"
        f"Booking status: {booking.get_status_display()}\n\n"
        "The hotel receptionist will review and confirm "
        "your booking request.\n\n"
        "Hotel Management System"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[
            booking.email,
        ],
        fail_silently=False,
    )


# ============================================================
# BOOKING CONFLICT HELPERS
# HÀM KIỂM TRA TRÙNG BOOKING
# ============================================================

def staff_booking_conflict_exists(
    room,
    check_in_at,
    check_out_at,
):
    """
    Check overlap against staff Booking date ranges.
    Kiểm tra overlap với khoảng ngày của Booking staff.
    """

    # Staff Booking stores dates rather than exact datetimes.
    # Booking staff lưu date thay vì datetime chính xác.
    start_date = (
        check_in_at.date()
    )

    end_date = (
        check_out_at.date()
    )

    # A CustomerBooking that starts and ends on the same
    # calendar date must still occupy one booking day when
    # compared with the date-based staff Booking model.
    #
    # CustomerBooking check-in và check-out cùng ngày vẫn phải
    # được tính là một ngày khi so với Booking staff dạng date.
    if end_date <= start_date:
        end_date = (
            start_date
            + timedelta(days=1)
        )

    return (
        Booking.objects
        .filter(
            room=room,
            status__in=(
                Booking.ACTIVE_BOOKING_STATUSES
            ),
            check_in_date__lt=end_date,
            check_out_date__gt=start_date,
        )
        .exists()
    )


def portal_booking_conflict_exists(
    room,
    check_in_at,
    check_out_at,
):
    """
    Check overlap against Customer Portal bookings.
    Kiểm tra overlap với CustomerBooking.
    """

    return (
        CustomerBooking.objects
        .filter(
            room=room,
            status__in=(
                CustomerBooking.ACTIVE_BOOKING_STATUSES
            ),
            check_in_at__lt=check_out_at,
            check_out_at__gt=check_in_at,
        )
        .exists()
    )


# ============================================================
# CUSTOMER REGISTRATION
# ĐĂNG KÝ CUSTOMER
# ============================================================

def customer_register(request):
    """
    Register a new Customer Portal account.
    Đăng ký tài khoản Customer Portal mới.
    """

    # Redirect authenticated users to their correct area.
    # Chuyển user đã đăng nhập về đúng khu vực.
    if request.user.is_authenticated:

        if hasattr(
            request.user,
            "customer_profile",
        ):
            return redirect(
                "customer_portal:customer_dashboard"
            )

        return redirect(
            "dashboard"
        )

    if request.method == "POST":

        form = CustomerRegistrationForm(
            request.POST
        )

        if form.is_valid():

            # CustomerRegistrationForm creates User and
            # CustomerProfile atomically.
            # CustomerRegistrationForm tạo User và
            # CustomerProfile trong cùng transaction.
            user = form.save()

            try:
                send_customer_registration_email(
                    user
                )

                messages.success(
                    request,
                    "Account created successfully. "
                    "A confirmation email has been sent.",
                )

            except Exception:
                # Registration remains valid when email fails.
                # Tài khoản vẫn hợp lệ nếu gửi email thất bại.
                logger.exception(
                    "Unable to send customer registration email."
                )

                messages.warning(
                    request,
                    "Account created successfully, "
                    "but the email could not be sent.",
                )

            return redirect(
                "customer_portal:customer_login"
            )

    else:

        form = CustomerRegistrationForm()

    return render(
        request,
        "customer_portal/register.html",
        {
            "form": form,
        },
    )


# ============================================================
# CUSTOMER LOGIN
# ĐĂNG NHẬP CUSTOMER
# ============================================================

def customer_login(request):
    """
    Authenticate Customer Portal accounts.
    Xác thực tài khoản Customer Portal.
    """

    # Redirect authenticated users to their correct area.
    # Chuyển user đã đăng nhập về đúng khu vực.
    if request.user.is_authenticated:

        if hasattr(
            request.user,
            "customer_profile",
        ):
            return redirect(
                "customer_portal:customer_dashboard"
            )

        return redirect(
            "dashboard"
        )

    if request.method == "POST":

        form = CustomerLoginForm(
            request.POST
        )

        if form.is_valid():

            identifier = (
                form.cleaned_data[
                    "identifier"
                ].strip()
            )

            password = (
                form.cleaned_data[
                    "password"
                ]
            )

            user = authenticate(
                request,
                username=identifier,
                password=password,
            )

            # Customer Portal accepts only users
            # that own a CustomerProfile.
            # Customer Portal chỉ chấp nhận user
            # có CustomerProfile.
            if (
                user is not None
                and hasattr(
                    user,
                    "customer_profile",
                )
            ):
                login(
                    request,
                    user,
                )

                return redirect(
                    "customer_portal:customer_dashboard"
                )

            messages.error(
                request,
                "Invalid email/phone or password.",
            )

    else:

        form = CustomerLoginForm()

    return render(
        request,
        "customer_portal/login.html",
        {
            "form": form,
        },
    )


# ============================================================
# CUSTOMER LOGOUT
# ĐĂNG XUẤT CUSTOMER
# ============================================================

@require_POST
def customer_logout(request):
    """
    Log out using POST only.
    Đăng xuất và chỉ cho phép phương thức POST.
    """

    logout(
        request
    )

    return redirect(
        "customer_portal:customer_login"
    )


# ============================================================
# CUSTOMER DASHBOARD
# DASHBOARD CUSTOMER
# ============================================================

@customer_required
def customer_dashboard(request):
    """
    Display the Customer Portal dashboard.
    Hiển thị dashboard Customer Portal.
    """

    return render(
        request,
        "customer_portal/dashboard.html",
    )


# ============================================================
# CUSTOMER PROFILE
# HỒ SƠ CUSTOMER
# ============================================================

@customer_required
def customer_profile(request):
    """
    Display and update CustomerProfile.
    Hiển thị và cập nhật CustomerProfile.
    """

    profile = (
        request.user.customer_profile
    )

    if request.method == "POST":

        form = CustomerProfileForm(
            request.POST,
            request.FILES,
            instance=profile,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Your profile has been updated successfully.",
            )

            return redirect(
                "customer_portal:customer_profile"
            )

    else:

        form = CustomerProfileForm(
            instance=profile
        )

    return render(
        request,
        "customer_portal/profile.html",
        {
            "form": form,
        },
    )


# ============================================================
# CUSTOMER ROOM LIST
# DANH SÁCH PHÒNG CHO CUSTOMER
# ============================================================

@customer_required
def customer_room_list(request):
    """
    Display rooms that can participate in the booking workflow.
    Hiển thị phòng có thể tham gia workflow booking.
    """

    # Do not filter by Available/Reserved/Occupied because
    # future availability is determined by booking overlap.
    #
    # Không lọc theo Available/Reserved/Occupied vì
    # availability tương lai được xác định bằng booking overlap.
    #
    # Maintenance is excluded until Admin returns the room
    # to an operational state.
    # Maintenance bị loại cho tới khi Admin đưa phòng
    # trở lại trạng thái vận hành.
    rooms = (
        Room.objects
        .exclude(
            status="maintenance"
        )
        .select_related(
            "room_type"
        )
        .order_by(
            "room_number"
        )
    )

    return render(
        request,
        "customer_portal/room_list.html",
        {
            "rooms": rooms,
        },
    )


# ============================================================
# CUSTOMER ROOM DETAIL
# CHI TIẾT PHÒNG CHO CUSTOMER
# ============================================================

@customer_required
def customer_room_detail(
    request,
    room_id,
):
    """
    Display a room available to the booking workflow.
    Hiển thị phòng có thể tham gia workflow booking.
    """

    room = get_object_or_404(
        Room.objects
        .select_related(
            "room_type"
        )
        .exclude(
            status="maintenance"
        ),
        id=room_id,
    )

    return render(
        request,
        "customer_portal/room_detail.html",
        {
            "room": room,
        },
    )


# ============================================================
# CUSTOMER BOOK ROOM
# CUSTOMER ĐẶT PHÒNG
# ============================================================

@customer_required
def customer_book_room(
    request,
    room_id,
):
    """
    Submit a Customer Portal booking request.
    Gửi booking request từ Customer Portal.
    """

    room = get_object_or_404(
        Room.objects
        .select_related(
            "room_type"
        )
        .exclude(
            status="maintenance"
        ),
        id=room_id,
    )

    profile = (
        request.user.customer_profile
    )

    initial_data = {
        "full_name": profile.full_name,
        "email": request.user.email,
        "phone": profile.phone,
        "identity_number": (
            profile.identity_number
        ),
        "address": profile.address,
    }

    if request.method == "POST":

        form = CustomerBookingForm(
            request.POST,
            request.FILES,
            room=room,
            profile=profile,
        )

        if form.is_valid():

            try:
                with transaction.atomic():

                    # Request a row lock where supported.
                    # Yêu cầu khóa row nếu database hỗ trợ.
                    locked_room = (
                        Room.objects
                        .select_for_update()
                        .select_related(
                            "room_type"
                        )
                        .get(
                            pk=room.pk
                        )
                    )

                    # Re-check Maintenance after obtaining
                    # the current room record.
                    # Kiểm tra lại Maintenance sau khi lấy
                    # bản ghi phòng hiện tại.
                    if (
                        locked_room.status
                        == "maintenance"
                    ):
                        messages.error(
                            request,
                            "This room is currently unavailable "
                            "for booking.",
                        )

                        return redirect(
                            "customer_portal:customer_room_list"
                        )

                    check_in_at = (
                        form.cleaned_data[
                            "check_in_at"
                        ]
                    )

                    check_out_at = (
                        form.cleaned_data[
                            "check_out_at"
                        ]
                    )

                    # Re-check both booking domains inside
                    # the transaction before saving.
                    # Kiểm tra lại cả hai loại booking bên trong
                    # transaction trước khi lưu.
                    staff_conflict = (
                        staff_booking_conflict_exists(
                            locked_room,
                            check_in_at,
                            check_out_at,
                        )
                    )

                    online_conflict = (
                        portal_booking_conflict_exists(
                            locked_room,
                            check_in_at,
                            check_out_at,
                        )
                    )

                    if (
                        staff_conflict
                        or online_conflict
                    ):
                        messages.error(
                            request,
                            "This room has just been booked "
                            "for the selected period. "
                            "Please choose another room or time.",
                        )

                        return redirect(
                            "customer_portal:customer_room_detail",
                            room_id=room.id,
                        )

                    booking = (
                        form.save(
                            commit=False
                        )
                    )

                    booking.customer_user = (
                        request.user
                    )

                    booking.room = (
                        locked_room
                    )

                    # Reuse the profile ID image when the customer
                    # does not upload a booking-specific image.
                    # Dùng ID image trong profile khi customer
                    # không upload ảnh riêng cho booking.
                    if (
                        not booking.id_document_image
                        and profile.id_document_image
                    ):
                        booking.id_document_image = (
                            profile.id_document_image
                        )

                    # Reuse the profile selfie as the Face Verification
                    # reference when no new selfie is supplied.
                    # Dùng selfie profile làm ảnh tham chiếu
                    # Face Verification khi không có selfie mới.
                    if (
                        not booking.selfie_image
                        and profile.selfie_image
                    ):
                        booking.selfie_image = (
                            profile.selfie_image
                        )

                    booking.save()

                    # A Pending booking that includes today should
                    # immediately affect the current Reserved status.
                    # Booking Pending chứa hôm nay phải lập tức ảnh hưởng
                    # trạng thái Reserved hiện tại của phòng.
                    refresh_room_status(
                        locked_room
                    )

            except Exception:
                # Keep technical details in server logs only.
                # Chỉ lưu chi tiết lỗi kỹ thuật trong server log.
                logger.exception(
                    "Unable to create Customer Portal booking."
                )

                messages.error(
                    request,
                    "Unable to create the booking. "
                    "Please try again.",
                )

            else:
                try:
                    send_customer_booking_email(
                        booking
                    )

                    messages.success(
                        request,
                        "Your booking has been submitted successfully. "
                        "A confirmation email has been sent.",
                    )

                except Exception:
                    # Booking remains valid if email notification fails.
                    # Booking vẫn hợp lệ nếu gửi email thông báo thất bại.
                    logger.exception(
                        "Unable to send Customer Portal booking email."
                    )

                    messages.warning(
                        request,
                        "Your booking has been submitted successfully, "
                        "but the email could not be sent.",
                    )

                return redirect(
                    "customer_portal:customer_my_bookings"
                )

    else:

        form = CustomerBookingForm(
            initial=initial_data,
            room=room,
            profile=profile,
        )

    return render(
        request,
        "customer_portal/booking_form.html",
        {
            "form": form,
            "room": room,
        },
    )


# ============================================================
# CUSTOMER BOOKING HISTORY
# LỊCH SỬ BOOKING CUSTOMER
# ============================================================

@customer_required
def customer_my_bookings(request):
    """
    Display bookings owned by the logged-in customer.
    Hiển thị booking thuộc customer đang đăng nhập.
    """

    bookings = (
        CustomerBooking.objects
        .filter(
            customer_user=request.user
        )
        .select_related(
            "room",
            "room__room_type",
        )
        .order_by(
            "-created_at"
        )
    )

    return render(
        request,
        "customer_portal/my_bookings.html",
        {
            "bookings": bookings,
        },
    )