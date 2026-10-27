from datetime import timedelta

from django import forms
from django.utils import timezone

from customer_portal.models import CustomerBooking
from rooms.models import Room

from .models import Booking


# ============================================================
# DATE CONVERSION HELPER
# HÀM CHUYỂN DATETIME THÀNH NGÀY LOCAL
# ============================================================

def get_local_date(datetime_value):
    """
    Convert a datetime to the hotel's local calendar date.
    Chuyển datetime thành ngày địa phương của khách sạn.
    """

    if timezone.is_aware(
        datetime_value
    ):
        return (
            timezone.localtime(
                datetime_value
            )
            .date()
        )

    return datetime_value.date()


# ============================================================
# BOOKING CONFLICT CHECK
# KIỂM TRA XUNG ĐỘT BOOKING
# ============================================================

def room_has_booking_conflict(
    room,
    check_in_date,
    check_out_date,
    exclude_booking_id=None,
):
    """
    Check active Booking and CustomerBooking conflicts.
    Kiểm tra xung đột với Booking và CustomerBooking active.
    """

    # ========================================================
    # STAFF BOOKING CONFLICT
    # XUNG ĐỘT BOOKING STAFF
    # ========================================================

    staff_bookings = (
        Booking.objects
        .filter(
            room=room,
            status__in=(
                Booking.ACTIVE_BOOKING_STATUSES
            ),
            check_in_date__lt=(
                check_out_date
            ),
            check_out_date__gt=(
                check_in_date
            ),
        )
    )

    # Exclude the Booking currently being edited.
    # Loại Booking hiện đang được chỉnh sửa.
    if exclude_booking_id:
        staff_bookings = (
            staff_bookings.exclude(
                pk=exclude_booking_id
            )
        )

    if staff_bookings.exists():
        return True

    # ========================================================
    # CUSTOMER PORTAL BOOKING CONFLICT
    # XUNG ĐỘT CUSTOMER PORTAL BOOKING
    # ========================================================

    # Booking uses DateField while CustomerBooking uses
    # DateTimeField, therefore active portal bookings are
    # converted to hotel-local calendar dates.
    #
    # Booking dùng DateField còn CustomerBooking dùng
    # DateTimeField, vì vậy portal booking active được
    # chuyển sang calendar date theo múi giờ khách sạn.
    online_bookings = (
        CustomerBooking.objects
        .filter(
            room=room,
            status__in=(
                CustomerBooking.ACTIVE_BOOKING_STATUSES
            ),
        )
        .only(
            "check_in_at",
            "check_out_at",
        )
    )

    for online_booking in online_bookings:

        portal_start_date = (
            get_local_date(
                online_booking.check_in_at
            )
        )

        portal_end_date = (
            get_local_date(
                online_booking.check_out_at
            )
        )

        # A valid same-day CustomerBooking still occupies
        # one calendar booking day when compared with
        # the date-based staff Booking model.
        #
        # CustomerBooking hợp lệ trong cùng ngày vẫn
        # được tính là một ngày khi so với Booking dạng date.
        if (
            portal_end_date
            <= portal_start_date
        ):
            portal_end_date = (
                portal_start_date
                + timedelta(days=1)
            )

        # Standard half-open interval overlap: [start, end).
        # Quy tắc overlap khoảng nửa mở: [start, end).
        if (
            portal_start_date
            < check_out_date
            and portal_end_date
            > check_in_date
        ):
            return True

    return False


# ============================================================
# STAFF BOOKING FORM
# FORM BOOKING STAFF
# ============================================================

