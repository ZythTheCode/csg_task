from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from notifications.models import Notification

class NotificationDeleteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="notif_user", password="password123")
        self.other_user = User.objects.create_user(username="other_user", password="password123")
        self.n1 = Notification.objects.create(recipient=self.user, title="Test 1", message="Message 1")
        self.n2 = Notification.objects.create(recipient=self.user, title="Test 2", message="Message 2")
        self.n3 = Notification.objects.create(recipient=self.user, title="Test 3", message="Message 3")
        self.other_n = Notification.objects.create(recipient=self.other_user, title="Other Test", message="Other Message")

    def test_single_delete_notification(self):
        self.client.login(username="notif_user", password="password123")
        response = self.client.post(reverse('notifications:delete', kwargs={'pk': self.n1.pk}))
        self.assertRedirects(response, reverse('notifications:list'))
        self.assertFalse(Notification.objects.filter(pk=self.n1.pk).exists())
        self.assertTrue(Notification.objects.filter(pk=self.other_n.pk).exists())

    def test_bulk_delete_selected_notifications(self):
        self.client.login(username="notif_user", password="password123")
        response = self.client.post(reverse('notifications:bulk_delete'), {
            'action_type': 'selected',
            'notification_ids': [self.n1.pk, self.n2.pk]
        })
        self.assertRedirects(response, reverse('notifications:list'))
        self.assertFalse(Notification.objects.filter(pk=self.n1.pk).exists())
        self.assertFalse(Notification.objects.filter(pk=self.n2.pk).exists())
        self.assertTrue(Notification.objects.filter(pk=self.n3.pk).exists())
        self.assertTrue(Notification.objects.filter(pk=self.other_n.pk).exists())

    def test_bulk_delete_all_notifications(self):
        self.client.login(username="notif_user", password="password123")
        response = self.client.post(reverse('notifications:bulk_delete'), {
            'action_type': 'all'
        })
        self.assertRedirects(response, reverse('notifications:list'))
        self.assertEqual(Notification.objects.filter(recipient=self.user).count(), 0)
        self.assertTrue(Notification.objects.filter(pk=self.other_n.pk).exists())
