from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Пользователь TaskFlow. Логин = электронная почта."""

    class Role(models.TextChoices):
        ADMIN = 'admin', _('Администратор')
        TEACHER = 'teacher', _('Преподаватель')
        STUDENT = 'student', _('Студент')

    email = models.EmailField(_('Электронная почта'), unique=True)
    full_name = models.CharField(_('ФИО'), max_length=150, blank=True)
    role = models.CharField(_('Роль'), max_length=10, choices=Role.choices,
                            default=Role.STUDENT)
    language = models.CharField(_('Язык интерфейса'), max_length=2,
                                default='ru')

    def save(self, *args, **kwargs):
        # Суперпользователь всегда считается администратором
        if self.is_superuser:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

    @property
    def is_teacher_like(self):
        """Преподаватель или администратор: видят панель управления."""
        return self.role in (self.Role.TEACHER, self.Role.ADMIN)

    def __str__(self):
        return self.full_name or self.email