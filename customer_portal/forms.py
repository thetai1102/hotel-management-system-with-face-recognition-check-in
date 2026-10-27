from datetime import timedelta
from pathlib import Path

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from bookings.models import Booking

from .models import (
    CustomerBooking,
    CustomerProfile,
)


# ============================================================
# IMAGE VALIDATION
# KIỂM TRA ẢNH
# ============================================================

ALLOWED_FACE_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
}


def validate_face_reference_image(
    image,
    field_label,
):
    """
    Validate image format used as a face reference.
    Kiểm tra định dạng ảnh dùng làm ảnh tham chiếu khuôn mặt.
    """

    if not image:
        return image

    image_name = getattr(
        image,
        "name",
        "",
    )

    if not image_name:
        return image

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
            f"{field_label} must be a JPG, JPEG, or PNG image."
        )

    return image


# ============================================================
# CUSTOMER REGISTRATION
# ĐĂNG KÝ CUSTOMER
# ============================================================

class CustomerRegistrationForm(forms.Form):

    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
            }
        ),
    )

    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
            }
        ),
    )

    phone = forms.CharField(
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
            }
        ),
    )

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
            }
        ),
    )

    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
            }
        ),
    )

    def clean_full_name(self):
        """
        Normalize customer full name.
        Chuẩn hóa họ tên customer.
        """

        full_name = (
            self.cleaned_data[
                "full_name"
            ]
            .strip()
        )

        if not full_name:
            raise forms.ValidationError(
                "Full name is required."
            )

        return full_name

    def clean_email(self):
        """
        Normalize email and protect customer username uniqueness.
        Chuẩn hóa email và bảo vệ tính duy nhất của username customer.
        """

        email = (
            self.cleaned_data[
                "email"
            ]
            .strip()
            .lower()
        )

        User = get_user_model()

        # Customer username is the normalized email,
        # therefore both username and email must be checked.
        # Username customer chính là email chuẩn hóa,
        # nên cần kiểm tra cả username và email.
        duplicate_user = (
            User.objects
            .filter(
                Q(email__iexact=email)
                | Q(username__iexact=email)
            )
            .exists()
        )

        if duplicate_user:
            raise forms.ValidationError(
                "This email is already registered."
            )

        return email

    def clean_phone(self):
        """
        Normalize and validate customer phone.
        Chuẩn hóa và kiểm tra số điện thoại customer.
        """

        phone = (
            self.cleaned_data[
                "phone"
            ]
            .strip()
        )

        if not phone:
            raise forms.ValidationError(
                "Phone number is required."
            )

        if (
            CustomerProfile.objects
            .filter(
                phone__iexact=phone
            )
            .exists()
        ):
            raise forms.ValidationError(
                "This phone number is already registered."
            )

        return phone

    def clean(self):
        """
        Validate matching and secure passwords.
        Kiểm tra hai mật khẩu và password validator.
        """

        cleaned_data = (
            super().clean()
        )

        password1 = (
            cleaned_data.get(
                "password1"
            )
        )

        password2 = (
            cleaned_data.get(
                "password2"
            )
        )

        if (
            password1
            and password2
        ):
            if password1 != password2:
                raise forms.ValidationError(
                    "Passwords do not match."
                )

            # Apply Django password validators.
            # Áp dụng bộ kiểm tra mật khẩu của Django.
            validate_password(
                password1
            )

        return cleaned_data

    def save(self):
        """
        Create User and CustomerProfile atomically.
        Tạo User và CustomerProfile trong cùng transaction.
        """

        User = get_user_model()

        email = (
            self.cleaned_data[
                "email"
            ]
        )

        full_name = (
            self.cleaned_data[
                "full_name"
            ]
        )

        phone = (
            self.cleaned_data[
                "phone"
            ]
        )

        password = (
            self.cleaned_data[
                "password1"
            ]
        )

        # User and profile must either both succeed or both roll back.
        # User và profile phải cùng thành công hoặc cùng rollback.
        with transaction.atomic():

            user = (
                User.objects
                .create_user(
                    username=email,
                    email=email,
                    password=password,
                )
            )

            CustomerProfile.objects.create(
                user=user,
                full_name=full_name,
                phone=phone,
            )

        return user


