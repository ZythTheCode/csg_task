import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csg_project.settings')
django.setup()

from accounts.models import User
from organizations.models import Organization
from officers.models import Position, Officer
from officers.forms import OfficerForm
from django.test import RequestFactory

rf = RequestFactory()
request = rf.get('/officers/create/')
admin = User.objects.filter(role='super_admin').first()
aces_org = Organization.objects.filter(abbreviation__iexact='ace').first() or Organization.objects.first()

request.user = admin
request.session = {'active_org_id': aces_org.pk}

# Create a new unassigned position in ACES for testing
new_pos, _ = Position.objects.get_or_create(title='Vice President', organization=aces_org)

# Test creating officer with Vice President
post_data = {
    'first_name': 'Jane',
    'last_name': 'Smith',
    'username': 'janesmith',
    'email': 'jane@csg.edu.ph',
    'role': 'executive',
    'position': str(new_pos.pk),
    'student_id': '202699999',
}
post_form = OfficerForm(data=post_data, request=request, user=admin)
print("Is post form valid with unassigned position?", post_form.is_valid())
if not post_form.is_valid():
    print("Errors:", post_form.errors)
else:
    print("Form is valid!")
