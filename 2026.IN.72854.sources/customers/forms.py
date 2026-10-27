from pathlib import Path

from django import forms

from .models import Customer


# Face reference images should use formats supported consistently
# by the current Face Check-in workflow.
# Ảnh tham chiếu khuôn mặt nên dùng định dạng được workflow
# Face Check-in hiện tại hỗ trợ ổn định.
ALLOWED_FACE_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
}


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer

        fields = [
            "full_name",
            "email",
            "phone",
            "id_card_number",
            "address",
            "id_document_image",
            "selfie_image",
            "face_image",
        ]

        widgets = {
            "full_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter full name",
                }
            ),

            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter email",
                }
            ),

            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter phone number",
                }
            ),

            "id_card_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter ID card / passport number",
                }
            ),

            "address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Enter address",
                }
            ),

            "id_document_image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),

            "selfie_image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".jpg,.jpeg,.png,image/jpeg,image/png",
                }
            ),

            "face_image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".jpg,.jpeg,.png,image/jpeg,image/png",
                }
            ),
        }

    def clean_full_name(self):
        """
        Normalize customer full name.
        Chuẩn hóa họ tên customer.
        """

        full_name = self.cleaned_data[
            "full_name"
        ].strip()

        if not full_name:
            raise forms.ValidationError(
                "Full name is required."
            )

        return full_name

    def clean_email(self):
        """
        Normalize optional customer email.
        Chuẩn hóa email tùy chọn của customer.
        """

        email = self.cleaned_data.get(
            "email"
        )

        if not email:
            return None

        return email.strip().lower()

    def clean_phone(self):
        """
        Normalize customer phone number.
        Chuẩn hóa số điện thoại customer.
        """

        phone = self.cleaned_data[
            "phone"
        ].strip()

        if not phone:
            raise forms.ValidationError(
                "Phone number is required."
            )

        return phone

    def clean_id_card_number(self):
        """
        Normalize and validate unique identity number.
        Chuẩn hóa và kiểm tra số giấy tờ không bị trùng.
        """

        id_card_number = (
            self.cleaned_data[
                "id_card_number"
            ]
            .strip()
            .upper()
        )

        if not id_card_number:
            raise forms.ValidationError(
                "ID card / passport number is required."
            )

        # Check uniqueness case-insensitively so values such as
        # "ab123" and "AB123" cannot represent two customers.
        # Kiểm tra không trùng không phân biệt hoa/thường để
        # "ab123" và "AB123" không tạo thành hai customer khác nhau.
        duplicate = (
            Customer.objects
            .filter(
                id_card_number__iexact=id_card_number
            )
            .exclude(
                pk=self.instance.pk
            )
            .exists()
        )

        if duplicate:
            raise forms.ValidationError(
                "A customer with this ID card / "
                "passport number already exists."
            )

        return id_card_number

    def validate_face_image(
        self,
        image,
        field_label,
    ):
        """
        Validate image format used for face recognition.
        Kiểm tra định dạng ảnh dùng cho nhận diện khuôn mặt.
        """

        if not image:
            return image

        # Existing ImageFieldFile objects may not represent
        # a newly uploaded file, so only validate when a name exists.
        # ImageFieldFile hiện có có thể không phải file vừa upload,
        # nên chỉ kiểm tra khi có tên file.
        image_name = getattr(
            image,
            "name",
            ""
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

    def clean_selfie_image(self):
        """
        Validate the preferred reference selfie.
        Kiểm tra selfie tham chiếu ưu tiên.
        """

        image = self.cleaned_data.get(
            "selfie_image"
        )

        return self.validate_face_image(
            image,
            "Selfie image",
        )

    def clean_face_image(self):
        """
        Validate the legacy reference face image.
        Kiểm tra ảnh khuôn mặt tham chiếu cũ.
        """

        image = self.cleaned_data.get(
            "face_image"
        )

        return self.validate_face_image(
            image,
            "Face image",
        )