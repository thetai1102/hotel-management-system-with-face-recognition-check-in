from django import forms

from .models import (
    Room,
    RoomType,
)


class RoomTypeForm(forms.ModelForm):
    class Meta:
        model = RoomType

        fields = [
            "name",
            "description",
            "price_per_night",
            "capacity",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter room type name",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Enter description",
                }
            ),
            "price_per_night": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter price per night",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "capacity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter capacity",
                    "min": "1",
                }
            ),
        }

    def clean_name(self):
        """
        Normalize room type name.
        Chuẩn hóa tên loại phòng.
        """

        name = self.cleaned_data[
            "name"
        ].strip()

        if not name:
            raise forms.ValidationError(
                "Room type name is required."
            )

        return name

    def clean_price_per_night(self):
        """
        Require a positive room price.
        Yêu cầu giá phòng phải lớn hơn 0.
        """

        price = self.cleaned_data[
            "price_per_night"
        ]

        if price <= 0:
            raise forms.ValidationError(
                "Price per night must be greater than 0."
            )

        return price

    def clean_capacity(self):
        """
        Require at least one guest capacity.
        Yêu cầu sức chứa tối thiểu là một khách.
        """

        capacity = self.cleaned_data[
            "capacity"
        ]

        if capacity <= 0:
            raise forms.ValidationError(
                "Capacity must be at least 1."
            )

        return capacity


class RoomForm(forms.ModelForm):
    # Reserved and Occupied are controlled by booking/check-in flows.
    # Reserved và Occupied được quản lý bởi workflow booking/check-in.
    SYSTEM_MANAGED_STATUSES = {
        "reserved",
        "occupied",
    }

    class Meta:
        model = Room

        fields = [
            "room_number",
            "room_type",
            "floor",
            "status",
        ]

        widgets = {
            "room_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter room number",
                }
            ),
            "room_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "floor": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter floor",
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        # Admin may manually manage only operational statuses.
        # Admin chỉ được quản lý thủ công các trạng thái vận hành.
        manual_status_choices = [
            choice
            for choice in Room.ROOM_STATUS
            if choice[0]
            not in self.SYSTEM_MANAGED_STATUSES
        ]

        current_status = (
            self.instance.status
            if self.instance
            and self.instance.pk
            else None
        )

        if (
            current_status
            in self.SYSTEM_MANAGED_STATUSES
        ):
            # Keep the current system-managed status visible,
            # but prevent manual modification.
            # Giữ trạng thái do hệ thống quản lý để hiển thị,
            # nhưng không cho chỉnh sửa thủ công.
            current_choice = [
                choice
                for choice in Room.ROOM_STATUS
                if choice[0] == current_status
            ]

            self.fields[
                "status"
            ].choices = current_choice

            self.fields[
                "status"
            ].disabled = True

            self.fields[
                "status"
            ].help_text = (
                "This status is managed automatically by "
                "the booking/check-in workflow."
            )

        else:
            self.fields[
                "status"
            ].choices = manual_status_choices

            self.fields[
                "status"
            ].help_text = (
                "Reserved and Occupied are managed "
                "automatically by the system."
            )

    def clean_room_number(self):
        """
        Normalize room number.
        Chuẩn hóa số phòng.
        """

        room_number = self.cleaned_data[
            "room_number"
        ].strip()

        if not room_number:
            raise forms.ValidationError(
                "Room number is required."
            )

        return room_number