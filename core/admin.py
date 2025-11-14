from django.contrib import admin
from .models import Profile, Transaction, SiteProject


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "balance")
    search_fields = ("user__username", "user__email")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "type", "amount", "created_at", "description")
    list_filter = ("type", "created_at")
    search_fields = ("user__username", "user__email", "description")


@admin.register(SiteProject)
class SiteProjectAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "user__username", "user__email")


from .models import Profile, Transaction, SiteProject, SystemPromts

@admin.register(SystemPromts)
class SystemPromtsAdmin(admin.ModelAdmin):
  list_display = ("type", "promt")
  search_fields = ("promt",)
  list_filter = ("type",)
