"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views

from common.api.views import health_check
from accounts.web import profile_settings, register, save_theme
from wallets.web import dashboard, deposit_web, history, transaction_detail, transfer_web, wallet_create, withdraw_web
from administration.web import adjust_wallet, admin_dashboard, audit_history, failed_transactions, freeze_wallet, unfreeze_wallet, user_list, wallet_detail as administration_wallet_detail, wallet_list as administration_wallet_list

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("api/", include("config.api_urls")),
    path("register/", register, name="register"),
    path("settings/", profile_settings, name="profile-settings"),
    path("settings/theme/", save_theme, name="save-theme"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", dashboard, name="dashboard"),
    path("wallets/create/", wallet_create, name="wallet-create"),
    path("deposit/", deposit_web, name="deposit"),
    path("withdraw/", withdraw_web, name="withdraw"),
    path("transfer/", transfer_web, name="transfer"),
    path("transactions/", history, name="history"),
    path("transactions/<str:reference>/", transaction_detail, name="transaction-detail"),
    path("administration/", admin_dashboard, name="administration-dashboard"),
    path("administration/users/", user_list, name="administration-users"),
    path("administration/wallets/", administration_wallet_list, name="administration-wallets"),
    path("administration/wallets/<int:pk>/", administration_wallet_detail, name="administration-wallet-detail"),
    path("administration/wallets/<int:pk>/freeze/", freeze_wallet, name="administration-freeze"),
    path("administration/wallets/<int:pk>/unfreeze/", unfreeze_wallet, name="administration-unfreeze"),
    path("administration/wallets/<int:pk>/adjust/", adjust_wallet, name="administration-adjust"),
    path("administration/failed-transactions/", failed_transactions, name="administration-failed"),
    path("administration/audits/", audit_history, name="administration-audits"),
    path("django-admin/", admin.site.urls),
]
