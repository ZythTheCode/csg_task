import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csg_project.settings')
django.setup()

from accounts.models import User
from officers.models import Position, Officer
from officers.forms import OfficerForm, PositionForm
from organizations.models import Organization

admin = User.objects.filter(role='super_admin').first()
org = Organization.objects.first()

print(f"Testing President Uniqueness in Organization: '{org.name}'")

# Check current President in DB
pres_users = User.objects.filter(organization=org, role='president')
print(f"Current President Users in '{org.name}': {[u.username for u in pres_users]}")

# 1. Try to create a second President officer
form = OfficerForm(data={
    'first_name': 'Second',
    'last_name': 'President',
    'email': 'pres2@csg.edu.ph',
    'role': 'president',
    'position': Position.objects.filter(organization=org).first().pk if Position.objects.filter(organization=org).exists() else '',
}, user=admin)

is_valid = form.is_valid()
print(f"Creating 2nd President officer allowed? {is_valid}")
if not is_valid:
    print("Expected Error:", form.errors)

# 2. Try to create a second Position named 'President'
pos_form = PositionForm(data={
    'title': 'President',
    'initials': 'PRES',
    'description': 'Duplicate President'
})
pos_form.instance.organization = org
pos_is_valid = pos_form.is_valid()
print(f"Creating 2nd 'President' position allowed? {pos_is_valid}")
if not pos_is_valid:
    print("Expected Position Error:", pos_form.errors)
