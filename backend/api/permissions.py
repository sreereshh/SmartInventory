from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminRole(BasePermission):
    message = "Only administrators can perform this action."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin_role)


class AdminDeletesOnly(BasePermission):
    """
    Role-based access control for CRUD endpoints:
    - Admin and Staff: list / retrieve / create / update
    - Admin only: delete
    """

    message = "Only administrators can delete records."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_active):
            return False
        if request.method == "DELETE":
            return user.is_admin_role
        return True
