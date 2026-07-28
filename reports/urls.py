from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.ReportsDashboardView.as_view(), name='dashboard'),
    path('export/pdf/', views.ExportReportPDFView.as_view(), name='export_pdf'),
    path('export/excel/', views.ExportReportExcelView.as_view(), name='export_excel'),
]
