from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from academics.models import Subject
from academics.permissions import allowed_subjects
from accounts.forms import BootstrapMixin
from .models import Task


def _dt_widget():
    """Поле даты и времени с календарём браузера."""
    return forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M')


class TaskForm(BootstrapMixin, forms.ModelForm):
    allowed_formats = forms.MultipleChoiceField(
        choices=Task.Format.choices, widget=forms.CheckboxSelectMultiple,
        label=_('Разрешённые форматы материалов'))

    class Meta:
        model = Task
        fields = ['title', 'description', 'instructions', 'subject',
                  'start_at', 'deadline',
                  'allowed_formats', 'max_files', 'max_file_mb',
                  'requires_presentation', 'presentation_minutes',
                  'max_score', 'allow_resubmission', 'resubmission_deadline']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'instructions': forms.Textarea(attrs={'rows': 6}),
            'start_at': _dt_widget(),
            'deadline': _dt_widget(),
            'resubmission_deadline': _dt_widget(),
        }

    def __init__(self, *args, group, user, perm, **kwargs):
        super().__init__(*args, **kwargs)
        # В списке только те предметы, где у пользователя есть нужное право
        allowed = allowed_subjects(user, perm, group)
        self.fields['subject'].queryset = Subject.objects.filter(
            pk__in=[s.pk for s in allowed])
        self.fields['subject'].empty_label = _('— выберите предмет —')
        for name in ('start_at', 'deadline', 'resubmission_deadline'):
            self.fields[name].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M']
        self.fields['allowed_formats'].widget.attrs['class'] = 'form-check-input'

    def clean(self):
        data = super().clean()
        start, deadline = data.get('start_at'), data.get('deadline')

        if start and deadline:
            if deadline <= start:
                self.add_error('deadline', _('Дедлайн должен быть позже даты начала.'))
            elif not self.instance.pk and deadline <= timezone.now():
                self.add_error('deadline', _('Дедлайн уже в прошлом.'))

        if data.get('requires_presentation'):
            minutes = data.get('presentation_minutes')
            if not minutes or not (1 <= minutes <= 60):
                self.add_error('presentation_minutes',
                               _('Укажите длительность выступления от 1 до 60 минут.'))
        else:
            data['presentation_minutes'] = None

        if data.get('allow_resubmission'):
            resub = data.get('resubmission_deadline')
            if resub and deadline and resub <= deadline:
                self.add_error('resubmission_deadline',
                               _('Срок пересдачи должен быть позже основного дедлайна.'))
        else:
            data['resubmission_deadline'] = None
        return data