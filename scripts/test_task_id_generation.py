import os
import django
from django.test import TestCase

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csg_project.settings')
django.setup()

from accounts.models import User
from tasks.models import Task
from organizations.models import Organization


class TaskIdGenerationTestCase(TestCase):
    def test_task_id_format(self):
        admin, _ = User.objects.get_or_create(username='testadmin', defaults={'role': 'super_admin', 'email': 'testadmin@example.com'})
        aces_org, _ = Organization.objects.get_or_create(name='ACES Org', defaults={'abbreviation': 'ACES'})

        new_task = Task.objects.create(
            title="Test New Task ID Format",
            description="Testing task_number without org abbreviation prefix",
            created_by=admin,
            organization=aces_org
        )

        print(f"Newly Created Task Number: {new_task.task_number}")
        self.assertFalse(new_task.task_number.startswith("ACES-"))
        parts = new_task.task_number.split("-")
        self.assertEqual(len(parts[0]), 4)

        new_task.delete()
        print("Task creation test passed successfully!")
