from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class StudyGroup(models.Model):
    """Учебная группа, например «115»."""
    name = models.CharField(_('Название группы'), max_length=50, unique=True)
    description = models.TextField(_('Описание'), blank=True)

    class Meta:
        verbose_name = 'Учебная группа'
        verbose_name_plural = 'Учебные группы'
        ordering = ['name']

    def __str__(self):
        return self.name


class Subject(models.Model):
    """Предмет внутри группы. У одной группы может быть много предметов."""
    name = models.CharField(_('Название предмета'), max_length=150)
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE,
                              related_name='subjects', verbose_name=_('Группа'))
    teachers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='taught_subjects',
        limit_choices_to={'role': 'teacher'}, verbose_name=_('Преподаватели'))

    class Meta:
        verbose_name = 'Предмет'
        verbose_name_plural = 'Предметы'
        ordering = ['group__name', 'name']
        constraints = [
            models.UniqueConstraint(fields=['group', 'name'], name='unique_subject_in_group'),
        ]

    def __str__(self):
        return f'{self.name} ({self.group})'


class GroupMembership(models.Model):
    """Участие студента в группе и его статус в ней."""

    class Status(models.TextChoices):
        STUDENT = 'student', _('Студент')
        HEADMAN = 'headman', _('Староста')
        RESPONSIBLE = 'responsible', _('Ответственный студент')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='memberships')
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE,
                              related_name='memberships')
    status = models.CharField(max_length=12, choices=Status.choices,
                              default=Status.STUDENT)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Участие в группе'
        verbose_name_plural = 'Участие в группах'
        constraints = [
            models.UniqueConstraint(fields=['user', 'group'], name='unique_membership'),
        ]

    def __str__(self):
        return f'{self.user} — {self.group} ({self.get_status_display()})'