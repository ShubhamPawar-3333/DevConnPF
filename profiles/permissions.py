from rest_framework.permissions import BasePermission


class IsProfileOwner(BasePermission):
    """Allow access only to the owner of the profile object."""

    def has_object_permission(self, request, view, obj):
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile == obj
        )


class IsProjectOwner(BasePermission):
    """Allow access only to the owner of the project entry's profile."""

    def has_object_permission(self, request, view, obj):
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile == obj.profile
        )