# ============================================================
# CUSTOMER LOGIN
# ĐĂNG NHẬP CUSTOMER
# ============================================================

class CustomerLoginForm(forms.Form):

    identifier = forms.CharField(
        label="Email or phone number",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
            }
        ),
    )

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
            }
        ),
    )


# ============================================================
# CUSTOMER PROFILE
# HỒ SƠ CUSTOMER
# ============================================================

class CustomerProfileForm(forms.ModelForm):

    class Meta:
        model = CustomerProfile

        fields = [
            "full_name",
            "phone",
            "identity_number",
            "address",
            "id_document_image",
            "selfie_image",
        ]

        widgets = {
            "full_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "identity_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),

            "id_document_image": (
                forms.ClearableFileInput(
                    attrs={
                        "class": "form-control",
                        "accept": "image/*",
                    }
                )
            ),

            "selfie_image": (
                forms.ClearableFileInput(
                    attrs={
                        "class": "form-control",
                        "accept": (
                            ".jpg,.jpeg,.png,"
                            "image/jpeg,image/png"
                        ),
                    }
                )
            ),
        }

    def clean_full_name(self):
        """
        Normalize profile full name.
        Chuẩn hóa họ tên trong profile.
        """

        full_name = (
            self.cleaned_data[
                "full_name"
            ]
            .strip()
        )

        if not full_name:
            raise forms.ValidationError(
                "Full name is required."
            )

        return full_name

    def clean_phone(self):
        """
        Normalize and validate unique profile phone.
        Chuẩn hóa và kiểm tra phone duy nhất trong profile.
        """

        phone = (
            self.cleaned_data[
                "phone"
            ]
            .strip()
        )

        duplicate = (
            CustomerProfile.objects
            .filter(
                phone__iexact=phone
            )
            .exclude(
                pk=self.instance.pk
            )
            .exists()
        )

        if duplicate:
            raise forms.ValidationError(
                "This phone number is already registered."
            )

        return phone

    def clean_identity_number(self):
        """
        Normalize optional identity number and detect duplicates.
        Chuẩn hóa số giấy tờ tùy chọn và kiểm tra trùng.
        """

        identity_number = (
            self.cleaned_data.get(
                "identity_number",
                "",
            )
            .strip()
            .upper()
        )

        if not identity_number:
            return ""

        duplicate = (
            CustomerProfile.objects
            .filter(
                identity_number__iexact=identity_number
            )
            .exclude(
                pk=self.instance.pk
            )
            .exists()
        )

        if duplicate:
            raise forms.ValidationError(
                "This identity number is already used "
                "by another customer profile."
            )

        return identity_number

    def clean_selfie_image(self):
        """
        Validate the profile selfie used for Face Verification.
        Kiểm tra selfie profile dùng cho Face Verification.
        """

        selfie_image = (
            self.cleaned_data.get(
                "selfie_image"
            )
        )

        return validate_face_reference_image(
            selfie_image,
            "Selfie image",
        )


# ============================================================
# CUSTOMER BOOKING
# BOOKING CUSTOMER PORTAL
# ============================================================

