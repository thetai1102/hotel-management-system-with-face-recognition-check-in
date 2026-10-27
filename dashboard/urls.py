from django.urls import path

from . import views


urlpatterns = [
    # Main dashboard for Admin and Receptionist.
    # Dashboard chính dành cho Admin và Receptionist.
    path(
        "",
        views.dashboard_view,
        name="dashboard",
    ),
]