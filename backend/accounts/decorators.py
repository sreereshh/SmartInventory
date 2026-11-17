from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def admin_required(view_func):
    """Login required AND the user must have the Admin role (otherwise HTTP 403)."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_admin_role:
            raise PermissionDenied("This action is restricted to administrators.")
        return view_func(request, *args, **kwargs)

    return _wrapped
