from pathlib import Path

from django import forms
from django.utils import timezone

from bookings.models import Booking
from customer_portal.models import CustomerBooking


# ============================================================
# FACE IMAGE VALIDATION
# KIỂM TRA ẢNH KHUÔN MẶT
# ============================================================

ALLOWED_FACE_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
}


def validate_uploaded_face_image(image):
    """
    Validate an uploaded current-face image.
    Kiểm tra ảnh khuôn mặt hiện tại được upload.
    """

    if not image:
        return image

    image_name = getattr(
        image,
        "name",
        "",
    )

    extension = (
        Path(image_name)
        .suffix
        .lower()
    )

    if (
        extension
        not in ALLOWED_FACE_IMAGE_EXTENSIONS
    ):
        raise forms.ValidationError(
            "Face image must be a JPG, JPEG, or PNG file."
        )

    return image


# ============================================================
# STAFF FACE CHECK-IN FORM
# FORM FACE CHECK-IN CHO BOOKING STAFF
# ============================================================

class FaceCheckInForm(forms.Form):

    booking = forms.ModelChoiceField(
        queryset=Booking.objects.none(),
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
        label="Booking",
    )

    checkin_image = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": (
                    ".jpg,.jpeg,.png,"
                    "image/jpeg,image/png"
                ),
            }
        ),
        label="Upload Face Image",
    )

    captured_image = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        today = (
            timezone.localdate()
        )

        # Only Confirmed staff bookings whose stay includes
        # today may enter the Face Check-in workflow.
        #
        # Chỉ Booking staff Confirmed có khoảng lưu trú
        # bao gồm hôm nay mới được vào workflow Face Check-in.
        self.fields[
            "booking"
        ].queryset = (
            Booking.objects
            .filter(
                status=(
                    Booking.STATUS_CONFIRMED
                ),
                check_in_date__lte=today,
                check_out_date__gt=today,
            )
            .exclude(
                room__status__in=[
                    "maintenance",
                    "cleaning",
                ]
            )
            .select_related(
                "customer",
                "room",
                "room__room_type",
            )
            .order_by(
                "-created_at"
            )
        )

    def clean_checkin_image(self):
        """
        Validate uploaded current-face image format.
        Kiểm tra định dạng ảnh khuôn mặt hiện tại upload.
        """

        image = (
            self.cleaned_data.get(
                "checkin_image"
            )
        )

        return validate_uploaded_face_image(
            image
        )

    def clean(self):
        """
        Validate image source and booking eligibility.
        Kiểm tra nguồn ảnh và điều kiện booking.
        """

        cleaned_data = (
            super().clean()
        )

        checkin_image = (
            cleaned_data.get(
                "checkin_image"
            )
        )

        captured_image = (
            cleaned_data.get(
                "captured_image"
            )
        )

        # Receptionist must provide either an uploaded
        # image or a camera capture.
        #
        # Receptionist phải cung cấp ảnh upload
        # hoặc ảnh được chụp từ camera.
        if (
            not checkin_image
            and not captured_image
        ):
            raise forms.ValidationError(
                "Please upload an image or capture "
                "a face image using the camera."
            )

        booking = (
            cleaned_data.get(
                "booking"
            )
        )

        if not booking:
            return cleaned_data

        today = (
            timezone.localdate()
        )

        # Re-check status because booking data may have changed
        # after the form queryset was initially created.
        #
        # Kiểm tra lại status vì dữ liệu booking có thể thay đổi
        # sau khi queryset của form được tạo.
        if (
            booking.status
            != Booking.STATUS_CONFIRMED
        ):
            raise forms.ValidationError(
                "Only confirmed bookings can be checked in."
            )

        # Do not allow check-in before the booked date.
        # Không cho check-in trước ngày booking.
        if (
            booking.check_in_date
            > today
        ):
            raise forms.ValidationError(
                "This booking is not ready for check-in yet."
            )

        # Do not allow check-in once the stay has expired.
        # Không cho check-in khi khoảng lưu trú đã hết.
        if (
            booking.check_out_date
            <= today
        ):
            raise forms.ValidationError(
                "This booking has already passed "
                "its check-out date."
            )

        # Maintenance and Cleaning are explicit operational
        # states that block check-in.
        #
        # Maintenance và Cleaning là trạng thái vận hành
        # chủ động và không cho phép check-in.
        if (
            booking.room.status
            in [
                "maintenance",
                "cleaning",
            ]
        ):
            raise forms.ValidationError(
                "This room is currently unavailable "
                "for check-in because it is under "
                "maintenance or cleaning."
            )

        return cleaned_data


