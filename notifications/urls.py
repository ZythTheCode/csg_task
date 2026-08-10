from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='list'),
    path('<int:pk>/read/', views.MarkReadView.as_view(), name='mark_read'),
    path('<int:pk>/delete/', views.DeleteNotificationView.as_view(), name='delete'),
    path('mark-all-read/', views.MarkAllReadView.as_view(), name='mark_all_read'),
    path('bulk-delete/', views.BulkDeleteNotificationView.as_view(), name='bulk_delete'),
]
