from django.contrib import admin
from .models import RoomType, Room


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_per_night', 'capacity')
    search_fields = ('name',)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'room_type', 'floor', 'status')
    list_filter = ('status', 'room_type', 'floor')
    search_fields = ('room_number',)