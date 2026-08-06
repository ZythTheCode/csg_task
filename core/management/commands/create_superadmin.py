from django.core.management.base import BaseCommand
from accounts.models import User
from organizations.models import Organization


class Command(BaseCommand):
    help = 'Create or sync default super admin accounts (superadmin and admin) attached to CSG organization'

    def handle(self, *args, **options):
        csg_org = Organization.objects.filter(id=2).first() or \
                  Organization.objects.filter(name__icontains='Central Student Government').first() or \
                  Organization.objects.filter(abbreviation='CSG').first() or \
                  Organization.objects.first()

        # Cleanup legacy 'superadmin' account if present
        User.objects.filter(username='superadmin').delete()

        admin_data = {'username': 'admin', 'email': 'admin@csg.edu.ph', 'first_name': 'Admin', 'last_name': 'CSG'}

        from officers.models import Officer

        user = User.objects.filter(username=admin_data['username']).first()
        if not user:
            user = User.objects.create_superuser(
                username=admin_data['username'],
                email=admin_data['email'],
                password='admin',
                first_name=admin_data['first_name'],
                last_name=admin_data['last_name'],
                role='super_admin',
                organization=csg_org
            )
            self.stdout.write(self.style.SUCCESS(f"Super admin '{admin_data['username']}' created with password 'admin'."))
        else:
            user.role = 'super_admin'
            user.is_superuser = True
            user.is_staff = True
            if csg_org:
                user.organization = csg_org
            user.save(update_fields=['role', 'is_superuser', 'is_staff', 'organization'])
            self.stdout.write(self.style.SUCCESS(f"Super admin '{admin_data['username']}' updated with full superadmin access & CSG organization."))

        Officer.objects.get_or_create(
            user=user,
            defaults={'student_id': 'SA-2026-0001'}
        )

        # ── CREATE / SYNC SUPERSUPERADMIN ACCOUNT ─────────────────────
        super_user = User.objects.filter(username='supersuperadmin').first()
        if not super_user:
            super_user = User.objects.create_superuser(
                username='supersuperadmin',
                email='supersuperadmin@csg.com',
                password='admin',
                first_name='Super',
                last_name='Super Admin',
                role='super_super_admin',
                organization=csg_org
            )
            self.stdout.write(self.style.SUCCESS("Super Super Admin 'supersuperadmin' created with password 'admin'."))
        else:
            super_user.role = 'super_super_admin'
            super_user.is_superuser = True
            super_user.is_staff = True
            if csg_org:
                super_user.organization = csg_org
            super_user.save(update_fields=['role', 'is_superuser', 'is_staff', 'organization'])
            self.stdout.write(self.style.SUCCESS("Super Super Admin 'supersuperadmin' updated with super_super_admin role."))


