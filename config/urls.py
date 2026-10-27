from django import forms
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.urls import include, path
from django.views.decorators.http import require_POST


class StaffAuthenticationForm(AuthenticationForm):
    """
    Allow only Admin, Receptionist, or superuser accounts
    to sign in through the staff login page.

    Chỉ cho phép Admin, Receptionist hoặc superuser
    đăng nhập qua trang đăng nhập staff.
    """

    def confirm_login_allowed(self, user):
        # Keep Django's built-in checks such as is_active.
        # Giữ các kiểm tra mặc định của Django như is_active.
        super().confirm_login_allowed(user)

        # Superusers always have access to the staff area.
        # Superuser luôn được phép truy cập khu vực staff.
        if user.is_superuser:
            return

        # Staff login is restricted to the two operational roles.
        # Staff login chỉ dành cho hai role vận hành này.
        has_staff_role = (
            user.groups
            .filter(
                name__in=[
                    "Admin",
                    "Receptionist",
                ]
            )
            .exists()
        )

        if not has_staff_role:
            raise forms.ValidationError(
                "This login page is for hotel staff only.",
                code="staff_only",
            )


@require_POST
def staff_logout_view(request):
    """
    Log out the current staff session.
    Đăng xuất phiên đăng nhập staff hiện tại.
    """

    logout(request)

    return redirect(
        "login"
    )


urlpatterns = [
    # ========================================================
    # DJANGO ADMIN
    # TRANG QUẢN TRỊ DJANGO
    # ========================================================
    path(
        "admin/",
        admin.site.urls,
    ),

    # ========================================================
    # PUBLIC HOTEL WEBSITE
    # WEBSITE CÔNG KHAI CỦA KHÁCH SẠN
    # ========================================================
    path(
        "",
        include("hotel_site.urls"),
    ),

    # ========================================================
    # STAFF AUTHENTICATION
    # XÁC THỰC STAFF
    # ========================================================
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=StaffAuthenticationForm,
            redirect_authenticated_user=False,
        ),
        name="login",
    ),

    path(
        "logout/",
        staff_logout_view,
        name="logout",
    ),

    # ========================================================
    # STAFF MODULES
    # CÁC MODULE DÀNH CHO STAFF
    # ========================================================
    path(
        "dashboard/",
        include("dashboard.urls"),
    ),
    path(
        "customers/",
        include("customers.urls"),
    ),
    path(
        "rooms/",
        include("rooms.urls"),
    ),
    path(
        "bookings/",
        include("bookings.urls"),
    ),
    path(
        "checkin/",
        include("checkin.urls"),
    ),
    path(
        "checkout/",
        include("checkout.urls"),
    ),
    path(
        "reports/",
        include("reports.urls"),
    ),

    # ========================================================
    # CUSTOMER PORTAL
    # KHU VỰC CUSTOMER PORTAL
    # ========================================================
    path(
        "",
        include("customer_portal.urls"),
    ),
]


# Serve uploaded media directly only during development.
# Chỉ phục vụ media trực tiếp khi chạy môi trường development.
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )