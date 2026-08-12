from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def health_check(request):
    return Response({"success": True, "data": {"status": "ok"}})
