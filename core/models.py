
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from core.tools import get_image_path_for_user


TYPE_CHATGPT = 'CHATGPT'
TYPE_DEEPSEEK = 'DEEPSEEK'

TYPE_CHOICES = (
    (TYPE_CHATGPT, TYPE_CHATGPT),
    (TYPE_DEEPSEEK, TYPE_DEEPSEEK),
)

MODEL_CHATGPT_5 = 'gpt-5'
MODEL_CHATGPT_5_1 = 'gpt-5.1'
MODEL_CHATGPT_IMG_1 = 'gpt-image-1'
MODEL_DEEP_SEEK_CHAT = 'deepseek-chat'
MODEL_DEEP_SEEK_REASONER = 'deepseek-reasoner'
MODEL_CHOICES = (
    (MODEL_CHATGPT_5, MODEL_CHATGPT_5),
    (MODEL_CHATGPT_5_1, MODEL_CHATGPT_5_1),
    (MODEL_CHATGPT_IMG_1, MODEL_CHATGPT_IMG_1),
    (MODEL_DEEP_SEEK_CHAT, MODEL_DEEP_SEEK_CHAT),
    (MODEL_DEEP_SEEK_REASONER, MODEL_DEEP_SEEK_REASONER),
)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    def get_balance(self):
        from core.funds_balance import balance
        return balance(user=self.user)

    def __str__(self):
        return f"Profile({self.user.username})"


class Transaction(models.Model):
    TYPE_TOPUP = "topup"
    TYPE_CHARGE = "charge"
    TYPE_CHOICES = (
        (TYPE_TOPUP, _("Пополнение")),
        (TYPE_CHARGE, _("Списание")),
    )

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="transactions")
    amount_client = models.DecimalField(max_digits=10, decimal_places=6)
    amount_ai = models.DecimalField(max_digits=10, decimal_places=6)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    sub_site = models.ForeignKey('SubSiteProject', on_delete=models.SET_NULL, null=True, blank=True, default=None, related_name="transactions")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):

        return f"{self.user.email} {self.created_at:%Y-%m-%d}"


class MyTask(models.Model):

    STATUS_AWAITING = "awaiting"
    STATUS_PROCESSING = "processing"
    STATUS_DONE = "done"
    STATUS_ERROR = "error"

    STATUS_CHOICES = (
        (STATUS_AWAITING, _("Ожидает")),
        (STATUS_PROCESSING, _("Выполняется")),
        (STATUS_DONE, _("Готов")),
        (STATUS_ERROR, _("Ошибка")),
    )


    TYPE_GENERATE_NAME = 'generate_name'
    TYPE_GENERATE_SITE = 'generate_site'
    TYPE_GENERATE_IMAGE = 'generate_image'
    TYPE_EDIT_IMAGE = 'edit_image'
    TYPE_EDIT_SITE = 'edit_site'
    TYPE_EDIT_FILE = 'edit_file'

    TYPE_CHOICES = (
        (TYPE_GENERATE_NAME, _("Генерация имени")),
        (TYPE_GENERATE_SITE, _("Генерация сайта")),
        (TYPE_GENERATE_IMAGE, _("Генерация изображения")),
        (TYPE_EDIT_IMAGE, _("Редактирование изображения")),
        (TYPE_EDIT_SITE, _("Редактирование сайта")),
        (TYPE_EDIT_FILE, _("Редактирование файла")),

    )

    sub_site = models.ForeignKey('SubSiteProject', on_delete=models.PROTECT, related_name="task")
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_AWAITING)
    message = models.TextField(blank=True, null=True)

    data_payload = models.JSONField(
        default=dict,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.id}) - {self.type} {self.status}"

class SiteProject(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sites")
    name = models.CharField(max_length=120)

    created_at = models.DateTimeField(auto_now_add=True)
    is_archived = models.BooleanField(default=False)

    prompt = models.TextField()
    ref_site_url = models.URLField(max_length=500, blank=True, null=True)

    def get_balance(self):
        from core.funds_balance import balance
        return balance(site=self)

    def get_status(self):
        for t in MyTask.objects.filter(sub_site__site=self).all():
            if t.status in [MyTask.STATUS_AWAITING, MyTask.STATUS_PROCESSING]:
                return MyTask.STATUS_PROCESSING
        return MyTask.STATUS_DONE

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name}"

