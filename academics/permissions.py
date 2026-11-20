from django.core.exceptions import PermissionDenied
from django.db.models import Q

from .models import RoleAssignment, StudyGroup


def manageable_groups(user):
    """Группы, которыми пользователь управляет как преподаватель/администратор."""
    if not user.is_authenticated:
        return StudyGroup.objects.none()
    if user.role == user.Role.ADMIN:
        return StudyGroup.objects.all()
    if user.role == user.Role.TEACHER:
        return StudyGroup.objects.filter(
            Q(created_by=user) | Q(subjects__teachers=user)).distinct()
    return StudyGroup.objects.none()


def is_group_owner(user, group):
    return manageable_groups(user).filter(pk=group.pk).exists()


def user_can(user, code, group, subject=None):
    """Можно ли пользователю выполнить действие `code` в этой группе (и предмете)?"""
    if not user.is_authenticated or not user.is_active:
        return False
    if is_group_owner(user, group):
        return True                     # преподаватель группы и админ могут всё

    assignments = RoleAssignment.objects.filter(
        user=user, group=group).select_related('permission_set')
    if subject is None:
        # действие уровня группы: подходят только назначения «на всю группу»
        assignments = assignments.filter(subject__isnull=True)
    else:
        # действие в предмете: подходит «вся группа» или именно этот предмет
        assignments = assignments.filter(Q(subject__isnull=True) | Q(subject=subject))
    return any(code in a.permission_set.codes for a in assignments)


def require_perm(user, code, group, subject=None):
    """Если права нет: ошибка 403. Вызываем в начале каждого действия."""
    if not user_can(user, code, group, subject):
        raise PermissionDenied


def require_group_owner(user, group):
    if not is_group_owner(user, group):
        raise PermissionDenied