class BookingForm(forms.ModelForm):

    class Meta:
        model = Booking

        fields = [
            "customer",
            "room",
            "check_in_date",
            "check_out_date",
            "status",
        ]

        widgets = {
            "customer": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "room": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "check_in_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "check_out_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
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

        # ====================================================
        # ROOM QUERYSET
        # DANH SÁCH PHÒNG
        # ====================================================

        # Do not rely on Room.status == Available.
        # Future availability is determined by booking overlap.
        #
        # Không dựa vào Room.status == Available.
        # Availability tương lai được xác định bằng booking overlap.
        rooms = (
            Room.objects
            .select_related(
                "room_type"
            )
            .order_by(
                "room_number"
            )
        )

        # New bookings cannot start on a room that is
        # currently marked as Maintenance.
        # Booking mới không được tạo trên phòng đang Maintenance.
        if not self.instance.pk:
            rooms = rooms.exclude(
                status="maintenance"
            )

        self.fields[
            "room"
        ].queryset = rooms

        # ====================================================
        # STATUS WORKFLOW
        # LUỒNG TRẠNG THÁI
        # ====================================================

        status_labels = dict(
            Booking.BOOKING_STATUS
        )

        if not self.instance.pk:

            # A new staff Booking may start Pending
            # or immediately Confirmed.
            # Booking staff mới có thể bắt đầu Pending
            # hoặc Confirmed.
            allowed_statuses = [
                Booking.STATUS_PENDING_CONFIRMATION,
                Booking.STATUS_CONFIRMED,
            ]

        elif (
            self.instance.status
            == Booking.STATUS_PENDING_CONFIRMATION
        ):

            # Pending may remain Pending, become Confirmed,
            # or be Cancelled.
            # Pending có thể giữ nguyên, Confirmed hoặc Cancelled.
            allowed_statuses = [
                Booking.STATUS_PENDING_CONFIRMATION,
                Booking.STATUS_CONFIRMED,
                Booking.STATUS_CANCELLED,
            ]

        elif (
            self.instance.status
            == Booking.STATUS_CONFIRMED
        ):

            # Confirmed may remain Confirmed or be Cancelled.
            # Confirmed có thể giữ nguyên hoặc Cancelled.
            #
            # Checked In is intentionally excluded because
            # check-in must occur through the Face Check-in workflow.
            #
            # Checked In cố ý không xuất hiện vì check-in
            # phải đi qua workflow Face Check-in.
            allowed_statuses = [
                Booking.STATUS_CONFIRMED,
                Booking.STATUS_CANCELLED,
            ]

        else:

            # Checked In, Checked Out and Cancelled are terminal
            # states for this generic Booking form.
            # Checked In, Checked Out và Cancelled là trạng thái
            # kết thúc đối với form Booking chung.
            allowed_statuses = [
                self.instance.status,
            ]

        self.fields[
            "status"
        ].choices = [
            (
                status,
                status_labels.get(
                    status,
                    status,
                ),
            )
            for status in allowed_statuses
        ]

        # ====================================================
        # LOCK OPERATIONAL HISTORY
        # KHÓA LỊCH SỬ NGHIỆP VỤ
        # ====================================================

        if (
            self.instance.pk
            and self.instance.status
            in [
                Booking.STATUS_CHECKED_IN,
                Booking.STATUS_CHECKED_OUT,
                Booking.STATUS_CANCELLED,
            ]
        ):

            # Historical or terminal bookings must not be
            # edited through this generic form.
            # Booking lịch sử hoặc terminal không được chỉnh sửa
            # thông qua form Booking chung.
            for field_name in [
                "customer",
                "room",
                "check_in_date",
                "check_out_date",
                "status",
            ]:
                self.fields[
                    field_name
                ].disabled = True

    def clean(self):
        """
        Validate staff Booking workflow and availability.
        Kiểm tra workflow và availability của Booking staff.
        """

        cleaned_data = (
            super().clean()
        )

        room = (
            cleaned_data.get(
                "room"
            )
        )

        check_in_date = (
            cleaned_data.get(
                "check_in_date"
            )
        )

        check_out_date = (
            cleaned_data.get(
                "check_out_date"
            )
        )

        status = (
            cleaned_data.get(
                "status"
            )
        )

        if (
            not check_in_date
            or not check_out_date
        ):
            return cleaned_data

        # Check-out must always be later than check-in.
        # Check-out luôn phải sau check-in.
        if (
            check_out_date
            <= check_in_date
        ):
            raise forms.ValidationError(
                "Check-out date must be after check-in date."
            )

        # Only newly created bookings are forbidden
        # from starting in the past.
        #
        # Chỉ booking mới bị cấm có ngày bắt đầu trong quá khứ.
        # Không đặt rule này ở model vì booking lịch sử vẫn cần
        # được chuyển trạng thái hợp lệ.
        if (
            not self.instance.pk
            and check_in_date
            < timezone.localdate()
        ):
            raise forms.ValidationError(
                "Check-in date cannot be in the past."
            )

        # Cancelled and Checked Out bookings no longer
        # participate in availability checks.
        # Cancelled và Checked Out không còn tham gia
        # kiểm tra availability.
        if (
            status
            not in Booking.ACTIVE_BOOKING_STATUSES
        ):
            return cleaned_data

        if not room:
            return cleaned_data

        # Do not allow an active booking to be placed on
        # a room currently marked as Maintenance.
        #
        # Không cho booking active nằm trên phòng hiện
        # đang được đánh dấu Maintenance.
        if room.status == "maintenance":
            raise forms.ValidationError(
                "A booking cannot remain active while "
                "the selected room is under maintenance."
            )

        conflict = (
            room_has_booking_conflict(
                room=room,
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                exclude_booking_id=(
                    self.instance.pk
                    if self.instance.pk
                    else None
                ),
            )
        )

        if conflict:
            raise forms.ValidationError(
                "This room is already booked "
                "during the selected period."
            )

        return cleaned_data