from django.urls import path

from . import views


app_name = "hotel_site"


urlpatterns = [
    path(
        "",
        views.home,
        name="home",
    ),
    path(
        "rooms-public/",
        views.public_rooms,
        name="public_rooms",
    ),
    path(
        "about/",
        views.about,
        name="about",
    ),
    path(
        "contact/",
        views.contact,
        name="contact",
    ),
]