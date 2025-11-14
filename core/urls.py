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
]
