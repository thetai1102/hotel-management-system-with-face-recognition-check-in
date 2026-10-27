from django.shortcuts import render

from rooms.models import Room


# ============================================================
# PUBLIC HOME PAGE
# TRANG CHỦ PUBLIC
# ============================================================

def home(request):
    """
    Display the public hotel homepage.
    Hiển thị trang chủ public của khách sạn.
    """

    # Featured rooms are examples of hotel inventory.
    # They must not be treated as future-date availability.
    # Các phòng nổi bật chỉ là ví dụ về inventory khách sạn.
    # Không dùng chúng để kết luận availability cho ngày tương lai.
    featured_rooms = (
        Room.objects
        .select_related(
            "room_type"
        )
        .order_by(
            "room_number"
        )[:3]
    )

    return render(
        request,
        "hotel_site/home.html",
        {
            "featured_rooms": featured_rooms,
        },
    )


# ============================================================
# PUBLIC ROOM BROWSING
# DANH SÁCH PHÒNG PUBLIC
# ============================================================

def public_rooms(request):
    """
    Display hotel rooms for public browsing.
    Hiển thị phòng để khách public tham khảo.
    """

    # Do not filter only by Room.status == "available".
    # Room.status represents the current operational state,
    # while future availability depends on booking-date overlap.
    #
    # Không chỉ lọc Room.status == "available".
    # Room.status thể hiện trạng thái vận hành hiện tại,
    # còn availability tương lai phụ thuộc vào booking overlap.
    rooms = (
        Room.objects
        .select_related(
            "room_type"
        )
        .order_by(
            "room_number"
        )
    )

    return render(
        request,
        "hotel_site/public_rooms.html",
        {
            "rooms": rooms,
        },
    )


# ============================================================
# ABOUT PAGE
# TRANG GIỚI THIỆU
# ============================================================

def about(request):
    """
    Display public hotel information.
    Hiển thị thông tin giới thiệu khách sạn.
    """

    return render(
        request,
        "hotel_site/about.html",
    )


# ============================================================
# CONTACT PAGE
# TRANG LIÊN HỆ
# ============================================================

def contact(request):
    """
    Display public contact information.
    Hiển thị thông tin liên hệ public.
    """

    return render(
        request,
        "hotel_site/contact.html",
    )