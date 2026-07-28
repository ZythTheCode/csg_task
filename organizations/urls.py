from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_organization, name='register_organization'),
    path('pending/', views.pending_organizations, name='pending_organizations'),
    path('<int:org_id>/approve/', views.approve_organization, name='approve_organization'),
    path('<int:org_id>/reject/', views.reject_organization, name='reject_organization'),
]
