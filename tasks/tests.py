from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from organizations.models import Organization
from tasks.models import Task

User = get_user_model()


class TaskModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='password123'
        )

    def test_task_number_uses_organization_abbreviation(self):
        org = Organization.objects.create(
            name='Computer Developers and Engineers Society',
            abbreviation='CO:DE',
            status='approved'
        )
        task = Task.objects.create(
            title='Test Task Abbreviation',
            description='Testing task number generation',
            organization=org,
            created_by=self.user
        )
        year = timezone.now().year
        self.assertTrue(task.task_number.startswith(f'CODE-{year}-'))

    def test_task_number_uses_organization_short_name_when_no_abbreviation(self):
        org = Organization.objects.create(
            name='Association of Civil Engineers',
            abbreviation='',
            status='approved'
        )
        task = Task.objects.create(
            title='Test Task Short Name',
            description='Testing task number generation',
            organization=org,
            created_by=self.user
        )
        year = timezone.now().year
        # Short name for 'Association of Civil Engineers' defaults to name[:3] -> 'ASS'
        self.assertTrue(task.task_number.startswith(f'ASS-{year}-'))

    def test_task_number_default_when_no_organization(self):
        task = Task.objects.create(
            title='Test Task No Org',
            description='Testing task number generation',
            created_by=self.user
        )
        year = timezone.now().year
        self.assertTrue(task.task_number.startswith(f'CSG-{year}-'))

