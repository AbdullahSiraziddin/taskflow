from django.urls import path
from . import views

urlpatterns = [
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/new/', views.task_new, name='task_new'),
    path('tasks/new/<int:group_pk>/', views.task_create, name='task_create'),
    path('tasks/<int:pk>/', views.task_detail, name='task_detail'),
    path('tasks/<int:pk>/edit/', views.task_edit, name='task_edit'),
    path('tasks/<int:pk>/action/', views.task_action, name='task_action'),
    path('tasks/<int:pk>/delete/', views.task_delete, name='task_delete'),
]