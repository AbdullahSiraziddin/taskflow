from django.contrib import admin
from .models import Task, TaskLog


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'group', 'subject', 'deadline', 'status', 'author')
    list_filter = ('group', 'subject', 'status')
    search_fields = ('title',)


@admin.register(TaskLog)
class TaskLogAdmin(admin.ModelAdmin):
    list_display = ('task', 'user', 'action', 'details', 'created_at')
    list_filter = ('action',)