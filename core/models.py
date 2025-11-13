from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from core.tools import get_image_path_for_user


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
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = (
        (STATUS_DRAFT, _("Черновик")),
        (STATUS_PUBLISHED, _("Опубликован")),
        (STATUS_ARCHIVED, _("Архив")),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sites")
    name = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)

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
