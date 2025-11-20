from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("billing/", views.billing_history, name="billing_history"),
    path("topup/", views.topup, name="topup"),
    path("payments/redirect/", views.payment_redirect, name="payment_gateway"),
    path("logout/", LogoutView.as_view(), name="logout"),

    path("reference_screenshot/", views.reference_screenshot, name="reference_screenshot"),
    path("users/<int:user_id>/<path:path>", views.user_file_view, name="user_file"),
    path("create_site_task/", views.create_site_task, name="create_site_task"),

    path("sites/<int:site_id>/archive/", views.site_archive, name="site_archive"),
    path("sites/bulk_archive/", views.sites_bulk_archive, name="sites_bulk_archive"),

    path("sites/<int:site_id>/", views.site_detail, name="site_detail"),
    path("api/subsite/<int:sub_id>/tasks_status/", views.subsite_tasks_status, name="subsite_tasks_status"),
    path("api/subsite/<int:sub_id>/update_text/", views.subsite_update_text, name="subsite_update_text"),

    path("api/subsite/<int:sub_id>/replace_image/", views.subsite_replace_image, name="subsite_replace_image"),
    path("api/subsite/<int:sub_id>/replace_image_by_url/", views.subsite_replace_image_by_url,
         name="subsite_replace_image_by_url"),

    path("api/subsite/<int:sub_id>/image_ai/conversations/", views.image_ai_conversations,
         name="image_ai_conversations"),
    path("api/subsite/<int:sub_id>/image_ai/create/", views.image_ai_create, name="image_ai_create"),
    path("api/site/<int:site_id>/tasks_status/", views.site_tasks_status, name="site_tasks_status"),

    path("sites/<int:site_id>/download/", views.site_download_latest, name="site_download_latest"),
    path("subsites/<int:sub_id>/download/", views.subsite_download, name="subsite_download"),

]
