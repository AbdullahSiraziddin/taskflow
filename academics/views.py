from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .forms import (AddMemberForm, AssignRoleForm, GroupForm,
                    PermissionSetForm, SubjectForm)
from .models import (GroupMembership, Perm, PermissionSet, RoleAssignment,
                     StudyGroup, Subject)
from .permissions import (is_group_owner, manageable_groups, require_group_owner,
                          require_perm, user_can)


def _form_page(request, form, title, back_url):
    """Одна общая страница для всех простых форм."""
    return render(request, 'academics/form_page.html',
                  {'form': form, 'title': title, 'back_url': back_url})


# ---------- Группы ----------

@login_required
def group_list(request):
    if request.user.is_teacher_like:
        groups = manageable_groups(request.user)
    else:
        groups = StudyGroup.objects.filter(memberships__user=request.user)
    return render(request, 'academics/group_list.html', {'groups': groups})


@login_required
def group_create(request):
    if not request.user.is_teacher_like:
        raise PermissionDenied
    form = GroupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        group = form.save(commit=False)
        group.created_by = request.user
        group.save()
        messages.success(request, _('Группа создана.'))
        return redirect('group_detail', pk=group.pk)
    return _form_page(request, form, _('Новая группа'), '/groups/')


@login_required
def group_detail(request, pk):
    group = get_object_or_404(StudyGroup, pk=pk)
    is_owner = is_group_owner(request.user, group)
    is_member = group.memberships.filter(user=request.user).exists()
    if not (is_owner or is_member):
        raise PermissionDenied          # чужую группу открыть нельзя

    context = {
        'group': group,
        'is_owner': is_owner,
        'can_manage_members': user_can(request.user, Perm.MANAGE_MEMBERS, group),
        'subjects': group.subjects.prefetch_related('teachers'),
        'members': group.memberships.select_related('user').order_by('user__full_name'),
        'status_choices': GroupMembership.Status.choices,
    }
    if is_owner:   # назначения видит только преподаватель
        context['assignments'] = group.role_assignments.select_related(
            'user', 'subject', 'permission_set')
    return render(request, 'academics/group_detail.html', context)


# ---------- Предметы ----------

@login_required
def subject_create(request, group_pk):
    group = get_object_or_404(StudyGroup, pk=group_pk)
    require_group_owner(request.user, group)
    form = SubjectForm(request.POST or None, group=group)
    if request.method == 'POST' and form.is_valid():
        subject = form.save(commit=False)
        subject.group = group
        subject.save()
        form.save_m2m()                 # сохраняет выбранных преподавателей
        messages.success(request, _('Предмет добавлен.'))
        return redirect('group_detail', pk=group.pk)
    return _form_page(request, form, _('Новый предмет'), f'/groups/{group.pk}/')


@login_required
def subject_edit(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    require_group_owner(request.user, subject.group)
    form = SubjectForm(request.POST or None, instance=subject, group=subject.group)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, _('Предмет сохранён.'))
        return redirect('group_detail', pk=subject.group_id)
    return _form_page(request, form, _('Редактирование предмета'),
                      f'/groups/{subject.group_id}/')


@login_required
@require_POST
def subject_delete(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    require_group_owner(request.user, subject.group)
    group_id = subject.group_id
    subject.delete()
    messages.success(request, _('Предмет удалён.'))
    return redirect('group_detail', pk=group_id)

# ---------- Состав группы ----------

@login_required
def member_add(request, group_pk):
    group = get_object_or_404(StudyGroup, pk=group_pk)
    require_perm(request.user, Perm.MANAGE_MEMBERS, group)
    form = AddMemberForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        _m, created = GroupMembership.objects.get_or_create(
            user=form.student, group=group)
        if created:
            messages.success(request, _('Студент добавлен в группу.'))
        else:
            messages.warning(request, _('Этот студент уже в группе.'))
        return redirect('group_detail', pk=group.pk)
    return _form_page(request, form, _('Добавить студента'), f'/groups/{group.pk}/')


@login_required
@require_POST
def member_status(request, pk):
    """Назначить старосту / ответственного. Это только отметка, права дают наборы."""
    membership = get_object_or_404(GroupMembership, pk=pk)
    require_group_owner(request.user, membership.group)
    status = request.POST.get('status')
    if status in GroupMembership.Status.values:
        membership.status = status
        membership.save(update_fields=['status'])
        messages.success(request, _('Статус обновлён.'))
    return redirect('group_detail', pk=membership.group_id)


@login_required
@require_POST
def member_remove(request, pk):
    membership = get_object_or_404(GroupMembership, pk=pk)
    require_perm(request.user, Perm.MANAGE_MEMBERS, membership.group)
    with transaction.atomic():
        # вместе со студентом пропадают и его права в этой группе
        RoleAssignment.objects.filter(
            user=membership.user, group=membership.group).delete()
        membership.delete()
    messages.success(request, _('Студент удалён из группы.'))
    return redirect('group_detail', pk=membership.group_id)

# ---------- Наборы разрешений ----------

def _teacher_only(user):
    if not user.is_teacher_like:
        raise PermissionDenied


@login_required
def permset_list(request):
    _teacher_only(request.user)
    return render(request, 'academics/permset_list.html', {
        'sets': request.user.permission_sets.all()})


@login_required
def permset_create(request):
    _teacher_only(request.user)
    form = PermissionSetForm(request.POST or None, owner=request.user)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.owner = request.user
        obj.save()
        messages.success(request, _('Набор разрешений создан.'))
        return redirect('permset_list')
    return _form_page(request, form, _('Новый набор разрешений'), '/permission-sets/')


@login_required
@require_POST
def permset_delete(request, pk):
    _teacher_only(request.user)
    get_object_or_404(PermissionSet, pk=pk, owner=request.user).delete()   # только свои
    messages.success(request, _('Набор удалён вместе с его назначениями.'))
    return redirect('permset_list')


# ---------- Назначение прав студентам ----------

@login_required
def role_assign(request, group_pk):
    group = get_object_or_404(StudyGroup, pk=group_pk)
    require_group_owner(request.user, group)

    if not PermissionSet.objects.filter(owner=request.user).exists():
        messages.warning(request, _('Сначала создайте хотя бы один набор разрешений.'))
        return redirect('permset_create')

    form = AssignRoleForm(request.POST or None, group=group, owner=request.user)
    if request.method == 'POST' and form.is_valid():
        _a, created = RoleAssignment.objects.get_or_create(
            user=form.cleaned_data['user'],
            group=group,
            subject=form.cleaned_data['subject'],
            permission_set=form.cleaned_data['permission_set'],
            defaults={'assigned_by': request.user})
        if created:
            messages.success(request, _('Права назначены.'))
        else:
            messages.warning(request, _('Такое назначение уже существует.'))
        return redirect('group_detail', pk=group.pk)
    return _form_page(request, form, _('Назначить права студенту'), f'/groups/{group.pk}/')


@login_required
@require_POST
def role_revoke(request, pk):
    assignment = get_object_or_404(RoleAssignment, pk=pk)
    require_group_owner(request.user, assignment.group)
    group_id = assignment.group_id
    assignment.delete()
    messages.success(request, _('Права отозваны.'))
    return redirect('group_detail', pk=group_id)