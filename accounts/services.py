from common.domain.exceptions import DomainError
from accounts.repositories import UserPreferenceRepository
from accounts.themes import THEMES


def update_theme(user, selected_theme, session):
    if selected_theme not in THEMES:
        raise DomainError("Select a valid theme.", "invalid_theme")
    UserPreferenceRepository.set_theme(user.id, selected_theme)
    user.theme = selected_theme
    session["selected_theme"] = selected_theme
    session.modified = True
    return selected_theme
