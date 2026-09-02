from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages

def role_required(*allowed_roles):
    def decorator(view_func):
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.role in allowed_roles or request.user.role == "ADMIN":
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "Accès interdit - Permissions insuffisantes")
                return redirect("dashboard")
        return wrapper
    return decorator

