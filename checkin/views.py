import logging

from django.contrib import messages
from django.db import transaction
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone

from accounts.decorators import group_required
from bookings.models import Booking
from customer_portal.models import CustomerBooking

from .face_utils import (
    base64_to_content_file,
    verify_customer_face,
)
from .forms import (
    FaceCheckInForm,
    OnlineFaceCheckInForm,
)
from .models import (
    CheckIn,
    OnlineCheckIn,
)


logger = logging.getLogger(__name__)


def get_current_face_image(form):
    """
    Get the current face image from upload or camera capture.
    Lấy ảnh khuôn mặt hiện tại từ upload hoặc camera.
    """

    uploaded_image = form.cleaned_data.get(
        "checkin_image"
    )

    captured_image_data = form.cleaned_data.get(
        "captured_image"
    )

    # Prefer an uploaded image when both sources are present.
    # Ưu tiên ảnh upload nếu đồng thời có cả hai nguồn ảnh.
    if uploaded_image:
        return uploaded_image

    if captured_image_data:
        return base64_to_content_file(
            captured_image_data
        )

    raise ValueError(
        "No current face image was provided."
    )


# ============================================================
# STAFF FACE CHECK-IN
# FACE CHECK-IN CHO BOOKING STAFF
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def face_checkin_view(request):

    if request.method == "POST":

        form = FaceCheckInForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            booking = form.cleaned_data[
                "booking"
            ]

            customer = booking.customer

            # Prefer the customer's selfie and fall back
            # to the legacy face image.
            # Ưu tiên selfie của customer và fallback
            # sang face_image cũ.
            registered_image = (
                customer.get_reference_face()
            )

            if not registered_image:

                messages.error(
                    request,
                    "This customer does not have "
                    "a registered face image.",
                )

                return redirect(
                    "face_checkin"
                )

            try:
                # Get the current image from upload or camera.
                # Lấy ảnh hiện tại từ upload hoặc camera.
                current_image = (
                    get_current_face_image(
                        form
                    )
                )

                registered_image_path = (
                    registered_image.path
                )

                # Perform face verification with DeepFace.
                # Thực hiện xác minh khuôn mặt bằng DeepFace.
                result = verify_customer_face(
                    registered_image_path,
                    current_image,
                )

                if not result["verified"]:

                    messages.error(
                        request,
                        "Face verification failed. "
                        "The current face does not match "
                        "the registered customer.",
                    )

                    return render(
                        request,
                        "checkin/face_checkin.html",
                        {
                            "form": form
                        },
                    )

                # Reset the file pointer before saving the image.
                # Đưa con trỏ file về đầu trước khi lưu ảnh.
                current_image.seek(0)

                with transaction.atomic():

                    # Lock the booking before changing check-in state.
                    # Khóa booking trước khi thay đổi trạng thái check-in.
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

                    # Re-check status after face verification.
                    # Kiểm tra lại trạng thái sau khi xác minh khuôn mặt.
                    if (
                        locked_booking.status
                        != Booking.STATUS_CONFIRMED
                    ):

                        messages.error(
                            request,
                            "This booking is no longer "
                            "available for check-in.",
                        )

                        return redirect(
                            "face_checkin"
                        )

                    # Re-check the valid stay period because data
                    # may have changed while face verification ran.
                    # Kiểm tra lại thời gian hợp lệ vì dữ liệu
                    # có thể thay đổi trong lúc DeepFace xử lý.
                    today = timezone.localdate()

                    if not (
                        locked_booking.check_in_date
                        <= today
                        < locked_booking.check_out_date
                    ):

                        messages.error(
                            request,
                            "This booking is outside its valid "
                            "check-in period.",
                        )

                        return redirect(
                            "face_checkin"
                        )

                    room = locked_booking.room

                    # Do not check a guest into a room that is
                    # unavailable for operational reasons.
                    # Không check-in khách vào phòng đang không
                    # sẵn sàng vì lý do vận hành.
                    if room.status in [
                        "maintenance",
                        "cleaning",
                    ]:

                        messages.error(
                            request,
                            "This room is currently unavailable "
                            "for check-in because it is under "
                            "maintenance or cleaning.",
                        )

                        return redirect(
                            "face_checkin"
                        )

                    # Create a durable face check-in audit record.
                    # Tạo bản ghi lịch sử Face Check-in lâu dài.
                    checkin, _ = (
                        CheckIn.objects
                        .update_or_create(
                            booking=locked_booking,
                            defaults={
                                "customer": (
                                    locked_booking.customer
                                ),
                                "method": (
                                    "face_verification"
                                ),
                                "face_verified": True,
                                "manual_verified": False,
                                "verified_image": (
                                    current_image
                                ),
                                "staff": request.user,
                            },
                        )
                    )

                    # Only this Face Check-in workflow may move
                    # a confirmed booking to checked_in.
                    # Chỉ workflow Face Check-in này mới chuyển
                    # Confirmed thành Checked In.
                    locked_booking.status = (
                        Booking.STATUS_CHECKED_IN
                    )

                    locked_booking.save(
                        update_fields=[
                            "status"
                        ]
                    )

                    # A successfully checked-in guest physically
                    # occupies the room.
                    # Khách check-in thành công sẽ chiếm phòng vật lý.
                    if room.status != "occupied":

                        room.status = "occupied"

                        room.save(
                            update_fields=[
                                "status"
                            ]
                        )

                messages.success(
                    request,
                    "Face verified successfully. "
                    f"{locked_booking.customer.full_name} checked in.",
                )

                return redirect(
                    "checkin_success",
                    checkin_id=checkin.id,
                )

            except Exception:
                # Keep technical DeepFace/file errors in server logs.
                # Chỉ ghi lỗi kỹ thuật DeepFace/file vào server log.
                logger.exception(
                    "Staff face check-in failed."
                )

                messages.error(
                    request,
                    "Face verification could not be completed. "
                    "Please check the image and try again.",
                )

    else:

        form = FaceCheckInForm()

    return render(
        request,
        "checkin/face_checkin.html",
        {
            "form": form
        },
    )


