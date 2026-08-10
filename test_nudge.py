import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csg_project.settings')
django.setup()

from django.test import RequestFactory
from accounts.models import User
from tasks.models import Task
from tasks.views import NudgeOfficersView

admin = User.objects.filter(role='super_admin').first()
task = Task.objects.first()
officers = list(task.assigned_officers.all())

if not officers:
    officers = [User.objects.filter(role='executive').first()]

rf = RequestFactory()
req = rf.post(
    f'/tasks/{task.pk}/nudge/',
    data={'officer_ids': [o.id for o in officers if o], 'message': 'Test nudge'},
    headers={'X-Requested-With': 'XMLHttpRequest'}
)
req.user = admin

view = NudgeOfficersView.as_view()
res = view(req, pk=task.pk)

import json
data = json.loads(res.content)
print("Nudge API Response:")
print(json.dumps(data, indent=2))
assert data['ok'] == True
assert 'In-app nudge sent' in data['message']
print("\nTest passed successfully!")
