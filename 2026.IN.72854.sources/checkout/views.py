from django.contrib import messages
from django.db import transaction
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from accounts.decorators import group_required
from bookings.models import Booking
from bookings.views import refresh_room_status
from customer_portal.models import CustomerBooking

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
# CHECKOUT HISTORY
# LỊCH SỬ CHECKOUT
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def checkout_list(request):
    """
    Display staff and Customer Portal checkout history.
    Hiển thị lịch sử checkout staff và Customer Portal.
    """

    # Load checkout history for Booking records.
    # Lấy lịch sử checkout của Booking.
    checkouts = (
        CheckOut.objects
        .select_related(
            "booking",
            "booking__customer",
            "booking__room",
            "booking__room__room_type",
            "staff",
        )
        .order_by(
            "-check_out_time"
        )
    )

    # Load checkout history for CustomerBooking records.
    # Lấy lịch sử checkout của CustomerBooking.
    online_checkouts = (
        OnlineCheckOut.objects
        .select_related(
            "booking",
            "booking__customer_user",
            "booking__room",
            "booking__room__room_type",
            "staff",
        )
        .order_by(
            "-check_out_time"
        )
    )

    return render(
        request,
        "checkout/checkout_list.html",
        {
            "checkouts": checkouts,
            "online_checkouts": online_checkouts,
        },
    )


# ============================================================
# STAFF BOOKING CHECKOUT
# CHECKOUT BOOKING STAFF
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def checkout_create(request):
    """
    Process payment and checkout for Booking.
    Xử lý thanh toán và checkout cho Booking.
    """

    if request.method == "POST":

        form = CheckoutForm(
            request.POST
        )

        if form.is_valid():

            booking = form.cleaned_data[
                "booking"
            ]

            payment_method = form.cleaned_data[
                "payment_method"
            ]

            payment_status = form.cleaned_data[
                "status"
            ]

            with transaction.atomic():

                # Lock the booking while processing checkout.
                # Khóa booking trong lúc xử lý checkout.
                locked_booking = (
                    Booking.objects
                    .select_for_update()
                    .select_related(
                        "customer",
                        "room",
                        "room__room_type",
                    )
                    .get(
                        pk=booking.pk
                    )
                )

                # Only Checked In bookings may be checked out.
                # Chỉ booking Checked In mới được checkout.
                if (
                    locked_booking.status
                    != Booking.STATUS_CHECKED_IN
                ):

                    messages.error(
                        request,
                        "This booking is no longer "
                        "available for checkout.",
                    )

                    return redirect(
                        "checkout_create"
                    )

                # Prevent duplicate checkout records even if
                # inconsistent data reaches this view.
                # Ngăn checkout trùng kể cả khi dữ liệu
                # không nhất quán đi tới view này.
                if CheckOut.objects.filter(
                    booking=locked_booking
                ).exists():

                    messages.error(
                        request,
                        "This booking has already been checked out.",
                    )

                    return redirect(
                        "checkout_create"
                    )

                # Store every payment attempt permanently.
                # Lưu mọi lần thử thanh toán vào database.
                Payment.objects.create(
                    booking=locked_booking,
                    amount=locked_booking.total_price,
                    payment_method=payment_method,
                    status=payment_status,
                )

                # Failed or unpaid payments must not complete checkout.
                # Thanh toán Failed/Unpaid không được hoàn tất checkout.
                if (
                    payment_status
                    != "paid"
                ):

                    messages.warning(
                        request,
                        "Payment was not completed. "
                        "The customer remains checked in.",
                    )

                    return redirect(
                        "checkout_create"
                    )

                # Create durable checkout history.
                # Tạo bản ghi lịch sử checkout lâu dài.
                checkout = (
                    CheckOut.objects.create(
                        booking=locked_booking,
                        final_amount=(
                            locked_booking.total_price
                        ),
                        staff=request.user,
                    )
                )

                # Move booking from Checked In to Checked Out.
                # Chuyển booking từ Checked In sang Checked Out.
                locked_booking.status = (
                    Booking.STATUS_CHECKED_OUT
                )

                locked_booking.save(
                    update_fields=[
                        "status"
                    ]
                )

                # Recalculate the room's current operational state.
                # Tính lại trạng thái vận hành hiện tại của phòng.
                #
                # Do not blindly force the room to Available because
                # another reservation may be relevant today, or the
                # room may be under maintenance/cleaning.
                #
                # Không ép phòng thành Available vì có thể còn
                # reservation khác trong hôm nay hoặc phòng đang
                # maintenance/cleaning.
                refresh_room_status(
                    locked_booking.room
                )

            messages.success(
                request,
                "Checkout completed successfully.",
            )

            return redirect(
                "invoice_detail",
                checkout_id=checkout.id,
            )

    else:

        form = CheckoutForm()

    return render(
        request,
        "checkout/checkout_form.html",
        {
            "form": form,
        },
    )


