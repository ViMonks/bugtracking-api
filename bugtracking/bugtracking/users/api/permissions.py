from rest_framework.permissions import BasePermission, SAFE_METHODS

class UserPermissions(BasePermission):

    message = {'errors': 'Permission denied.'}

    def has_object_permission(self, request, view, obj):
        return request.user == obj
