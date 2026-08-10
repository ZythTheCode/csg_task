from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    path('', views.TaskListView.as_view(), name='list'),
    path('create/', views.TaskCreateView.as_view(), name='create'),
    path('<int:pk>/', views.TaskDetailView.as_view(), name='detail'),
    path('<int:pk>/json/', views.TaskDetailJSONView.as_view(), name='detail_json'),
    path('<int:pk>/edit/', views.TaskUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.TaskDeleteView.as_view(), name='delete'),
    path('bulk-delete/', views.TaskBulkDeleteView.as_view(), name='bulk_delete'),
    path('board/', views.TaskBoardView.as_view(), name='board'),
    path('calendar/', views.TaskCalendarView.as_view(), name='calendar'),
    path('calendar/events/', views.TaskCalendarEventsView.as_view(), name='calendar_events'),

    path('<int:pk>/move/', views.TaskMoveStatusView.as_view(), name='move'),
    path('<int:pk>/progress/', views.UpdateProgressView.as_view(), name='update_progress'),
    path('<int:pk>/complete/', views.MarkCompleteView.as_view(), name='complete'),
    path('<int:pk>/archive/', views.ArchiveTaskView.as_view(), name='archive'),
    path('<int:pk>/comments/', views.AddCommentView.as_view(), name='add_comment'),
    path('comments/<int:pk>/delete/', views.DeleteCommentView.as_view(), name='delete_comment'),
    path('<int:pk>/attachments/', views.AddAttachmentView.as_view(), name='add_attachment'),
    path('attachments/<int:pk>/delete/', views.DeleteAttachmentView.as_view(), name='delete_attachment'),
    path('attachments/<int:pk>/download/', views.DownloadAttachmentView.as_view(), name='download_attachment'),
    path('attachments/<int:pk>/view/', views.ViewAttachmentView.as_view(), name='view_attachment'),
    path('export/pdf/', views.ExportTasksPDFView.as_view(), name='export_pdf'),
    path('export/excel/', views.ExportTasksExcelView.as_view(), name='export_excel'),
    path('<int:pk>/nudge/', views.NudgeOfficersView.as_view(), name='nudge'),
    path('search-suggestions/', views.TaskSearchSuggestionsView.as_view(), name='search_suggestions'),
]
