from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('progress/<str:download_id>/', views.progress, name='progress'),
    path('download/<str:download_id>/', views.download_file, name='download_file'),
]
