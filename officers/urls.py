from django.urls import path
from . import views

app_name = 'officers'

urlpatterns = [
    path('', views.OfficerListView.as_view(), name='list'),
    path('create/', views.OfficerCreateView.as_view(), name='create'),
    path('<int:pk>/', views.OfficerDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.OfficerUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.OfficerDeleteView.as_view(), name='delete'),
    path('positions/', views.PositionListView.as_view(), name='position_list'),
    path('positions/create/', views.PositionCreateView.as_view(), name='position_create'),
    path('positions/<int:pk>/edit/', views.PositionUpdateView.as_view(), name='position_edit'),
    path('positions/<int:pk>/delete/', views.PositionDeleteView.as_view(), name='position_delete'),
]