class CustomerBookingForm(forms.ModelForm):

    class Meta:
        model = CustomerBooking

        fields = [
            "full_name",
            "email",
            "phone",
            "identity_number",
            "address",
            "check_in_at",
            "check_out_at",
            "id_document_image",
            "selfie_image",
            "note",
        ]

        widgets = {
            "full_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "identity_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "check_in_at": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "form-control",
                },
                format="%Y-%m-%dT%H:%M",
            ),

            "check_out_at": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "form-control",
                },
                format="%Y-%m-%dT%H:%M",
            ),

            "address": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": "form-control",
                }
            ),

            "id_document_image": (
                forms.ClearableFileInput(
                    attrs={
                        "class": "form-control",
                        "accept": "image/*",
                    }
                )
            ),

            "selfie_image": (
                forms.ClearableFileInput(
                    attrs={
                        "class": "form-control",
                        "accept": (
                            ".jpg,.jpeg,.png,"
                            "image/jpeg,image/png"
                        ),
                    }
                )
            ),

            "note": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": "form-control",
                }
            ),
        }

    def __init__(
        self,
        *args,
        room=None,
        profile=None,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        # When editing, use the booking's existing room if the
        # caller did not explicitly provide one.
        # Khi edit, dùng room hiện có nếu caller không truyền room.
        if (
            room is None
            and self.instance
            and self.instance.pk
        ):
            room = self.instance.room

        self.room = room
        self.profile = profile

        self.fields[
            "check_in_at"
        ].input_formats = [
            "%Y-%m-%dT%H:%M",
        ]

        self.fields[
            "check_out_at"
        ].input_formats = [
            "%Y-%m-%dT%H:%M",
        ]

        existing_id_image = bool(
            self.instance
            and self.instance.pk
            and self.instance.id_document_image
        )

        existing_selfie = bool(
            self.instance
            and self.instance.pk
            and self.instance.selfie_image
        )

        # Require an ID image only when neither the profile nor
        # the existing booking already provides one.
        # Chỉ bắt buộc ID image khi cả profile và booking hiện tại
        # đều chưa có ảnh.
        self.fields[
            "id_document_image"
        ].required = not (
            (
                profile
                and profile.id_document_image
            )
            or existing_id_image
        )

        # Require a selfie only when neither the profile nor
        # the existing booking already provides one.
        # Chỉ bắt buộc selfie khi cả profile và booking hiện tại
        # đều chưa có selfie.
        self.fields[
            "selfie_image"
        ].required = not (
            (
                profile
                and profile.selfie_image
            )
            or existing_selfie
        )

    def clean_full_name(self):
        """
        Normalize booking customer name snapshot.
        Chuẩn hóa snapshot họ tên trong booking.
        """

        full_name = (
            self.cleaned_data[
                "full_name"
            ]
            .strip()
        )

        if not full_name:
            raise forms.ValidationError(
                "Full name is required."
            )

        return full_name

    def clean_email(self):
        """
        Normalize booking email snapshot.
        Chuẩn hóa snapshot email của booking.
        """

        return (
            self.cleaned_data[
                "email"
            ]
            .strip()
            .lower()
        )

    def clean_phone(self):
        """
        Normalize booking phone snapshot.
        Chuẩn hóa snapshot phone của booking.
        """

        phone = (
            self.cleaned_data[
                "phone"
            ]
            .strip()
        )

        if not phone:
            raise forms.ValidationError(
                "Phone number is required."
            )

        return phone

    def clean_identity_number(self):
        """
        Normalize booking identity snapshot.
        Chuẩn hóa snapshot số giấy tờ của booking.
        """

        identity_number = (
            self.cleaned_data.get(
                "identity_number",
                "",
            )
            .strip()
            .upper()
        )

        return identity_number

    def clean_selfie_image(self):
        """
        Validate booking selfie used for Face Verification.
        Kiểm tra selfie booking dùng cho Face Verification.
        """

        selfie_image = (
            self.cleaned_data.get(
                "selfie_image"
            )
        )

        return validate_face_reference_image(
            selfie_image,
            "Selfie image",
        )

    def clean(self):
        """
        Validate booking dates, overlaps, and required images.
        Kiểm tra thời gian, overlap và ảnh bắt buộc của booking.
        """

        cleaned_data = (
            super().clean()
        )

        check_in_at = (
            cleaned_data.get(
                "check_in_at"
            )
        )

        check_out_at = (
            cleaned_data.get(
                "check_out_at"
            )
        )

        if (
            not check_in_at
            or not check_out_at
        ):
            return cleaned_data

        # Check-in cannot be in the past.
        # Thời gian check-in không được nằm trong quá khứ.
        if (
            check_in_at
            < timezone.now()
        ):
            raise forms.ValidationError(
                "Check-in time cannot be in the past."
            )

        # Check-out must be later than check-in.
        # Thời gian check-out phải sau thời gian check-in.
        if (
            check_out_at
            <= check_in_at
        ):
            raise forms.ValidationError(
                "Check-out time must be after check-in time."
            )

        if self.room is None:
            raise forms.ValidationError(
                "A room is required for this booking."
            )

        # ====================================================
        # STAFF BOOKING OVERLAP
        # OVERLAP VỚI BOOKING STAFF
        # ====================================================

        # Staff Booking stores dates rather than exact datetimes.
        # A same-day CustomerBooking still occupies one calendar
        # booking day, so use the following day as the exclusive
        # end when check-in/out fall on the same date.
        #
        # Staff Booking lưu theo date thay vì datetime.
        # CustomerBooking check-in/out cùng ngày vẫn chiếm một ngày,
        # nên dùng ngày kế tiếp làm mốc kết thúc exclusive.
        portal_start_date = (
            check_in_at.date()
        )

        portal_end_date = (
            check_out_at.date()
        )

        if (
            portal_end_date
            <= portal_start_date
        ):
            portal_end_date = (
                portal_start_date
                + timedelta(days=1)
            )

        staff_conflict = (
            Booking.objects
            .filter(
                room=self.room,
                status__in=(
                    Booking.ACTIVE_BOOKING_STATUSES
                ),
                check_in_date__lt=portal_end_date,
                check_out_date__gt=portal_start_date,
            )
            .exists()
        )

        if staff_conflict:
            raise forms.ValidationError(
                "This room is already booked "
                "during the selected period."
            )

        # ====================================================
        # CUSTOMER PORTAL OVERLAP
        # OVERLAP VỚI CUSTOMER PORTAL
        # ====================================================

        online_conflict = (
            CustomerBooking.objects
            .filter(
                room=self.room,
                status__in=(
                    CustomerBooking.ACTIVE_BOOKING_STATUSES
                ),
                check_in_at__lt=check_out_at,
                check_out_at__gt=check_in_at,
            )
        )

        # Exclude the current booking when editing.
        # Bỏ qua chính booking hiện tại khi chỉnh sửa.
        if (
            self.instance
            and self.instance.pk
        ):
            online_conflict = (
                online_conflict.exclude(
                    pk=self.instance.pk
                )
            )

        if online_conflict.exists():
            raise forms.ValidationError(
                "This room is already booked "
                "during the selected period."
            )

        # ====================================================
        # REQUIRED ID IMAGE
        # ẢNH GIẤY TỜ BẮT BUỘC
        # ====================================================

        id_image = (
            cleaned_data.get(
                "id_document_image"
            )
        )

        existing_id_image = bool(
            self.instance
            and self.instance.pk
            and self.instance.id_document_image
        )

        if (
            not id_image
            and not existing_id_image
            and not (
                self.profile
                and self.profile.id_document_image
            )
        ):
            raise forms.ValidationError(
                "Please upload an ID document image."
            )

        # ====================================================
        # REQUIRED SELFIE
        # SELFIE BẮT BUỘC
        # ====================================================

        selfie = (
            cleaned_data.get(
                "selfie_image"
            )
        )

        existing_selfie = bool(
            self.instance
            and self.instance.pk
            and self.instance.selfie_image
        )

        if (
            not selfie
            and not existing_selfie
            and not (
                self.profile
                and self.profile.selfie_image
            )
        ):
            raise forms.ValidationError(
                "Please upload a selfie image."
            )

        return cleaned_data