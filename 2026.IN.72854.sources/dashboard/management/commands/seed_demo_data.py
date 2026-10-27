from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.utils import timezone

from customers.models import Customer
from rooms.models import RoomType, Room
from bookings.models import Booking
from checkout.models import CheckOut, Payment


class Command(BaseCommand):
    help = 'Create demo data for Hotel Face Check-in System'

    def handle(self, *args, **kwargs):
        User = get_user_model()

        self.stdout.write(self.style.WARNING('Creating demo data...'))

        admin_group, _ = Group.objects.get_or_create(name='Admin')
        receptionist_group, _ = Group.objects.get_or_create(name='Receptionist')

        admin_user, created = User.objects.get_or_create(
            username='admin_demo',
            defaults={
                'email': 'admin_demo@example.com',
                'is_staff': True,
                'is_superuser': True,
            }
        )

        if created:
            admin_user.set_password('12345678')
            admin_user.save()

        admin_user.groups.add(admin_group)

        receptionist_user, created = User.objects.get_or_create(
            username='receptionist',
            defaults={
                'email': 'receptionist@example.com',
                'is_staff': False,
                'is_superuser': False,
            }
        )

        if created:
            receptionist_user.set_password('12345678')
            receptionist_user.save()

        receptionist_user.groups.add(receptionist_group)

        single_room, _ = RoomType.objects.get_or_create(
            name='Single Room',
            defaults={
                'description': 'Room for one guest',
                'price_per_night': 50,
                'capacity': 1,
            }
        )

        double_room, _ = RoomType.objects.get_or_create(
            name='Double Room',
            defaults={
                'description': 'Room for two guests',
                'price_per_night': 80,
                'capacity': 2,
            }
        )

        vip_room, _ = RoomType.objects.get_or_create(
            name='VIP Room',
            defaults={
                'description': 'Luxury room with premium services',
                'price_per_night': 150,
                'capacity': 4,
            }
        )

        room_data = [
            ('101', single_room, 1, 'available'),
            ('102', single_room, 1, 'available'),
            ('201', double_room, 2, 'available'),
            ('202', double_room, 2, 'maintenance'),
            ('301', vip_room, 3, 'available'),
        ]

        rooms = {}

        for room_number, room_type, floor, status in room_data:
            room, _ = Room.objects.get_or_create(
                room_number=room_number,
                defaults={
                    'room_type': room_type,
                    'floor': floor,
                    'status': status,
                }
            )
            rooms[room_number] = room

        customer_data = [
            {
                'full_name': 'Nguyen Van A',
                'email': 'nguyenvana@example.com',
                'phone': '0123456789',
                'id_card_number': 'ID001',
                'address': 'Rzeszow, Poland',
            },
            {
                'full_name': 'Tran Thi B',
                'email': 'tranthib@example.com',
                'phone': '0987654321',
                'id_card_number': 'ID002',
                'address': 'Warsaw, Poland',
            },
            {
                'full_name': 'Le Van C',
                'email': 'levanc@example.com',
                'phone': '0111222333',
                'id_card_number': 'ID003',
                'address': 'Krakow, Poland',
            },
        ]

        customers = {}

        for data in customer_data:
            customer, _ = Customer.objects.get_or_create(
                id_card_number=data['id_card_number'],
                defaults=data
            )
            customers[data['id_card_number']] = customer

        today = timezone.localdate()

        booking_1, _ = Booking.objects.get_or_create(
            customer=customers['ID001'],
            room=rooms['101'],
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
            defaults={
                'status': 'confirmed',
            }
        )

        booking_2, _ = Booking.objects.get_or_create(
            customer=customers['ID002'],
            room=rooms['201'],
            check_in_date=today + timedelta(days=1),
            check_out_date=today + timedelta(days=4),
            defaults={
                'status': 'pending',
            }
        )

        booking_3, _ = Booking.objects.get_or_create(
            customer=customers['ID003'],
            room=rooms['301'],
            check_in_date=today - timedelta(days=3),
            check_out_date=today - timedelta(days=1),
            defaults={
                'status': 'checked_out',
            }
        )

        booking_1.save()
        booking_2.save()
        booking_3.save()

        CheckOut.objects.get_or_create(
            booking=booking_3,
            defaults={
                'final_amount': booking_3.total_price,
                'staff': receptionist_user,
            }
        )

        Payment.objects.get_or_create(
            booking=booking_3,
            amount=booking_3.total_price,
            payment_method='cash',
            status='paid',
        )

        self.stdout.write(self.style.SUCCESS('Demo data created successfully.'))
        self.stdout.write(self.style.SUCCESS('Admin demo login: admin_demo / 12345678'))
        self.stdout.write(self.style.SUCCESS('Receptionist login: receptionist / 12345678'))