from accounts.themes import DEFAULT_THEME, THEMES, valid_theme


def theme_context(request):
    selected = DEFAULT_THEME
    if request.user.is_authenticated:
        selected = valid_theme(request.session.get("selected_theme") or request.user.theme)
        if request.session.get("selected_theme") != selected:
            request.session["selected_theme"] = selected
    return {"selected_theme": selected, "available_themes": THEMES}
