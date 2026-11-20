from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Perm(models.TextChoices):
    """Список действий, которые преподаватель может разрешить студенту."""
    CREATE_TASK = 'create_task', _('Создавать задания')
    EDIT_TASK = 'edit_task', _('Редактировать задания')
    DELETE_TASK = 'delete_task', _('Удалять задания')
    VIEW_SUBMISSIONS = 'view_submissions', _('Просматривать сданные работы')
    MANAGE_QUEUE = 'manage_queue', _('Управлять очередью выступлений')
    RUN_PRESENTATION = 'run_presentation', _('Запускать режим демонстрации')
    GRADE = 'grade', _('Выставлять оценки')
    MANAGE_MEMBERS = 'manage_members', _('Управлять составом группы')


class StudyGroup(models.Model):
    """Учебная группа, например «115»."""
    name = models.CharField(_('Название группы'), max_length=50, unique=True)
    description = models.TextField(_('Описание'), blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='created_groups', verbose_name=_('Создал'))

    class Meta:
        verbose_name = 'Учебная группа'
        verbose_name_plural = 'Учебные группы'
        ordering = ['name']

    def __str__(self):
        return self.name


class Subject(models.Model):
    """Предмет внутри группы."""
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


class PermissionSet(models.Model):
    """Набор разрешений, который создаёт преподаватель (например, «Староста»)."""
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name='permission_sets')
    name = models.CharField(_('Название набора'), max_length=100)
    codes = models.JSONField(default=list)   # список кодов из Perm
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Набор разрешений'
        verbose_name_plural = 'Наборы разрешений'
        constraints = [
            models.UniqueConstraint(fields=['owner', 'name'], name='unique_permset_name'),
        ]

    def labels(self):
        """Читаемые названия разрешений набора."""
        names = dict(Perm.choices)
        return [names[c] for c in self.codes if c in names]

    def __str__(self):
        return self.name


class RoleAssignment(models.Model):
    """Назначение: студент получает набор разрешений в группе (или в одном предмете)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='role_assignments')
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE,
                              related_name='role_assignments')
    subject = models.ForeignKey(Subject, null=True, blank=True, on_delete=models.CASCADE,
                                related_name='role_assignments')   # пусто = вся группа
    permission_set = models.ForeignKey(PermissionSet, on_delete=models.CASCADE,
                                       related_name='assignments')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name='given_assignments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Назначение прав'
        verbose_name_plural = 'Назначения прав'

    def __str__(self):
        return f'{self.user} — {self.permission_set} ({self.group})'