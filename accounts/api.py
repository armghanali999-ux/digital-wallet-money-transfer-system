from rest_framework import generics, permissions

from accounts.serializers import RegistrationSerializer


class RegisterAPIView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [permissions.AllowAny]
