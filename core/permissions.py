from rest_framework import permissions

class IsTeacher(permissions.BasePermission):
    """
    Custom permission to only allow teachers to edit objects.
    """
    def has_permission(self, request, view):
        # Read permissions are allowed to any request, so we'll always allow GET, HEAD, or OPTIONS requests.
        # if request.method in permissions.SAFE_METHODS:
        #     return True

        # Write permissions are only allowed to the owner of the snippet.
        return request.user and request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'teacher'

class IsStudent(permissions.BasePermission):
    """
    Custom permission to only allow students to edit objects.
    """
    def has_permission(self, request, view):
        # Read permissions are allowed to any request, so we'll always allow GET, HEAD, or OPTIONS requests.
        # if request.method in permissions.SAFE_METHODS:
        #     return True

        return request.user and request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'student'

class IsTeacherOrAdmin(permissions.BasePermission):
    """
    Custom permission to allow teachers or administrators to manage objects.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (request.user.is_staff or (hasattr(request.user, 'profile') and request.user.profile.role == 'teacher'))
