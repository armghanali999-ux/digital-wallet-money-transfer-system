from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.api import RegisterAPIView
from administration.api import AdjustBalanceAPIView, AdminWalletListAPIView, FreezeAPIView, UnfreezeAPIView, UserListAPIView
from wallets.api import DepositAPIView, TransactionDetailAPIView, TransactionListAPIView, TransferAPIView, WalletDetailAPIView, WalletListCreateAPIView, WithdrawAPIView

urlpatterns = [
    path("auth/register/", RegisterAPIView.as_view()), path("auth/token/", TokenObtainPairView.as_view()), path("auth/token/refresh/", TokenRefreshView.as_view()),
    path("wallets/", WalletListCreateAPIView.as_view()), path("wallets/<int:pk>/", WalletDetailAPIView.as_view()),
    path("wallet/deposit/", DepositAPIView.as_view()), path("wallet/withdraw/", WithdrawAPIView.as_view()), path("wallet/transfer/", TransferAPIView.as_view()),
    path("wallet/transactions/", TransactionListAPIView.as_view()), path("wallet/transactions/<str:reference>/", TransactionDetailAPIView.as_view()),
    path("admin/users/", UserListAPIView.as_view()), path("admin/wallets/", AdminWalletListAPIView.as_view()),
    path("admin/wallets/<int:pk>/freeze/", FreezeAPIView.as_view()), path("admin/wallets/<int:pk>/unfreeze/", UnfreezeAPIView.as_view()), path("admin/wallets/<int:pk>/adjust-balance/", AdjustBalanceAPIView.as_view()),
]
