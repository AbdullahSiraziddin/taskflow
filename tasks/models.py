from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# Какие расширения файлов относятся к какому формату (понадобится в Части 4)
FORMAT_EXTENSIONS = {
    'document': ['.doc', '.docx', '.odt', '.rtf', '.txt'],
    'pdf': ['.pdf'],
    'presentation': ['.ppt', '.pptx', '.odp'],
    'table': ['.xls', '.xlsx', '.ods', '.csv'],
    'image': ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
    'video': ['.mp4', '.webm', '.mov'],
    'archive': ['.zip'],
}


class Task(models.Model):
    """Учебное задание."""

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Черновик')
        PUBLISHED = 'published', _('Опубликовано')
        PAUSED = 'paused', _('Приостановлено')
        CLOSED = 'closed', _('Сдача закрыта')
        ARCHIVED = 'archived', _('В архиве')

    class Format(models.TextChoices):
        DOCUMENT = 'document', _('Документ (DOC, DOCX, TXT)')
        PDF = 'pdf', _('PDF')
        PRESENTATION = 'presentation', _('Презентация (PPT, PPTX)')
        TABLE = 'table', _('Таблица (XLS, XLSX, CSV)')
        IMAGE = 'image', _('Изображение (JPG, PNG)')
        VIDEO = 'video', _('Видео (MP4, WEBM)')
        ARCHIVE = 'archive', _('Архив ZIP')
        LINK = 'link', _('Ссылка')
        TEXT = 'text', _('Текстовый ответ на сайте')

    # Состояние на экране: (название, css для значка, css для карточки)
    STATE_META = {
        'draft': (_('Черновик'), 'st-draft', 'c-violet'),
        'upcoming': (_('Скоро откроется'), 'st-upcoming', 'c-blue'),
        'open': (_('Сдача открыта'), 'st-open', 'c-green'),
        'expired': (_('Срок истёк'), 'st-expired', 'c-red'),
        'paused': (_('Приостановлено'), 'st-paused', 'c-yellow'),
        'closed': (_('Сдача закрыта'), 'st-closed', 'c-violet'),
        'archived': (_('В архиве'), 'st-archived', 'c-violet'),
    }

    title = models.CharField(_('Название'), max_length=200)
    description = models.TextField(_('Краткое описание'), blank=True)
    instructions = models.TextField(_('Инструкции и требования'), blank=True)

    group = models.ForeignKey('academics.StudyGroup', on_delete=models.CASCADE,
                              related_name='tasks', verbose_name=_('Группа'))
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE,
                                related_name='tasks', verbose_name=_('Предмет'))
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                               on_delete=models.SET_NULL, related_name='created_tasks',
                               verbose_name=_('Автор'))

    start_at = models.DateTimeField(_('Начало выполнения'))
    deadline = models.DateTimeField(_('Дедлайн (окончание сдачи)'))

    allowed_formats = models.JSONField(_('Разрешённые форматы материалов'), default=list)
    max_files = models.PositiveSmallIntegerField(
        _('Максимум файлов'), default=5,
        validators=[MinValueValidator(1), MaxValueValidator(10)])
    max_file_mb = models.PositiveSmallIntegerField(
        _('Максимальный размер файла (МБ)'), default=10,
        validators=[MinValueValidator(1), MaxValueValidator(50)])

    requires_presentation = models.BooleanField(_('Нужно выступление'), default=False)
    presentation_minutes = models.PositiveSmallIntegerField(
        _('Длительность выступления (минут)'), null=True, blank=True)

    max_score = models.PositiveSmallIntegerField(
        _('Максимальная оценка'), default=100,
        validators=[MinValueValidator(1), MaxValueValidator(100)])

    allow_resubmission = models.BooleanField(_('Разрешить повторную сдачу'), default=False)
    resubmission_deadline = models.DateTimeField(
        _('Дедлайн повторной сдачи'), null=True, blank=True)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Задание'
        verbose_name_plural = 'Задания'
        ordering = ['deadline']

    def __str__(self):
        return self.title

    @property
    def state(self):
        """Что показывать пользователю: статус + сравнение дат с серверным временем."""
        if self.status != self.Status.PUBLISHED:
            return self.status
        now = timezone.now()
        if now < self.start_at:
            return 'upcoming'
        if now > self.deadline:
            return 'expired'
        return 'open'

    @property
    def state_label(self):
        return self.STATE_META[self.state][0]

    @property
    def state_css(self):
        return self.STATE_META[self.state][1]

    @property
    def card_css(self):
        return self.STATE_META[self.state][2]

    @property
    def formats_display(self):
        names = dict(self.Format.choices)
        return [names[c] for c in self.allowed_formats if c in names]

    def allowed_extensions(self):
        exts = set()
        for code in self.allowed_formats:
            exts.update(FORMAT_EXTENSIONS.get(code, []))
        return exts


# Допустимые действия: код -> (из каких статусов, в какой статус)
TASK_ACTIONS = {
    'publish': (('draft',), 'published'),
    'pause': (('published',), 'paused'),
    'resume': (('paused', 'closed'), 'published'),
    'close': (('published', 'paused'), 'closed'),
    'archive': (('published', 'paused', 'closed'), 'archived'),
    'restore': (('archived',), 'closed'),
}
ACTION_LABELS = {
    'publish': _('Опубликовать'),
    'pause': _('Приостановить'),
    'resume': _('Открыть снова'),
    'close': _('Закрыть сдачу'),
    'archive': _('В архив'),
    'restore': _('Вернуть из архива'),
}


class TaskLog(models.Model):
    """История важных действий с заданием."""

    class Action(models.TextChoices):
        CREATED = 'created', _('Создано')
        UPDATED = 'updated', _('Изменено')
        STATUS = 'status', _('Смена статуса')

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL)
    action = models.CharField(max_length=10, choices=Action.choices)
    details = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def details_display(self):
        """Человекочитаемые подробности на языке интерфейса."""
        if self.action == self.Action.UPDATED:
            names = []
            for field_name in self.details.split(','):
                try:
                    names.append(str(Task._meta.get_field(field_name).verbose_name))
                except FieldDoesNotExist:
                    pass
            return ', '.join(names)
        if self.action == self.Action.STATUS:
            try:
                return str(Task.Status(self.details).label)
            except ValueError:
                return ''
        return ''