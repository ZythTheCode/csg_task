from django.test import RequestFactory
from django.utils import timezone
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csg_project.settings')
django.setup()

from accounts.models import User
from core.views import DashboardView
from tasks.api_views import DashboardChartsAPIView
from tasks.models import Task

for u in User.objects.all()[:10]:
    rf = RequestFactory()
    req_all = rf.get('/dashboard/?scope=all')
    req_all.user = u
    req_my = rf.get('/dashboard/?scope=my_tasks')
    req_my.user = u

    v_all = DashboardView()
    v_all.request = req_all
    ctx_all = v_all.get_context_data()

    v_my = DashboardView()
    v_my.request = req_my
    ctx_my = v_my.get_context_data()

    api_all = DashboardChartsAPIView.as_view()(req_all)
    api_my = DashboardChartsAPIView.as_view()(req_my)

    print(f"User: {u.username} ({u.role}) override={u.has_task_override}")
    print(f"  ALL: active={ctx_all['active_tasks']}, completed={ctx_all['completed_tasks']}, overdue={ctx_all['overdue_tasks']}, upcoming={ctx_all['upcoming_tasks']}")
    print(f"  MY:  active={ctx_my['active_tasks']}, completed={ctx_my['completed_tasks']}, overdue={ctx_my['overdue_tasks']}, upcoming={ctx_my['upcoming_tasks']}")
    print(f"  API ALL status: {api_all.data['status_distribution']}")
    print(f"  API MY status:  {api_my.data['status_distribution']}")
