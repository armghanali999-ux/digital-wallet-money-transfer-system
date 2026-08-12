import json

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import redirect, render

from accounts.forms import RegistrationForm
from accounts.services import update_theme
from accounts.themes import THEMES
from common.domain.exceptions import DomainError


def register(request):
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(); login(request, user); return redirect("dashboard")
    return render(request, "registration/register.html", {"form": form})


@login_required
def profile_settings(request):
    return render(request, "accounts/settings.html", {"themes": THEMES})


@login_required
@require_POST
def save_theme(request):
    try:
        payload = json.loads(request.body or "{}")
        selected = update_theme(request.user, payload.get("theme"), request.session)
        return JsonResponse({"success": True, "data": {"theme": selected}})
    except (json.JSONDecodeError, DomainError) as exc:
        message = exc.message if isinstance(exc, DomainError) else "Invalid request."
        code = exc.code if isinstance(exc, DomainError) else "invalid_request"
        return JsonResponse({"success": False, "error": {"code": code, "message": message}}, status=400)
