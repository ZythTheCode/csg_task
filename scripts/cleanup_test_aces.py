import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csg_project.settings')
django.setup()

from organizations.models import Organization
from officers.models import Position

aces_org = Organization.objects.get(abbreviation='ACES')
Position.objects.filter(title='Vice President', organization=aces_org).delete()
print("Cleaned up test Vice President position from ACES.")
