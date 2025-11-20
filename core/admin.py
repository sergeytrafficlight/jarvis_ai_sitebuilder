from django.contrib import admin
from .models import Profile, Transaction, SiteProject, SystemPrompts, AICommunicationLog, AIModelsSettings, SubSiteProject, MyTask


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user",)
    search_fields = ("user__username", "user__email")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "type", "amount_client", "amount_ai", "created_at", "description")
    list_filter = ("type", "created_at")
    search_fields = ("user__username", "user__email", "description")


@admin.register(SiteProject)
class SiteProjectAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "created_at")
    list_filter = ["created_at"]
    search_fields = ("name", "user__username", "user__email")

@admin.register(SubSiteProject)
class SubSiteProjectAdmin(admin.ModelAdmin):
    list_display = ("site", "root_sub_site", "created_at", "dir", "error")
    list_filter = []
    search_fields = []

@admin.register(SystemPrompts)
class SystemPromptsAdmin(admin.ModelAdmin):
  list_display = ("type", "prompt")
  search_fields = ("prompt",)
  list_filter = ("type",)

@admin.register(AICommunicationLog)
class AICommunicationLogAdmin(admin.ModelAdmin):
  list_display = (
      "created_at", "updated_at", "task", "ai_model", "price_for_ai", "price_for_client",
      "prompt", "answer",
  )
  search_fields = ("prompt", "answer")
  list_filter = ()

@admin.register(AIModelsSettings)
class AIModelsSettingsAdmin(admin.ModelAdmin):
  list_display = ("type", "model", "prompt_tokens_price_1m", "completion_tokens_price_1m", "my_margin")
  search_fields = ("type", "model")
  list_filter = ()

  @admin.register(MyTask)
  class MyTaskAdmin(admin.ModelAdmin):
      list_display = ("created_at", "updated_at", "sub_site", "name", "type", "status", "message", "data_payload")
      search_fields = []
      list_filter = []
