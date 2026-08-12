from types import MappingProxyType


THEMES = MappingProxyType({
    "emerald_finance": {
        "name": "Emerald Finance", "primary": "#14532D", "secondary": "#16A34A",
        "accent": "#22C55E", "background": "#F8FAFC", "text": "#17201B",
    },
    "navy_teal_fintech": {
        "name": "Navy Teal Fintech", "primary": "#0F172A", "secondary": "#14B8A6",
        "accent": "#06B6D4", "background": "#F8FAFC", "text": "#172033",
    },
    "indigo_professional": {
        "name": "Indigo Professional", "primary": "#4338CA", "secondary": "#6366F1",
        "accent": "#818CF8", "background": "#F8FAFC", "text": "#1E1B4B",
    },
    "premium_black_gold": {
        "name": "Premium Black Gold", "primary": "#111827", "secondary": "#D4AF37",
        "accent": "#F5C542", "background": "#FAF7F0", "text": "#241F15",
    },
    "classic_blue": {
        "name": "Classic Blue", "primary": "#1D4ED8", "secondary": "#2563EB",
        "accent": "#60A5FA", "background": "#F8FAFC", "text": "#172554",
    },
    "dark_mode": {
        "name": "Dark Mode", "primary": "#0F172A", "secondary": "#1E293B",
        "accent": "#14B8A6", "background": "#0B1120", "text": "#F8FAFC",
    },
})

DEFAULT_THEME = "emerald_finance"
THEME_CHOICES = tuple((key, value["name"]) for key, value in THEMES.items())


def valid_theme(value):
    return value if value in THEMES else DEFAULT_THEME
