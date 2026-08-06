from django.core.management.base import BaseCommand
from accounts.models import User
from organizations.models import Organization


class Command(BaseCommand):
    help = 'Create or sync default super admin accounts (superadmin and admin) attached to CSG organization'

    def handle(self, *args, **options):
        csg_org = Organization.objects.filter(abbreviation='CSG').first() or \
                  Organization.objects.filter(name__icontains='Central Student Government').first() or \
                  Organization.objects.first()

        superadmins = [
            {'username': 'superadmin', 'email': 'superadmin@csg.com', 'first_name': 'Super', 'last_name': 'Admin'},
            {'username': 'admin', 'email': 'admin@csg.edu.ph', 'first_name': 'Admin', 'last_name': 'CSG'},
        ]

        for sa in superadmins:
            user = User.objects.filter(username=sa['username']).first()
            if not user:
                user = User.objects.create_superuser(
                    username=sa['username'],
                    email=sa['email'],
                    password='admin',
                    first_name=sa['first_name'],
                    last_name=sa['last_name'],
                    role='super_admin',
                    organization=csg_org
                )
                self.stdout.write(self.style.SUCCESS(f"Super admin '{sa['username']}' created with password 'admin'."))
            else:
                user.role = 'super_admin'
                user.is_superuser = True
                user.is_staff = True
                if csg_org:
                    user.organization = csg_org
                user.save(update_fields=['role', 'is_superuser', 'is_staff', 'organization'])
                self.stdout.write(self.style.SUCCESS(f"Super admin '{sa['username']}' updated with full superadmin access & CSG organization."))

