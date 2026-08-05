from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'Create default super admin accounts if none exist'

    def handle(self, *args, **options):
        # Ensure default 'admin' account exists
        admin_user, created_admin = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@csg.com',
                'first_name': 'Admin',
                'last_name': 'CSG',
                'role': 'super_admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created_admin:
            admin_user.set_password('admin')
            admin_user.role = 'super_admin'
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Super admin created: admin / admin'))

        # Ensure 'superadmin' account exists (username: superadmin, password: admin123)
        user, created = User.objects.get_or_create(
            username='superadmin',
            defaults={
                'email': 'superadmin@csg.com',
                'first_name': 'Super',
                'last_name': 'Admin',
                'role': 'super_admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        user.set_password('admin123')
        user.role = 'super_admin'
        user.is_staff = True
        user.is_superuser = True
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS('Super admin created: superadmin / admin123'))
        else:
            self.stdout.write(self.style.SUCCESS('Super admin updated: superadmin / admin123'))

