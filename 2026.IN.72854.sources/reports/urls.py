from django.urls import path

from . import views


urlpatterns = [
    # Reports dashboard for Admin users.
    # Dashboard báo cáo dành cho Admin.
    path(
        "",
        views.reports_dashboard,
        name="reports_dashboard",
    ),
]