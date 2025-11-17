
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from core.tools import get_image_path_for_user

AI_MODEL_CHATGPT = "chatgpt"

AI_MODEL_LIST = [
    AI_MODEL_CHATGPT,
]


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Profile({self.user.username})"


class Transaction(models.Model):
    TYPE_TOPUP = "topup"
    TYPE_CHARGE = "charge"
    TYPE_CHOICES = (
        (TYPE_TOPUP, _("Пополнение")),
        (TYPE_CHARGE, _("Списание")),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        sign = "+" if self.type == self.TYPE_TOPUP else "-"
        return f"{self.user.email} {sign}{self.amount} {self.created_at:%Y-%m-%d}"


class SiteProject(models.Model):

    STATUS_AWAITING = "awaiting"
    STATUS_PROCESSING = "processing"
    STATUS_DONE = "done"
    STATUS_ERROR = "error"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = (
        (STATUS_AWAITING, _("Ожидает")),
        (STATUS_PROCESSING, _("Выполняется")),
        (STATUS_DONE, _("Готов")),
        (STATUS_ERROR, _("Ошибка")),
        (STATUS_ARCHIVED, _("Архив")),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sites")
    name = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_AWAITING)

    created_at = models.DateTimeField(auto_now_add=True)

    promt = models.TextField()
    ref_site_url = models.URLField(max_length=500, blank=True, null=True)


    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


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

class SystemPromts(models.Model):
    SP_NAME_BASE = "basic_promt"
    SP_NAME_CLASSIFICATION = "name_classification"
    SP_CHOICES = (
        (SP_NAME_BASE, _("Базовый промт")),
        (SP_NAME_CLASSIFICATION, _("Классификация имени сайта")),
    )

    type = models.CharField(choices=SP_CHOICES, max_length=64)
    promt = models.TextField(blank=True)



class MyTask(models.Model):
    TASK_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('STARTED', 'Started'),
        ('SUCCESS', 'Success'),
        ('FAILURE', 'Failure'),
        ('RETRY', 'Retry'),
    ]


    TYPE_GENERATE_NAME = 'generate_name'
    TYPE_GENERATE_SITE = 'generate_site'

    TYPE_CHOICES = (
        (TYPE_GENERATE_NAME, _("Генерация имени")),
        (TYPE_GENERATE_SITE, _("Генерация сайта")),
    )

    site = models.ForeignKey(SiteProject, on_delete=models.PROTECT, related_name="task")
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='PENDING')
    message = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.id}) - {self.status}"

class AICommunicationLog(models.Model):
    task = models.ForeignKey(MyTask, on_delete=models.PROTECT, related_name="log")
    ai_model = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    promt = models.TextField()
    answer = models.TextField(blank=True, null=True)

