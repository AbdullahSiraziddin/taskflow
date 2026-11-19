from django.contrib import admin
from .models import StudyGroup, Subject, GroupMembership


@admin.register(StudyGroup)
class StudyGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'group')
    list_filter = ('group',)
    filter_horizontal = ('teachers',)


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'status', 'joined_at')
    list_filter = ('group', 'status')