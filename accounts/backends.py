from django.contrib.auth.backends import ModelBackend

from accounts.models import User


class ActiveStatusBackend(ModelBackend):
    def user_can_authenticate(self, user):
        return super().user_can_authenticate(user) and user.status == User.Status.ACTIVE
