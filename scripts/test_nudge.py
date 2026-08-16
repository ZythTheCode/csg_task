from django.test import TestCase, RequestFactory
from accounts.models import User
from tasks.models import Task
from tasks.views import NudgeOfficersView
import json

class NudgeTestCase(TestCase):
    def test_nudge(self):
        admin = User.objects.filter(role='super_admin').first() or User.objects.create_user(username='nudge_admin', role='super_admin')
        task = Task.objects.first()
        if not task:
            task = Task.objects.create(title='Nudge Test Task', created_by=admin)
        officers = list(task.assigned_officers.all())
        if not officers:
            exec_user = User.objects.filter(role='executive').first() or User.objects.create_user(username='exec_officer', role='executive')
            task.assigned_officers.add(exec_user)
            officers = [exec_user]

        rf = RequestFactory()
        req = rf.post(
            f'/tasks/{task.pk}/nudge/',
            data={'officer_ids': [o.id for o in officers if o], 'message': 'Test nudge'},
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        req.user = admin

        view = NudgeOfficersView.as_view()
        res = view(req, pk=task.pk)

        data = json.loads(res.content)
        self.assertTrue(data.get('ok'), f"Nudge failed: {data}")
