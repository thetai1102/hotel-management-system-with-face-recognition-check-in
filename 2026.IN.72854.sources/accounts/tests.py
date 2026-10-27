from django.contrib.auth import get_user_model
from django.contrib.auth.models import (
    AnonymousUser,
    Group,
)
from django.contrib.messages.storage.fallback import (
    FallbackStorage,
)
from django.contrib.sessions.middleware import (
    SessionMiddleware,
)
from django.http import HttpResponse
from django.test import (
    RequestFactory,
    TestCase,
)
from django.urls import reverse

from customer_portal.models import CustomerProfile

from .decorators import group_required


# ============================================================
# TEST VIEW
# VIEW DÙNG CHO TEST
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def protected_test_view(request):
    """
    Simple protected view used by authorization tests.
    View đơn giản được dùng để test phân quyền.
    """

    return HttpResponse(
        "allowed"
    )


# ============================================================
# GROUP REQUIRED TESTS
# TEST DECORATOR GROUP_REQUIRED
# ============================================================

class GroupRequiredDecoratorTests(TestCase):

    def setUp(self):
        """
        Prepare users, groups and RequestFactory.
        Chuẩn bị user, group và RequestFactory.
        """

        self.factory = (
            RequestFactory()
        )

        self.User = (
            get_user_model()
        )

        self.admin_group = (
            Group.objects.create(
                name="Admin"
            )
        )

        self.receptionist_group = (
            Group.objects.create(
                name="Receptionist"
            )
        )

    def build_request(
        self,
        user,
    ):
        """
        Build a request with session and message storage.
        Tạo request có session và message storage.
        """

        request = (
            self.factory.get(
                "/protected-test/"
            )
        )

        request.user = user

        # Add session support required by Django messages.
        # Thêm session để Django messages hoạt động.
        session_middleware = (
            SessionMiddleware(
                lambda req: None
            )
        )

        session_middleware.process_request(
            request
        )

        request._messages = (
            FallbackStorage(
                request
            )
        )

        return request

    def test_anonymous_user_redirects_to_staff_login(
        self,
    ):
        """
        Anonymous users must be redirected to staff login.
        User chưa đăng nhập phải được chuyển tới staff login.
        """

        request = (
            self.build_request(
                AnonymousUser()
            )
        )

        response = (
            protected_test_view(
                request
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse("login"),
        )

    def test_superuser_is_allowed(
        self,
    ):
        """
        Superusers must always pass staff authorization.
        Superuser luôn phải vượt qua kiểm tra phân quyền staff.
        """

        user = (
            self.User.objects
            .create_superuser(
                username="superadmin",
                email="superadmin@example.com",
                password="StrongPass123!",
            )
        )

        request = (
            self.build_request(
                user
            )
        )

        response = (
            protected_test_view(
                request
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.content,
            b"allowed",
        )

    def test_admin_group_is_allowed(
        self,
    ):
        """
        Admin group members must be allowed.
        Thành viên group Admin phải được cho phép.
        """

        user = (
            self.User.objects
            .create_user(
                username="adminstaff",
                password="StrongPass123!",
            )
        )

        user.groups.add(
            self.admin_group
        )

        request = (
            self.build_request(
                user
            )
        )

        response = (
            protected_test_view(
                request
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_receptionist_group_is_allowed(
        self,
    ):
        """
        Receptionist group members must be allowed.
        Thành viên group Receptionist phải được cho phép.
        """

        user = (
            self.User.objects
            .create_user(
                username="receptionist",
                password="StrongPass123!",
            )
        )

        user.groups.add(
            self.receptionist_group
        )

        request = (
            self.build_request(
                user
            )
        )

        response = (
            protected_test_view(
                request
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_ordinary_authenticated_user_redirects_to_staff_login(
        self,
    ):
        """
        Authenticated users without a staff role must be denied.
        User đã đăng nhập nhưng không có role staff phải bị từ chối.
        """

        user = (
            self.User.objects
            .create_user(
                username="ordinaryuser",
                password="StrongPass123!",
            )
        )

        request = (
            self.build_request(
                user
            )
        )

        response = (
            protected_test_view(
                request
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse("login"),
        )

    def test_customer_account_redirects_to_customer_dashboard(
        self,
    ):
        """
        Customer Portal users must not enter the staff area.
        User Customer Portal không được truy cập khu vực staff.
        """

        user = (
            self.User.objects
            .create_user(
                username="customer@example.com",
                email="customer@example.com",
                password="StrongPass123!",
            )
        )

        CustomerProfile.objects.create(
            user=user,
            full_name="Test Customer",
            phone="+48123456789",
        )

        request = (
            self.build_request(
                user
            )
        )

        response = (
            protected_test_view(
                request
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse(
                "customer_portal:customer_dashboard"
            ),
        )