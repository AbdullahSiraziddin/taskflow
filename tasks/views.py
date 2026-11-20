from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from academics.models import Perm, StudyGroup
from academics.permissions import (allowed_subjects, groups_for_action,
                                   is_group_owner, require_perm)
from .access import can_delete_task, can_edit_task, can_view_task, visible_tasks
from .forms import TaskForm
from .models import ACTION_LABELS, TASK_ACTIONS, Task, TaskLog


@login_required
def task_list(request):
    tasks = visible_tasks(request.user)
    groups = sorted({t.group for t in tasks}, key=lambda g: g.name)

    group_id = request.GET.get('group', '')
    state = request.GET.get('state', '')
    if group_id.isdigit():
        tasks = [t for t in tasks if t.group_id == int(group_id)]
    if state:
        tasks = [t for t in tasks if t.state == state]
    else:
        tasks = [t for t in tasks if t.state != 'archived']   # архив скрыт по умолчанию
    tasks.sort(key=lambda t: t.deadline)

    return render(request, 'tasks/task_list.html', {
        'tasks': tasks,
        'groups': groups,
        'group_id': group_id,
        'state': state,
        'state_choices': [(k, v[0]) for k, v in Task.STATE_META.items()],
    })


@login_required
def task_new(request):
    """Шаг 1 создания: выбор группы."""
    groups = groups_for_action(request.user, Perm.CREATE_TASK)
    if len(groups) == 1:
        return redirect('task_create', group_pk=groups[0].pk)
    return render(request, 'tasks/choose_group.html', {'groups': groups})


@login_required
def task_create(request, group_pk):
    """Шаг 2 создания: форма задания (предмет выбирается из предметов этой группы)."""
    group = get_object_or_404(StudyGroup, pk=group_pk)
    subjects = allowed_subjects(request.user, Perm.CREATE_TASK, group)
    if not subjects:
        if is_group_owner(request.user, group) and not group.subjects.exists():
            messages.warning(request, _('Сначала добавьте в группу хотя бы один предмет.'))
            return redirect('group_detail', pk=group.pk)
        raise PermissionDenied

    initial = {
        'start_at': timezone.localtime().replace(second=0, microsecond=0),
        'allowed_formats': ['pdf'],
        'presentation_minutes': 5,
    }
    form = TaskForm(request.POST or None, initial=initial, group=group,
                    user=request.user, perm=Perm.CREATE_TASK)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            task = form.save(commit=False)
            task.group = group
            task.author = request.user
            publish = request.POST.get('action') == 'publish'
            task.status = Task.Status.PUBLISHED if publish else Task.Status.DRAFT
            task.save()
            TaskLog.objects.create(task=task, user=request.user,
                                   action=TaskLog.Action.CREATED,
                                   details=task.status)
        # Часть 8: здесь студенты группы получат уведомление о новом задании
        messages.success(request, _('Задание опубликовано.') if publish
                         else _('Черновик сохранён.'))
        return redirect('task_detail', pk=task.pk)

    return render(request, 'tasks/task_form.html', {
        'form': form, 'group': group, 'is_new': True,
        'title': _('Новое задание'), 'back_url': '/tasks/'})


@login_required
def task_detail(request, pk):
    task = get_object_or_404(
        Task.objects.select_related('group', 'subject', 'author'), pk=pk)
    user = request.user
    if not can_view_task(user, task):
        raise PermissionDenied          # чужое задание или чужой черновик

    can_edit = can_edit_task(user, task)
    state = task.state
    actions = []
    if can_edit:
        actions = [(code, ACTION_LABELS[code])
                   for code, (from_statuses, _to) in TASK_ACTIONS.items()
                   if task.status in from_statuses]

    countdown_target = None
    if state == 'upcoming':
        countdown_target = task.start_at
    elif state == 'open':
        countdown_target = task.deadline

    return render(request, 'tasks/task_detail.html', {
        'task': task,
        'can_edit': can_edit,
        'can_delete': can_delete_task(user, task),
        'actions': actions,
        'hide_details': (not can_edit) and state == 'upcoming',
        'countdown_target': countdown_target,
        'now': timezone.now(),
        'logs': task.logs.select_related('user')[:20] if can_edit else [],
    })

@login_required
def task_edit(request, pk):
    task = get_object_or_404(Task.objects.select_related('group', 'subject'), pk=pk)
    require_perm(request.user, Perm.EDIT_TASK, task.group, task.subject)

    form = TaskForm(request.POST or None, instance=task, group=task.group,
                    user=request.user, perm=Perm.EDIT_TASK)
    if request.method == 'POST' and form.is_valid():
        changed = list(form.changed_data)
        with transaction.atomic():
            form.save()
            if changed:
                TaskLog.objects.create(task=task, user=request.user,
                                       action=TaskLog.Action.UPDATED,
                                       details=','.join(changed)[:250])
        # Часть 8: при смене дедлайна или инструкций студенты получат уведомление
        messages.success(request, _('Задание сохранено.'))
        return redirect('task_detail', pk=task.pk)

    return render(request, 'tasks/task_form.html', {
        'form': form, 'group': task.group, 'is_new': False,
        'title': _('Редактирование задания'), 'back_url': f'/tasks/{task.pk}/'})


@login_required
@require_POST
def task_action(request, pk):
    """Опубликовать, приостановить, закрыть, архивировать и т. д."""
    task = get_object_or_404(Task.objects.select_related('group', 'subject'), pk=pk)
    require_perm(request.user, Perm.EDIT_TASK, task.group, task.subject)

    rule = TASK_ACTIONS.get(request.POST.get('action'))
    if not rule or task.status not in rule[0]:
        messages.error(request, _('Это действие сейчас недоступно.'))
        return redirect('task_detail', pk=task.pk)

    new_status = rule[1]
    with transaction.atomic():
        task.status = new_status
        task.save(update_fields=['status', 'updated_at'])
        TaskLog.objects.create(task=task, user=request.user,
                               action=TaskLog.Action.STATUS, details=new_status)

    if new_status == Task.Status.PUBLISHED and task.deadline <= timezone.now():
        messages.warning(request, _('Срок сдачи уже истёк. Измените дедлайн в редактировании.'))
    messages.success(request, _('Статус задания обновлён.'))
    return redirect('task_detail', pk=task.pk)


@login_required
@require_POST
def task_delete(request, pk):
    task = get_object_or_404(Task.objects.select_related('group', 'subject'), pk=pk)
    require_perm(request.user, Perm.DELETE_TASK, task.group, task.subject)
    # Часть 4: для заданий со сданными работами удаление будет запрещено (только архив)
    task.delete()
    messages.success(request, _('Задание удалено.'))
    return redirect('task_list')