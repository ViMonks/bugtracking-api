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
        elif request.method == 'DELETE':
            return False
        return request.user in obj.get_admins()


class ProjectPermissions(BasePermission):
    """
    All project members can view a project.
    A project's manager and that project's teams' admins can edit a project.
    A team admin can create a project.
    """
    def has_permission(self, request, view):
        team = Team.objects.get(slug=view.kwargs['team_slug'])
        if request.method == 'POST':
            return request.user in team.get_admins()
        return request.user in team.members.all()

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return obj.can_user_view(request.user)
        elif request.method == 'CREATE':
            return request.user in obj.team.get_admins()
        return obj.can_user_edit(request.user)
