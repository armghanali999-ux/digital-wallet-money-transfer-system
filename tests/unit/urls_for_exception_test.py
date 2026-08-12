from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from common.domain.exceptions import ConflictError


@api_view(["GET"])
@permission_classes([AllowAny])
def domain_error_view(request):
    raise ConflictError("Safe conflict.")


urlpatterns = [path("domain-error/", domain_error_view)]
