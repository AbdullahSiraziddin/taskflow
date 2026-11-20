from django.contrib import admin
from .models import StudyGroup, Subject, GroupMembership, PermissionSet, RoleAssignment


@admin.register(StudyGroup)
class StudyGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_by')
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


@admin.register(PermissionSet)
class PermissionSetAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'codes')


@admin.register(RoleAssignment)
class RoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'subject', 'permission_set', 'assigned_by')
    list_filter = ('group',)