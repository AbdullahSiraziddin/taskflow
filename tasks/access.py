from django.db.models import Q

from academics.models import Perm
from academics.permissions import manageable_groups, user_can
from .models import Task


def can_edit_task(user, task):
    return user_can(user, Perm.EDIT_TASK, task.group, task.subject)


def can_delete_task(user, task):
    return user_can(user, Perm.DELETE_TASK, task.group, task.subject)


def can_view_task(user, task):
    """Менеджер видит всё, автор видит своё, остальные члены группы видят не-черновики."""
    if can_edit_task(user, task) or task.author_id == user.id:
        return True
    if task.status == Task.Status.DRAFT:
        return False
    return task.group.memberships.filter(user=user).exists()


def visible_tasks(user):
    """Список заданий, доступных пользователю. Для небольшого колледжа этого достаточно."""
    qs = (Task.objects.select_related('group', 'subject', 'author')
          .filter(Q(group__in=manageable_groups(user))
                  | Q(group__memberships__user=user)
                  | Q(author=user))
          .distinct())
    return [t for t in qs if can_view_task(user, t)]