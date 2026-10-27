from django.contrib import messages
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from accounts.decorators import group_required

from .forms import (
    RoomForm,
    RoomTypeForm,
)
from .models import (
    Room,
    RoomType,
)


# ============================================================
# ROOM TYPE VIEWS
# CÁC VIEW QUẢN LÝ LOẠI PHÒNG
# ============================================================

@group_required("Admin")
def room_type_list(request):
    """
    Display all room types.
    Hiển thị toàn bộ loại phòng.
    """

    room_types = (
        RoomType.objects
        .all()
        .order_by("name")
    )

    return render(
        request,
        "rooms/room_type_list.html",
        {
            "room_types": room_types,
        },
    )


@group_required("Admin")
def room_type_create(request):
    """
    Create a new room type.
    Tạo loại phòng mới.
    """

    if request.method == "POST":

        form = RoomTypeForm(
            request.POST
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Room type created successfully.",
            )

            return redirect(
                "room_type_list"
            )

    else:

        form = RoomTypeForm()

    return render(
        request,
        "rooms/room_type_form.html",
        {
            "form": form,
            "title": "Add Room Type",
        },
    )


@group_required("Admin")
def room_type_update(
    request,
    pk,
):
    """
    Update an existing room type.
    Cập nhật loại phòng hiện có.
    """

    room_type = get_object_or_404(
        RoomType,
        pk=pk,
    )

    if request.method == "POST":

        form = RoomTypeForm(
            request.POST,
            instance=room_type,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Room type updated successfully.",
            )

            return redirect(
                "room_type_list"
            )

    else:

        form = RoomTypeForm(
            instance=room_type
        )

    return render(
        request,
        "rooms/room_type_form.html",
        {
            "form": form,
            "title": "Edit Room Type",
        },
    )


@group_required("Admin")
def room_type_delete(
    request,
    pk,
):
    """
    Delete a room type only when no Room references it.
    Chỉ xóa loại phòng khi không có Room nào đang tham chiếu.
    """

    room_type = get_object_or_404(
        RoomType,
        pk=pk,
    )

    if request.method == "POST":

        try:
            room_type.delete()

        except ProtectedError:
            # Room.room_type uses PROTECT, therefore a room type
            # currently used by any room must be preserved.
            # Room.room_type dùng PROTECT nên loại phòng đang
            # được bất kỳ phòng nào sử dụng phải được bảo toàn.
            messages.error(
                request,
                "This room type cannot be deleted because "
                "one or more rooms are currently using it.",
            )

            return redirect(
                "room_type_list"
            )

        messages.success(
            request,
            "Room type deleted successfully.",
        )

        return redirect(
            "room_type_list"
        )

    return render(
        request,
        "rooms/room_type_confirm_delete.html",
        {
            "room_type": room_type,
        },
    )


# ============================================================
# ROOM VIEWS
# CÁC VIEW QUẢN LÝ PHÒNG
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def room_list(request):
    """
    Display and filter hotel rooms.
    Hiển thị và lọc danh sách phòng.
    """

    search_query = (
        request.GET.get(
            "q",
            ""
        ).strip()
    )

    status_filter = (
        request.GET.get(
            "status",
            ""
        )
    )

    room_type_filter = (
        request.GET.get(
            "room_type",
            ""
        )
    )

    rooms = (
        Room.objects
        .select_related(
            "room_type"
        )
        .all()
        .order_by(
            "room_number"
        )
    )

    # Search by room number or room type.
    # Tìm kiếm theo số phòng hoặc loại phòng.
    if search_query:
        rooms = rooms.filter(
            Q(
                room_number__icontains=search_query
            )
            | Q(
                room_type__name__icontains=search_query
            )
        )

    # Filter by current operational status.
    # Lọc theo trạng thái vận hành hiện tại.
    valid_statuses = {
        value
        for value, _ in Room.ROOM_STATUS
    }

    if status_filter in valid_statuses:
        rooms = rooms.filter(
            status=status_filter
        )

    # Filter by RoomType id.
    # Lọc theo ID loại phòng.
    if room_type_filter:
        try:
            room_type_id = int(
                room_type_filter
            )

        except (
            TypeError,
            ValueError,
        ):
            room_type_id = None

        if room_type_id is not None:
            rooms = rooms.filter(
                room_type_id=room_type_id
            )

    room_types = (
        RoomType.objects
        .all()
        .order_by(
            "name"
        )
    )

    return render(
        request,
        "rooms/room_list.html",
        {
            "rooms": rooms,
            "room_types": room_types,
            "status_choices": Room.ROOM_STATUS,
            "search_query": search_query,
            "status_filter": status_filter,
            "room_type_filter": room_type_filter,
        },
    )


@group_required("Admin")
def room_create(request):
    """
    Create a hotel room.
    Tạo phòng khách sạn.
    """

    if request.method == "POST":

        form = RoomForm(
            request.POST
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Room created successfully.",
            )

            return redirect(
                "room_list"
            )

    else:

        form = RoomForm()

    return render(
        request,
        "rooms/room_form.html",
        {
            "form": form,
            "title": "Add Room",
        },
    )


@group_required("Admin")
def room_update(
    request,
    pk,
):
    """
    Update room information and operational status.
    Cập nhật thông tin và trạng thái vận hành của phòng.
    """

    room = get_object_or_404(
        Room.objects.select_related(
            "room_type"
        ),
        pk=pk,
    )

    if request.method == "POST":

        form = RoomForm(
            request.POST,
            instance=room,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Room updated successfully.",
            )

            return redirect(
                "room_list"
            )

    else:

        form = RoomForm(
            instance=room
        )

    return render(
        request,
        "rooms/room_form.html",
        {
            "form": form,
            "title": "Edit Room",
        },
    )


@group_required("Admin")
def room_delete(
    request,
    pk,
):
    """
    Delete a room only when no protected history references it.
    Chỉ xóa phòng khi không có lịch sử được PROTECT tham chiếu.
    """

    room = get_object_or_404(
        Room.objects.select_related(
            "room_type"
        ),
        pk=pk,
    )

    if request.method == "POST":

        try:
            room.delete()

        except ProtectedError:
            # Booking and CustomerBooking records protect
            # the room from historical data loss.
            # Booking và CustomerBooking bảo vệ phòng để
            # tránh mất dữ liệu lịch sử.
            messages.error(
                request,
                "This room cannot be deleted because "
                "it already has protected booking, "
                "check-in, checkout, or payment history.",
            )

            return redirect(
                "room_list"
            )

        messages.success(
            request,
            "Room deleted successfully.",
        )

        return redirect(
            "room_list"
        )

    return render(
        request,
        "rooms/room_confirm_delete.html",
        {
            "room": room,
        },
    )