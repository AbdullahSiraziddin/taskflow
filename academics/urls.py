from django.urls import path
from . import views

urlpatterns = [
    path('groups/', views.group_list, name='group_list'),
    path('groups/new/', views.group_create, name='group_create'),
    path('groups/<int:pk>/', views.group_detail, name='group_detail'),

    path('groups/<int:group_pk>/subjects/new/', views.subject_create, name='subject_create'),
    path('subjects/<int:pk>/edit/', views.subject_edit, name='subject_edit'),
    path('subjects/<int:pk>/delete/', views.subject_delete, name='subject_delete'),

    path('groups/<int:group_pk>/members/add/', views.member_add, name='member_add'),
    path('members/<int:pk>/status/', views.member_status, name='member_status'),
    path('members/<int:pk>/remove/', views.member_remove, name='member_remove'),

    path('permission-sets/', views.permset_list, name='permset_list'),
    path('permission-sets/new/', views.permset_create, name='permset_create'),
    path('permission-sets/<int:pk>/delete/', views.permset_delete, name='permset_delete'),

    path('groups/<int:group_pk>/roles/assign/', views.role_assign, name='role_assign'),
    path('roles/<int:pk>/revoke/', views.role_revoke, name='role_revoke'),
]