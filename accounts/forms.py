from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from academics.models import GroupMembership, StudyGroup
from .models import User


class BootstrapMixin:
    """Добавляет Bootstrap-классы ко всем полям формы."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                css = 'form-check-input'
            elif isinstance(field.widget, forms.Select):
                css = 'form-select'
            else:
                css = 'form-control'
            field.widget.attrs['class'] = css


class RegisterForm(BootstrapMixin, forms.ModelForm):
    group = forms.ModelChoiceField(
        queryset=StudyGroup.objects.all(), label=_('Учебная группа'),
        empty_label=_('— выберите группу —'))
    password1 = forms.CharField(label=_('Пароль'), widget=forms.PasswordInput)
    password2 = forms.CharField(label=_('Подтверждение пароля'), widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['full_name', 'email']
        labels = {'full_name': _('ФИО'), 'email': _('Электронная почта')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['full_name'].required = True

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_('Эта почта уже зарегистрирована.'))
        return email

    def clean_password1(self):
        password = self.cleaned_data['password1']
        validate_password(password)
        return password

    def clean(self):
        data = super().clean()
        p1, p2 = data.get('password1'), data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', _('Пароли не совпадают.'))
        return data

    @transaction.atomic
    def save(self, commit=True):
        # Либо создаётся и пользователь, и участие в группе, либо ничего
        user = super().save(commit=False)
        user.username = user.email
        user.role = User.Role.STUDENT      # через сайт регистрируются только студенты
        user.set_password(self.cleaned_data['password1'])
        user.save()
        GroupMembership.objects.create(user=user, group=self.cleaned_data['group'])
        return user


class LoginForm(BootstrapMixin, AuthenticationForm):
    username = forms.CharField(label=_('Электронная почта'))
    password = forms.CharField(label=_('Пароль'), widget=forms.PasswordInput)

    def clean_username(self):
        return self.cleaned_data['username'].strip().lower()