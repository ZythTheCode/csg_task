from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from organizations.models import Organization
from tasks.models import Task, TaskAssignment

User = get_user_model()


class TaskModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='password123'
        )

    def test_task_number_generation(self):
        task = Task.objects.create(
            title='Test Task Number',
            description='Testing task number generation',
            created_by=self.user
        )
        year = timezone.now().year
        self.assertTrue(task.task_number.startswith(f'{year}-'))


class TaskNotificationTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(username='creator', password='password123')
        self.officer1 = User.objects.create_user(username='officer1', password='password123')
        self.officer2 = User.objects.create_user(username='officer2', password='password123')
        self.task = Task.objects.create(
            title='Sample Task',
            description='Sample Task Description',
            created_by=self.creator
        )
        TaskAssignment.objects.create(task=self.task, officer=self.officer1, assigned_by=self.creator)
        TaskAssignment.objects.create(task=self.task, officer=self.officer2, assigned_by=self.creator)

    def test_comment_notification(self):
        from notifications.models import Notification
        self.client.login(username='creator', password='password123')
        response = self.client.post(f'/tasks/{self.task.pk}/comments/', {
            'content': 'This is a test comment'
        })
        self.assertRedirects(response, f'/tasks/{self.task.pk}/')
        self.assertTrue(Notification.objects.filter(recipient=self.officer1, notification_type='comment_added').exists())
        self.assertTrue(Notification.objects.filter(recipient=self.officer2, notification_type='comment_added').exists())
        self.assertFalse(Notification.objects.filter(recipient=self.creator, notification_type='comment_added').exists())

    def test_attachment_notification(self):
        from notifications.models import Notification
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.login(username='officer1', password='password123')
        test_file = SimpleUploadedFile("test_doc.pdf", b"file_content", content_type="application/pdf")
        response = self.client.post(f'/tasks/{self.task.pk}/attachments/', {
            'file': test_file
        })
        self.assertRedirects(response, f'/tasks/{self.task.pk}/')
        self.assertTrue(Notification.objects.filter(recipient=self.officer2, notification_type='attachment_added').exists())
        self.assertTrue(Notification.objects.filter(recipient=self.creator, notification_type='attachment_added').exists())
        self.assertFalse(Notification.objects.filter(recipient=self.officer1, notification_type='attachment_added').exists())

    def test_delete_comment(self):
        from tasks.models import TaskComment
        comment = TaskComment.objects.create(task=self.task, author=self.creator, content='Delete me')
        self.client.login(username='creator', password='password123')
        response = self.client.post(f'/tasks/comments/{comment.pk}/delete/')
        self.assertRedirects(response, f'/tasks/{self.task.pk}/')
        self.assertFalse(TaskComment.objects.filter(pk=comment.pk).exists())

    def test_task_category(self):
        multimedia_task = Task.objects.create(
            title='Multimedia Task',
            description='Editing video',
            category='multimedia',
            created_by=self.creator
        )
        self.assertEqual(multimedia_task.category, 'multimedia')
        self.assertEqual(multimedia_task.get_category_display(), 'Multimedia')

