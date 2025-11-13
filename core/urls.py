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
]
