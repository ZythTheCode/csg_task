import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csg_project.settings')
django.setup()

from organizations.models import Organization
from officers.models import Position, Officer

for org in Organization.objects.all():
    positions = Position.objects.filter(organization=org)
    officers = Officer.objects.filter(user__organization=org)
    print(f"\n--- Organization: {org.name} ({org.abbreviation}) ---")
    print(f"Total Positions: {positions.count()}")
    for p in positions:
        assigned = getattr(p, 'officer', None)
        print(f"  Position: {p.title} (ID: {p.pk}) -> Assigned to: {assigned.user.get_full_name() if assigned and getattr(assigned, 'user', None) else 'UNASSIGNED'}")
    print(f"Total Officers: {officers.count()}")
