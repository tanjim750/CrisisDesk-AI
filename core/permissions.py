try:
    from rest_framework.permissions import BasePermission
except ImportError:
    class BasePermission:
        pass


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
        )
