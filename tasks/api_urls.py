from django.urls import path
from . import api_views

urlpatterns = [
    path('dashboard/stats/', api_views.DashboardStatsAPIView.as_view(), name='api_dashboard_stats'),
    path('dashboard/charts/', api_views.DashboardChartsAPIView.as_view(), name='api_dashboard_charts'),
    path('tasks/', api_views.TaskListAPIView.as_view(), name='api_task_list'),
    path('tasks/<int:pk>/', api_views.TaskDetailAPIView.as_view(), name='api_task_detail'),
    path('notifications/unread/', api_views.UnreadNotificationsAPIView.as_view(), name='api_notifications_unread'),
    path('notifications/<int:pk>/read/', api_views.MarkNotificationReadAPIView.as_view(), name='api_notification_read'),
]
