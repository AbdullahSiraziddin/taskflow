from django import forms
from django.utils.translation import gettext_lazy as _

from accounts.forms import BootstrapMixin
from accounts.models import User
from .models import Perm, PermissionSet, StudyGroup, Subject


class GroupForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = StudyGroup
        fields = ['name', 'description']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}


class SubjectForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'teachers']

    def __init__(self, *args, group=None, **kwargs):
        self.group = group
        super().__init__(*args, **kwargs)
        self.fields['teachers'].queryset = User.objects.filter(role=User.Role.TEACHER)
        self.fields['teachers'].widget = forms.CheckboxSelectMultiple()

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        same = Subject.objects.filter(group=self.group, name__iexact=name)
        if same.exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(_('Такой предмет в этой группе уже есть.'))
        return name


class AddMemberForm(BootstrapMixin, forms.Form):
    email = forms.EmailField(label=_('Почта студента'))

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        try:
            self.student = User.objects.get(email__iexact=email, role=User.Role.STUDENT)
        except User.DoesNotExist:
            raise forms.ValidationError(_('Студент с такой почтой не найден.'))
        return email


class PermissionSetForm(BootstrapMixin, forms.ModelForm):
    codes = forms.MultipleChoiceField(
        choices=Perm.choices, widget=forms.CheckboxSelectMultiple,
        label=_('Что разрешено'))

    class Meta:
        model = PermissionSet
        fields = ['name', 'codes']

    def __init__(self, *args, owner=None, **kwargs):
        self.owner = owner
        super().__init__(*args, **kwargs)
        self.fields['codes'].widget.attrs['class'] = 'form-check-input'

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if PermissionSet.objects.filter(owner=self.owner, name__iexact=name).exists():
            raise forms.ValidationError(_('У вас уже есть набор с таким названием.'))
        return name


class AssignRoleForm(BootstrapMixin, forms.Form):
    user = forms.ModelChoiceField(queryset=User.objects.none(), label=_('Студент'))
    permission_set = forms.ModelChoiceField(
        queryset=PermissionSet.objects.none(), label=_('Набор разрешений'))
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.none(), required=False, label=_('Область действия'),
        empty_label=_('Все предметы группы'))

    def __init__(self, *args, group, owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = User.objects.filter(
            memberships__group=group, role=User.Role.STUDENT, is_active=True)
        self.fields['permission_set'].queryset = PermissionSet.objects.filter(owner=owner)
        self.fields['subject'].queryset = group.subjects.all()