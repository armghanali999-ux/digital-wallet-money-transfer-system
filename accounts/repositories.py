from accounts.models import User


class UserPreferenceRepository:
    @staticmethod
    def set_theme(user_id, theme):
        User.objects.filter(id=user_id).update(theme=theme)
