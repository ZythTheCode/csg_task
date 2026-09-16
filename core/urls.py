from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.LandingPageView.as_view(), name='landing'),
    path('landing/', views.LandingPageView.as_view(), name='landing_direct'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('activity-log/', views.ActivityLogView.as_view(), name='activity_log'),
]
