# stdlib imports

# core django imports

# third party imports
from rest_framework.permissions import BasePermission, SAFE_METHODS

# my internal imports
from ..models import Team

class TeamPermissions(BasePermission):
    """
    All authenticated users can create a team.
    Team members can view a team.
    Team admins can update teams.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return request.user in obj.members.all()
        elif request.method == 'CREATE':
            return request.user.is_authenticated
        elif request.method == 'DELETE':
            return False
        return request.user in obj.get_admins()
