from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class IsOwnerOrAdminOrReadOnly(permissions.BasePermission):
    owner_field = "user"

    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True

        owner = getattr(obj, self.owner_field, None)
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or owner == request.user)
        )