# ============================================================
# STAFF INVOICE
# HÓA ĐƠN STAFF
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def invoice_detail(
    request,
    checkout_id,
):
    """
    Display invoice from durable checkout/payment records.
    Hiển thị hóa đơn từ bản ghi checkout/payment trong database.
    """

    checkout = get_object_or_404(
        CheckOut.objects
        .select_related(
            "booking",
            "booking__customer",
            "booking__room",
            "booking__room__room_type",
            "staff",
        ),
        id=checkout_id,
    )

    # Read the successful payment associated with the checkout.
    # Lấy giao dịch Paid thuộc booking đã checkout.
    payment = (
        Payment.objects
        .filter(
            booking=checkout.booking,
            status="paid",
        )
        .order_by(
            "-payment_date"
        )
        .first()
    )

    return render(
        request,
        "checkout/invoice_detail.html",
        {
            "checkout": checkout,
            "payment": payment,
        },
    )


# ============================================================
# CUSTOMER PORTAL CHECKOUT
# CHECKOUT CUSTOMER PORTAL
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def online_checkout_create(request):
    """
    Process payment and checkout for CustomerBooking.
    Xử lý thanh toán và checkout cho CustomerBooking.
    """

    if request.method == "POST":

        form = OnlineCheckoutForm(
            request.POST
        )

        if form.is_valid():

            booking = form.cleaned_data[
                "booking"
            ]

            payment_method = form.cleaned_data[
                "payment_method"
            ]

            payment_status = form.cleaned_data[
                "status"
            ]

            with transaction.atomic():

                # Lock the CustomerBooking during checkout.
                # Khóa CustomerBooking trong lúc checkout.
                locked_booking = (
                    CustomerBooking.objects
                    .select_for_update()
                    .select_related(
                        "customer_user",
                        "room",
                        "room__room_type",
                    )
                    .get(
                        pk=booking.pk
                    )
                )

                # Only Checked In bookings may be checked out.
                # Chỉ CustomerBooking Checked In mới được checkout.
                if (
                    locked_booking.status
                    != CustomerBooking.STATUS_CHECKED_IN
                ):

                    messages.error(
                        request,
                        "This online booking is no longer "
                        "available for checkout.",
                    )

                    return redirect(
                        "online_checkout"
                    )

                # Prevent duplicate OnlineCheckOut records.
                # Ngăn tạo OnlineCheckOut trùng.
                if OnlineCheckOut.objects.filter(
                    booking=locked_booking
                ).exists():

                    messages.error(
                        request,
                        "This online booking has already "
                        "been checked out.",
                    )

                    return redirect(
                        "online_checkout"
                    )

                # Store every online payment attempt.
                # Lưu mọi lần thử thanh toán online.
                OnlinePayment.objects.create(
                    booking=locked_booking,
                    amount=locked_booking.total_price,
                    payment_method=payment_method,
                    status=payment_status,
                )

                # Failed or unpaid payment keeps the guest checked in.
                # Failed/Unpaid giữ customer ở trạng thái Checked In.
                if (
                    payment_status
                    != "paid"
                ):

                    messages.warning(
                        request,
                        "Payment was not completed. "
                        "The customer remains checked in.",
                    )

                    return redirect(
                        "online_checkout"
                    )

                # Create durable OnlineCheckOut history.
                # Tạo lịch sử OnlineCheckOut lâu dài.
                OnlineCheckOut.objects.create(
                    booking=locked_booking,
                    final_amount=(
                        locked_booking.total_price
                    ),
                    staff=request.user,
                )

                # Move CustomerBooking to Checked Out.
                # Chuyển CustomerBooking sang Checked Out.
                locked_booking.status = (
                    CustomerBooking.STATUS_CHECKED_OUT
                )

                locked_booking.save(
                    update_fields=[
                        "status"
                    ]
                )

                # Refresh instead of blindly setting Available.
                # Refresh thay vì ép trực tiếp thành Available.
                refresh_room_status(
                    locked_booking.room
                )

            messages.success(
                request,
                "Online checkout completed successfully.",
            )

            return redirect(
                "online_invoice_detail",
                booking_id=locked_booking.id,
            )

    else:

        form = OnlineCheckoutForm()

    return render(
        request,
        "checkout/online_checkout_form.html",
        {
            "form": form,
        },
    )


# ============================================================
# CUSTOMER PORTAL INVOICE
# HÓA ĐƠN CUSTOMER PORTAL
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def online_invoice_detail(
    request,
    booking_id,
):
    """
    Display Customer Portal invoice from durable database records.
    Hiển thị hóa đơn Customer Portal từ dữ liệu database lâu dài.
    """

    # Require a real OnlineCheckOut record.
    # Yêu cầu bản ghi OnlineCheckOut thực sự tồn tại.
    online_checkout = get_object_or_404(
        OnlineCheckOut.objects
        .select_related(
            "booking",
            "booking__customer_user",
            "booking__room",
            "booking__room__room_type",
            "staff",
        ),
        booking_id=booking_id,
    )

    booking = (
        online_checkout.booking
    )

    # Read the successful payment from the database.
    # Đọc giao dịch thanh toán thành công từ database.
    online_payment = (
        OnlinePayment.objects
        .filter(
            booking=booking,
            status="paid",
        )
        .order_by(
            "-payment_date"
        )
        .first()
    )

    return render(
        request,
        "checkout/online_invoice_detail.html",
        {
            "booking": booking,
            "online_checkout": online_checkout,
            "online_payment": online_payment,
        },
    )