"""
Django settings for the Hotel Management System project.
Cấu hình Django cho project Hotel Management System.
"""

import os
from pathlib import Path


# ============================================================
# BASE DIRECTORY
# THƯ MỤC GỐC CỦA PROJECT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# BASIC CONFIGURATION
# CẤU HÌNH CƠ BẢN
# ============================================================

# Use an environment variable in production while keeping
# a development fallback so the local graduation demo still works.
# Production nên dùng biến môi trường, đồng thời giữ fallback
# development để bản demo đồ án local vẫn chạy bình thường.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-development-only-change-this-key",
)


# Development mode is enabled by default for the local demo.
# Mặc định bật development mode cho bản demo local.
DEBUG = (
    os.environ.get(
        "DJANGO_DEBUG",
        "True",
    ).lower()
    == "true"
)


ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
]


# ============================================================
# INSTALLED APPLICATIONS
# CÁC ỨNG DỤNG ĐÃ CÀI ĐẶT
# ============================================================

INSTALLED_APPS = [
    # Django built-in applications.
    # Các ứng dụng mặc định của Django.
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Public hotel website.
    # Website công khai của khách sạn.
    "hotel_site",

    # Staff authentication and role support.
    # Xác thực và phân quyền tài khoản staff.
    "accounts",

    # Hotel management modules.
    # Các module quản lý khách sạn.
    "dashboard",
    "customers",
    "rooms",
    "bookings",
    "checkin",
    "checkout",
    "reports",

    # Customer Portal.
    # Cổng thông tin dành cho customer.
    "customer_portal",
]


# ============================================================
# MIDDLEWARE
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================
# URL AND WSGI
# URL VÀ WSGI
# ============================================================

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"


# ============================================================
# TEMPLATES
# TEMPLATE
# ============================================================

TEMPLATES = [
    {
        "BACKEND": (
            "django.template.backends.django.DjangoTemplates"
        ),

        "DIRS": [
            BASE_DIR / "templates",
        ],

        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",

                # Provide Admin/Receptionist role information
                # to staff templates.
                # Cung cấp thông tin role Admin/Receptionist
                # cho template staff.
                "accounts.context_processors.user_roles",
            ],
        },
    },
]


# ============================================================
# DATABASE
# CƠ SỞ DỮ LIỆU
# ============================================================

# SQLite is intentionally used for the local graduation demo.
# PostgreSQL migration is avoided during the audit to reduce risk.
# SQLite được chủ động sử dụng cho bản demo đồ án local.
# Không chuyển PostgreSQL trong giai đoạn audit để giảm rủi ro.
DATABASES = {
    "default": {
        "ENGINE": (
            "django.db.backends.sqlite3"
        ),
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# ============================================================
# PASSWORD VALIDATION
# KIỂM TRA MẬT KHẨU
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ============================================================
# LANGUAGE AND TIME ZONE
# NGÔN NGỮ VÀ MÚI GIỜ
# ============================================================

LANGUAGE_CODE = "en-us"

# The hotel is located in Rzeszów, Poland, so hotel operations
# should use the local Polish time zone.
# Khách sạn ở Rzeszów, Ba Lan nên nghiệp vụ khách sạn
# sử dụng múi giờ địa phương của Ba Lan.
TIME_ZONE = "Europe/Warsaw"

USE_I18N = True

# Keep timezone-aware datetimes internally.
# Giữ datetime có timezone bên trong hệ thống.
USE_TZ = True


# ============================================================
# STATIC FILES
# STATIC FILES
# ============================================================

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = (
    BASE_DIR / "staticfiles"
)


# ============================================================
# MEDIA FILES
# MEDIA FILES
# ============================================================

# Media contains sensitive guest and check-in images.
# Production must not expose these files using the
# development media-serving configuration.
#
# Media chứa ảnh giấy tờ, selfie và ảnh Face Check-in nhạy cảm.
# Production không được public trực tiếp các file này
# bằng cấu hình phục vụ media của development.
MEDIA_URL = "/media/"

MEDIA_ROOT = (
    BASE_DIR / "media"
)


# ============================================================
# DEFAULT PRIMARY KEY
# PRIMARY KEY MẶC ĐỊNH
# ============================================================

DEFAULT_AUTO_FIELD = (
    "django.db.models.BigAutoField"
)


# ============================================================
# AUTHENTICATION AND LOGIN
# XÁC THỰC VÀ ĐĂNG NHẬP
# ============================================================

# Staff authentication routes.
# Route xác thực dành cho staff.
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/login/"


# Customer Portal authentication routes.
# Route xác thực dành cho Customer Portal.
CUSTOMER_LOGIN_URL = (
    "customer_portal:customer_login"
)

CUSTOMER_LOGIN_REDIRECT_URL = (
    "customer_portal:customer_dashboard"
)

CUSTOMER_LOGOUT_REDIRECT_URL = (
    "customer_portal:customer_login"
)


AUTHENTICATION_BACKENDS = [
    # Standard Django username/password authentication.
    # Xác thực username/password mặc định của Django.
    "django.contrib.auth.backends.ModelBackend",

    # Customer Portal authentication by username,
    # email, or phone number.
    # Customer Portal có thể đăng nhập bằng username,
    # email hoặc số điện thoại.
    "customer_portal.backends.EmailOrPhoneBackend",
]


# ============================================================
# EMAIL
# EMAIL
# ============================================================

# For the local demo, outgoing emails are printed to the terminal.
# This is sufficient for testing registration and booking-status
# notifications without configuring a real email provider.
#
# Trong bản demo local, email được in ra terminal.
# Cách này đủ để test đăng ký và thông báo trạng thái booking
# mà không cần cấu hình nhà cung cấp email thực tế.
EMAIL_BACKEND = (
    "django.core.mail.backends.console.EmailBackend"
)

DEFAULT_FROM_EMAIL = (
    "Hotel Management System <noreply@hotel.local>"
)