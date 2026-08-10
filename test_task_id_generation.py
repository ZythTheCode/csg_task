import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csg_project.settings')
django.setup()

from accounts.models import User
from tasks.models import Task
from organizations.models import Organization

admin = User.objects.filter(role='super_admin').first()
aces_org = Organization.objects.get(abbreviation='ACES')

new_task = Task.objects.create(
    title="Test New Task ID Format",
    description="Testing task_number without org abbreviation prefix",
    created_by=admin,
    organization=aces_org
)

print(f"Newly Created Task Number: {new_task.task_number}")
assert not new_task.task_number.startswith("ACES-")
assert "-" in new_task.task_number and len(new_task.task_number.split("-")[0]) == 4

new_task.delete()
print("Task creation test passed successfully!")