class SubSiteProject(models.Model):

    site = models.ForeignKey(SiteProject, on_delete=models.CASCADE, related_name="sub_site")
    root_sub_site = models.ForeignKey('SubSiteProject', on_delete=models.CASCADE, related_name="sub_site", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    dir = models.CharField(max_length=64)

    error = models.TextField(null=True, blank=True)

    def get_status(self):
        for t in MyTask.objects.filter(sub_site=self).all():
            if t.status in [MyTask.STATUS_AWAITING, MyTask.STATUS_PROCESSING]:
                return MyTask.STATUS_PROCESSING
        return MyTask.STATUS_DONE

    def get_balance(self):
        from core.funds_balance import balance
        return balance(sub_site=self)



@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

def image_upload_path(instance, filename):
    return f"{get_image_path_for_user(instance.user)}/{filename}"

class GeneratedImage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=image_upload_path)
    created_at = models.DateTimeField(auto_now_add=True)

class SystemPrompts(models.Model):
    SP_NAME_BASE = "basic_prompt"
    SP_NAME_CLASSIFICATION = "name_classification"
    SP_NAME_BASE_JSON = "basic_json"
    SP_NAME_GENERATE_FOR_SITE_IMAGE = "generate_image_for_site"
    SP_NAME_I_HAVE_PAGE_SCREENSHOT = "i_have_page_screenshot"
    SP_NAME_SITE_EDIT_MAKE_PLAN = "site_edit_make_plan"

    SP_CHOICES = (
        (SP_NAME_BASE, _("Базовый промт")),
        (SP_NAME_CLASSIFICATION, _("Классификация имени сайта")),
        (SP_NAME_BASE_JSON, _("JSON коммуникация")),
        (SP_NAME_GENERATE_FOR_SITE_IMAGE, _("Генерация картинки для сайта")),
        (SP_NAME_I_HAVE_PAGE_SCREENSHOT, _("У меня есть скриншот картинки")),
        (SP_NAME_SITE_EDIT_MAKE_PLAN, _("Создание плана редактирования сайта")),
    )

    type = models.CharField(choices=SP_CHOICES, max_length=64)
    prompt = models.TextField(blank=True)



class AICommunicationLog(models.Model):
    task = models.ForeignKey(MyTask, on_delete=models.PROTECT, related_name="log")
    ai_type = models.CharField(max_length=20, choices=TYPE_CHOICES, null=True, blank=True, default=None)
    ai_model = models.CharField(max_length=20, choices=MODEL_CHOICES, null=True, blank=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    prompt = models.TextField()
    answer = models.TextField(blank=True, null=True)

    prompt_tokens = models.IntegerField(default=None, blank=True, null=True)
    completion_tokens = models.IntegerField(default=None, blank=True, null=True)
    price_for_ai = models.DecimalField(max_digits=14, decimal_places=6, default=None, blank=True, null=True)
    price_for_client = models.DecimalField(max_digits=14, decimal_places=6, default=None, blank=True, null=True)


class AIModelsSettings(models.Model):


    FORMAT_TXT = 'text'
    FORMAT_IMAGE = 'image'

    FORMAT_CHOICES = (
        (FORMAT_TXT, FORMAT_TXT),
        (FORMAT_IMAGE, FORMAT_IMAGE),
    )

    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    model = models.CharField(max_length=20, choices=MODEL_CHOICES)
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES)

    prompt_tokens_price_1m = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    completion_tokens_price_1m = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    my_margin = models.FloatField(default=2, validators=[MinValueValidator(1.0)] )

    class Meta:
        unique_together = [
            ("type", "model"),
        ]

class ImageAIEdit(models.Model):
    sub_site = models.ForeignKey(SubSiteProject, on_delete=models.CASCADE, related_name="image_ai")

    file_path = models.CharField(max_length=256)

    class Meta:
        unique_together = [
            ("sub_site", "file_path"),
        ]

class ImageAIEditConversation(models.Model):

    image_ai_edit = models.ForeignKey(ImageAIEdit, on_delete=models.CASCADE, related_name="image_ai", blank=True, null=True, default=None)
    prompt = models.TextField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    answer_id = models.CharField(max_length=256)

    task = models.ForeignKey(MyTask, on_delete=models.CASCADE, related_name="image_ai")

    def get_status(self):
        if self.task_id is None:
            return MyTask.STATUS_AWAITING
        else:
            return self.task.status