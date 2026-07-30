from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'Create a default super admin account if none exists'

    def handle(self, *args, **options):
        if User.objects.filter(role='super_admin').exists():
            self.stdout.write(self.style.WARNING('Super admin already exists. Skipping.'))
            return

        User.objects.create_superuser(
            username='admin',
            password='admin',
            first_name='Admin',
            last_name='CSG',
            email='admin@csg.com',
            role='super_admin',
        )
        self.stdout.write(self.style.SUCCESS('Super admin created: admin / admin'))