# ============================================================
# CUSTOMER PORTAL FACE CHECK-IN FORM
# FORM FACE CHECK-IN CUSTOMER PORTAL
# ============================================================

class OnlineFaceCheckInForm(forms.Form):

    booking = forms.ModelChoiceField(
        queryset=CustomerBooking.objects.none(),
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
        label="Online Booking",
    )

    checkin_image = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": (
                    ".jpg,.jpeg,.png,"
                    "image/jpeg,image/png"
                ),
            }
        ),
        label="Upload Current Face Image",
    )

    captured_image = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        now = (
            timezone.now()
        )

        # Only Confirmed CustomerBooking records currently
        # inside their exact datetime stay window are selectable.
        #
        # Chỉ CustomerBooking Confirmed đang nằm trong đúng
        # khoảng datetime lưu trú mới được chọn.
        self.fields[
            "booking"
        ].queryset = (
            CustomerBooking.objects
            .filter(
                status=(
                    CustomerBooking.STATUS_CONFIRMED
                ),
                check_in_at__lte=now,
                check_out_at__gt=now,
            )
            .exclude(
                room__status__in=[
                    "maintenance",
                    "cleaning",
                ]
            )
            .select_related(
                "customer_user",
                "room",
                "room__room_type",
            )
            .order_by(
                "-created_at"
            )
        )

    def clean_checkin_image(self):
        """
        Validate uploaded current-face image format.
        Kiểm tra định dạng ảnh khuôn mặt hiện tại upload.
        """

        image = (
            self.cleaned_data.get(
                "checkin_image"
            )
        )

        return validate_uploaded_face_image(
            image
        )

    def clean(self):
        """
        Validate image source and online booking eligibility.
        Kiểm tra nguồn ảnh và điều kiện CustomerBooking.
        """

        cleaned_data = (
            super().clean()
        )

        checkin_image = (
            cleaned_data.get(
                "checkin_image"
            )
        )

        captured_image = (
            cleaned_data.get(
                "captured_image"
            )
        )

        # Receptionist must provide either uploaded
        # or camera-captured face data.
        #
        # Receptionist phải cung cấp ảnh upload
        # hoặc ảnh khuôn mặt từ camera.
        if (
            not checkin_image
            and not captured_image
        ):
            raise forms.ValidationError(
                "Please upload an image or capture "
                "a face image using the camera."
            )

        booking = (
            cleaned_data.get(
                "booking"
            )
        )

        if not booking:
            return cleaned_data

        now = (
            timezone.now()
        )

        # Re-check the booking state immediately before
        # the Face Verification workflow begins.
        #
        # Kiểm tra lại trạng thái ngay trước khi bắt đầu
        # workflow Face Verification.
        if (
            booking.status
            != CustomerBooking.STATUS_CONFIRMED
        ):
            raise forms.ValidationError(
                "Only confirmed bookings can be checked in."
            )

        # CustomerBooking uses exact datetime scheduling,
        # therefore early check-in is intentionally blocked.
        #
        # CustomerBooking dùng lịch datetime chính xác,
        # nên hiện tại hệ thống chủ động không cho check-in sớm.
        if (
            booking.check_in_at
            > now
        ):
            raise forms.ValidationError(
                "This booking is not ready for check-in yet."
            )

        # Once check_out_at is reached, Face Check-in expires.
        # Khi tới check_out_at thì quyền Face Check-in hết hiệu lực.
        if (
            booking.check_out_at
            <= now
        ):
            raise forms.ValidationError(
                "This booking has already passed "
                "its check-out time."
            )

        # Do not begin Face Verification for a room that
        # is operationally blocked.
        #
        # Không bắt đầu Face Verification cho phòng
        # đang bị khóa vì lý do vận hành.
        if (
            booking.room.status
            in [
                "maintenance",
                "cleaning",
            ]
        ):
            raise forms.ValidationError(
                "This room is currently unavailable "
                "for check-in because it is under "
                "maintenance or cleaning."
            )

        return cleaned_data