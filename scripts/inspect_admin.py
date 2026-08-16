import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csg_project.settings')
django.setup()

from accounts.models import User
from organizations.models import Organization

print("=== ALL USERS IN NEON DB ===")
for u in User.objects.all():
    pic_name = u.profile_picture.name if u.profile_picture else "EMPTY"
    pic_url = ""
    try:
        if u.profile_picture:
            pic_url = u.profile_picture.url
    except Exception as e:
        pic_url = f"ERROR: {e}"
    print(f"ID: {u.id} | Username: '{u.username}' | Full Name: '{u.get_full_name()}' | Role: '{u.role}' | Pic Name: '{pic_name}' | Pic URL: '{pic_url}'")

print("\n=== ALL ORGS IN NEON DB ===")
for o in Organization.objects.all():
    logo_name = o.logo.name if o.logo else "EMPTY"
    logo_url = ""
    try:
        if o.logo:
            logo_url = o.logo.url
    except Exception as e:
        logo_url = f"ERROR: {e}"
    print(f"ID: {o.id} | Name: '{o.name}' | Logo Name: '{logo_name}' | Logo URL: '{logo_url}'")
