from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOrPhoneBackend(ModelBackend):
    """
    Authenticate customer accounts by username, email, or phone number.
    Xác thực tài khoản customer bằng username, email hoặc số điện thoại.
    """

    def authenticate(
        self,
        request,
        username=None,
        password=None,
        **kwargs
    ):
        User = get_user_model()

        identifier = (
            username
            or kwargs.get("identifier")
        )

        if not identifier or not password:
            return None

        # Only search users that have a CustomerProfile.
        # Chỉ tìm những user thực sự là tài khoản customer.
        users = User.objects.filter(
            customer_profile__isnull=False
        ).filter(
            Q(username__iexact=identifier)
            | Q(email__iexact=identifier)
            | Q(
                customer_profile__phone__iexact=identifier
            )
        ).distinct()

        # A login identifier must resolve to exactly one customer.
        # Thông tin đăng nhập phải xác định đúng một customer.
        if users.count() != 1:
            return None

        user = users.first()

        if (
            user
            and user.check_password(password)
            and self.user_can_authenticate(user)
        ):
            return user

        return None