# ============================================================
# STAFF CHECK-IN SUCCESS
# TRANG THÀNH CÔNG CHECK-IN STAFF
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def checkin_success_view(
    request,
    checkin_id,
):

    checkin = get_object_or_404(
        CheckIn.objects
        .select_related(
            "booking",
            "customer",
            "booking__room",
            "booking__room__room_type",
            "staff",
        ),
        id=checkin_id,
    )

    return render(
        request,
        "checkin/checkin_success.html",
        {
            "checkin": checkin
        },
    )


# ============================================================
# CHECK-IN HISTORY
# LỊCH SỬ CHECK-IN
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def checkin_history_view(request):

    # Staff/legacy Booking check-in history.
    # Lịch sử check-in của Booking staff/legacy.
    checkins = (
        CheckIn.objects
        .select_related(
            "booking",
            "customer",
            "booking__room",
            "booking__room__room_type",
            "staff",
        )
        .order_by(
            "-check_in_time"
        )
    )

    # Customer Portal booking check-in history.
    # Lịch sử check-in của Customer Portal.
    online_checkins = (
        OnlineCheckIn.objects
        .select_related(
            "booking",
            "booking__customer_user",
            "booking__room",
            "booking__room__room_type",
            "staff",
        )
        .order_by(
            "-check_in_time"
        )
    )

    return render(
        request,
        "checkin/checkin_history.html",
        {
            "checkins": checkins,
            "online_checkins": online_checkins,
        },
    )


