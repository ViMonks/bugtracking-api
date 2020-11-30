# stdlib imports

# core django imports

# third party imports
from rest_framework.permissions import BasePermission, SAFE_METHODS

# my internal imports
from ..models import Team, Project

class TeamPermissions(BasePermission):
    """
    View permissions: Team members can view a team.
    Edit permissions: Team admins can update teams.
    Create permissions: All authenticated users can create a team.
    """
    message = {'errors': 'Permission denied.'} # this is just a fallback; message will be customized in permission checks

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return request.user in obj.members.all()
        elif request.method == 'DELETE':
            self.message['errors'] = 'Teams cannot be deleted.'
            return False
        if 'title' in request.data:
            self.message['errors'] = 'Team titles cannot be changed after creation.'
            return False
        return request.user in obj.get_admins()


class TeamInvitePermissionsForAction(BasePermission):
    """
    Only team admins may invite new members.
    """
    message = {'errors': 'Permission denied.'}

    def has_object_permission(self, request, view, obj):
        if request.user in obj.get_admins():
            return True
        self.message['errors'] = 'Only team administrators may invite new members.'
        return False


class TeamInvitePermissions(BasePermission):
    """
    Only team admins may view team invitations or invite new members.
    """
    message = {'errors': 'Permission denied.'}

    def has_permission(self, request, view):
        team = Team.objects.get(slug=view.kwargs['team_slug'])
        if request.user in team.get_admins():
            return True
        self.message['errors'] = "Only a team administrator may view or manage team invitations."
        return False

    def has_object_permission(self, request, view, obj):
        if request.user in obj.team.get_admins():
            return True
        self.message['errors'] = "Only a team administrator may view or manage team invitations."
        return False


class BeenInvitedToTeam(BasePermission):
    """
    Tests to see whether the requesting user has been invited to the team.
    """
    message = {'errors': 'You have not been invited to this team.'}

    def has_object_permission(self, request, view, obj):
        invitations = obj.invitations_set.filter(invitee_email=request.user.email)
        if invitations:
            return True
        return False



class ProjectPermissions(BasePermission):
    """
    View permissions: All project members can view a project.
    Edit permissions: project's manager and that project's teams' admins.
    Only team admins may change the project's manager.
    Create permissions: A team admin can create a project.
    """
    message = {'errors': 'Permission denied.'} # this is just a fallback; message will be customized in permission checks

    def has_permission(self, request, view):
        team = Team.objects.get(slug=view.kwargs['team_slug'])
        if request.method == 'POST':
            if request.user in team.get_admins():
                return True
            else:
                self.message['errors'] = "Only a team admin may post a new project."
                return False
        return request.user in team.members.all()

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return obj.can_user_view(request.user)
        elif request.method == 'CREATE':
            return request.user in obj.team.get_admins()
        if 'manager' in request.data and not obj.can_user_update_manager(request.user):
            self.message['errors'] = "Only a team admin may change the manager of a project."
            return False
        return obj.can_user_edit(request.user)


class TicketPermissions(BasePermission):
    """
    View permissions: All project members can view all tickets; team admin can view all tickets.
    Edit permissions: Team admins, project manager, ticket's assigned developer, ticket's creator.
    Only team admins and project managers may update a ticket's assigned developer.
    Create permissions: All project members.
    """
    message = {'errors': 'Permission denied.'}

    def has_permission(self, request, view):
        team = Team.objects.get(slug=view.kwargs['team_slug'])
        project = Project.objects.get(slug=view.kwargs['project_slug'])
        if request.method == 'POST':
            if project.can_user_create_tickets(request.user):
                return True
            else:
                self.message['errors'] = "Only project members may submit tickets to a project."
                return False
        return request.user in project.members.all() or request.user in team.get_admins()

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return obj.can_user_view(request.user)
        if 'developer' in request.data:
            if not obj.can_user_change_developer(request.user):
                self.message['errors'] = "Only team admins and project managers may change a ticket's assigned developer."
                return False
            else:
                return True
        if request.method == 'DELETE':
            return obj.can_user_delete(request.user)
        return obj.can_user_edit(request.user)
