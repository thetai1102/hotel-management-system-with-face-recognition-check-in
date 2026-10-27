from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def group_required(*group_names):
    """
    Chỉ cho phép user thuộc các group được yêu cầu truy cập view.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Chưa đăng nhập thì chuyển tới trang đăng nhập staff
            if not request.user.is_authenticated:
                return redirect('login')

            # Superuser luôn có toàn quyền
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Cho phép user thuộc ít nhất một group được yêu cầu
            if request.user.groups.filter(name__in=group_names).exists():
                return view_func(request, *args, **kwargs)

            messages.error(
                request,
                'You do not have permission to access this page.'
            )

            # Customer đăng nhập nhầm khu vực staff thì quay về customer portal
            if hasattr(request.user, 'customer_profile'):
                return redirect('customer_portal:customer_dashboard')

            # User khác không có quyền thì quay về trang đăng nhập staff
            return redirect('login')

        return wrapped_view

    return decorator