# ============================================================
# CUSTOMER PORTAL ONLINE FACE CHECK-IN
# ONLINE FACE CHECK-IN CUSTOMER PORTAL
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def online_face_checkin_view(request):

    if request.method == "POST":

        form = OnlineFaceCheckInForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            booking = form.cleaned_data[
                "booking"
            ]

            # Prefer the selfie saved with this booking.
            # Ưu tiên selfie được lưu riêng với booking này.
            registered_image = (
                booking.selfie_image
            )

            # Fall back to the selfie stored in CustomerProfile.
            # Nếu booking không có selfie thì dùng selfie trong profile.
            if not registered_image:

                customer_profile = getattr(
                    booking.customer_user,
                    "customer_profile",
                    None,
                )

                if (
                    customer_profile
                    and customer_profile.selfie_image
                ):
                    registered_image = (
                        customer_profile.selfie_image
                    )

            if not registered_image:

                messages.error(
                    request,
                    "This customer does not have "
                    "a registered selfie image. "
                    "Please upload a selfie when booking "
                    "or update the customer profile.",
                )

                return redirect(
                    "online_face_checkin"
                )

            try:
                # Get the current face image.
                # Lấy ảnh khuôn mặt hiện tại.
                current_image = (
                    get_current_face_image(
                        form
                    )
                )

                registered_image_path = (
                    registered_image.path
                )

                # Compare the registered reference selfie
                # with the current face.
                # So sánh selfie tham chiếu với khuôn mặt hiện tại.
                result = verify_customer_face(
                    registered_image_path,
                    current_image,
                )

                if not result["verified"]:

                    messages.error(
                        request,
                        "Face verification failed. "
                        "The current face does not match "
                        "the registered customer selfie.",
                    )

                    return render(
                        request,
                        "checkin/online_face_checkin.html",
                        {
                            "form": form
                        },
                    )

                # Reset the file pointer before storing the image.
                # Đưa con trỏ file về đầu trước khi lưu ảnh.
                current_image.seek(0)

                with transaction.atomic():

                    # Lock the CustomerBooking before state transition.
                    # Khóa CustomerBooking trước khi đổi trạng thái.
                    locked_booking = (
                        CustomerBooking.objects
                        .select_for_update()
                        .select_related(
                            "customer_user",
                            "customer_user__customer_profile",
                            "room",
                            "room__room_type",
                        )
                        .get(
                            pk=booking.pk
                        )
                    )

                    # Only Confirmed bookings may enter check-in.
                    # Chỉ booking Confirmed mới được check-in.
                    if (
                        locked_booking.status
                        != CustomerBooking.STATUS_CONFIRMED
                    ):

                        messages.error(
                            request,
                            "This booking is no longer "
                            "available for check-in.",
                        )

                        return redirect(
                            "online_face_checkin"
                        )

                    # Re-check the booking's datetime window.
                    # Kiểm tra lại khoảng thời gian booking.
                    now = timezone.now()

                    if not (
                        locked_booking.check_in_at
                        <= now
                        < locked_booking.check_out_at
                    ):

                        messages.error(
                            request,
                            "This booking is outside its valid "
                            "check-in period.",
                        )

                        return redirect(
                            "online_face_checkin"
                        )

                    room = locked_booking.room

                    # Do not overwrite maintenance/cleaning state.
                    # Không ghi đè trạng thái maintenance/cleaning.
                    if room.status in [
                        "maintenance",
                        "cleaning",
                    ]:

                        messages.error(
                            request,
                            "This room is currently unavailable "
                            "for check-in because it is under "
                            "maintenance or cleaning.",
                        )

                        return redirect(
                            "online_face_checkin"
                        )

                    # Persist the Online Face Check-in record.
                    # Lưu bản ghi Online Face Check-in.
                    online_checkin, _ = (
                        OnlineCheckIn.objects
                        .update_or_create(
                            booking=locked_booking,
                            defaults={
                                "method": (
                                    "face_verification"
                                ),
                                "face_verified": True,
                                "verified_image": (
                                    current_image
                                ),
                                "staff": request.user,
                            },
                        )
                    )

                    # Face verification is the only workflow here
                    # that changes Confirmed to Checked In.
                    # Face verification là workflow duy nhất ở đây
                    # chuyển Confirmed thành Checked In.
                    locked_booking.status = (
                        CustomerBooking.STATUS_CHECKED_IN
                    )

                    locked_booking.save(
                        update_fields=[
                            "status"
                        ]
                    )

                    # Mark the physical room as occupied.
                    # Đánh dấu phòng vật lý là occupied.
                    if room.status != "occupied":

                        room.status = "occupied"

                        room.save(
                            update_fields=[
                                "status"
                            ]
                        )

                messages.success(
                    request,
                    "Face verified successfully. "
                    f"{locked_booking.full_name} checked in.",
                )

                return redirect(
                    "online_checkin_success",
                    booking_id=locked_booking.id,
                )

            except Exception:
                # Do not expose DeepFace or filesystem errors to staff.
                # Không hiển thị lỗi DeepFace/filesystem kỹ thuật ra giao diện.
                logger.exception(
                    "Customer Portal face check-in failed."
                )

                messages.error(
                    request,
                    "Face verification could not be completed. "
                    "Please check the image and try again.",
                )

    else:

        form = OnlineFaceCheckInForm()

    return render(
        request,
        "checkin/online_face_checkin.html",
        {
            "form": form
        },
    )


# ============================================================
# ONLINE CHECK-IN SUCCESS
# TRANG THÀNH CÔNG ONLINE CHECK-IN
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def online_checkin_success_view(
    request,
    booking_id,
):

    # Require a durable OnlineCheckIn record rather than
    # trusting CustomerBooking.status alone.
    # Yêu cầu bản ghi OnlineCheckIn thực sự thay vì chỉ
    # tin vào CustomerBooking.status.
    online_checkin = get_object_or_404(
        OnlineCheckIn.objects
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
        online_checkin.booking
    )

    return render(
        request,
        "checkin/online_checkin_success.html",
        {
            "booking": booking,
            "online_checkin": online_checkin,
        },
    )