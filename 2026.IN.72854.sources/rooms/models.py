from django.db import models


class RoomType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    capacity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.name


class Room(models.Model):
    ROOM_STATUS = [
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('occupied', 'Occupied'),
        ('cleaning', 'Cleaning'),
        ('maintenance', 'Maintenance'),
    ]

    room_number = models.CharField(max_length=20, unique=True)

    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.PROTECT
    )

    floor = models.PositiveIntegerField(default=1)

    status = models.CharField(
        max_length=20,
        choices=ROOM_STATUS,
        default='available'
    )

    def __str__(self):
        return f"Room {self.room_number}"