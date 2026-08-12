from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.serializers import UserSerializer
from administration.models import AdministrativeAudit
from wallets.models import Wallet
from wallets.serializers import AdjustmentSerializer, WalletSerializer
from wallets.services import adjust_balance, set_wallet_frozen


class IsAdministrator(permissions.BasePermission):
    def has_permission(self, request, view): return bool(request.user.is_authenticated and (request.user.is_staff or request.user.role == "ADMIN"))


class UserListAPIView(generics.ListAPIView):
    permission_classes = [IsAdministrator]; serializer_class = UserSerializer; queryset = User.objects.all().order_by("-created_at")


class AdminWalletListAPIView(generics.ListAPIView):
    permission_classes = [IsAdministrator]; serializer_class = WalletSerializer
    def get_queryset(self):
        qs = Wallet.objects.select_related("owner").all().order_by("-created_at"); q = self.request.query_params.get("q")
        return qs.filter(owner__email__icontains=q) if q else qs


class WalletStatusAPIView(APIView):
    permission_classes = [IsAdministrator]; freeze = True
    def post(self, request, pk):
        wallet = set_wallet_frozen(request.user, pk, self.freeze, request.data.get("reason", ""))
        return Response({"success": True, "data": WalletSerializer(wallet).data})


class FreezeAPIView(WalletStatusAPIView): freeze = True
class UnfreezeAPIView(WalletStatusAPIView): freeze = False


class AdjustBalanceAPIView(APIView):
    permission_classes = [IsAdministrator]
    def post(self, request, pk):
        serializer = AdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = adjust_balance(request.user, pk, serializer.validated_data["amount"], serializer.validated_data["reason"], request.headers.get("Idempotency-Key"))
        return Response({"success": True, "data": result})
