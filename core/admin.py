from django.contrib import admin
from .models import Profile, Transaction, SiteProject, SystemPrompts, AICommunicationLog, AIModelsSettings


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
