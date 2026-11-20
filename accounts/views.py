from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from academics.models import Subject
from academics.permissions import manageable_groups
from .forms import RegisterForm

def home(request):
    """Лендинг. Вошедших сразу отправляем на панель."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html')


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, _('Добро пожаловать в TaskFlow!'))
        return redirect('dashboard')
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def dashboard(request):
    """Главная панель: у студента и преподавателя она разная."""
    user = request.user
    if user.is_teacher_like:
        groups = manageable_groups(user)
        return render(request, 'dashboard/teacher.html', {
            'groups': groups,
            'subjects': Subject.objects.filter(group__in=groups).select_related('group'),
        })

    memberships = user.memberships.select_related('group')
    group_ids = [m.group_id for m in memberships]
    return render(request, 'dashboard/student.html', {
        'memberships': memberships,
        'subjects': Subject.objects.filter(group_id__in=group_ids).select_related('group'),
        'roles': user.role_assignments.select_related('group', 'subject', 'permission_set'),
    })