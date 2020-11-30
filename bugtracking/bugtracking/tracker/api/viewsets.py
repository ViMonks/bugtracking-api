# stdlib imports

# core django imports
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.translation import gettext_lazy as _

# third party imports
from rest_framework import viewsets
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import ValidationError as SerializerValidationError

# my internal imports
from ..models import Team, TeamMembership, Project, Ticket, TeamInvitation
from . import serializers
from . import permissions

User = settings.AUTH_USER_MODEL


class TeamViewSet(viewsets.ModelViewSet):
    # serializer_class = serializers.TeamCreateRetrieveSerializer
    # serializer_class = serializers.TeamUpdateSerializer
    permission_classes = [IsAuthenticated, permissions.TeamPermissions]
    lookup_field = 'slug'

    def get_queryset(self):
        user = self.request.user
        return Team.objects.all_users_teams(user)

    def get_serializer_class(self):
        """
        The two serializers referenced in this method differ only in that TeamUpdateSerializer sets 'title' as a
        read-only field. This is done so that 'title' is editable and required when creating a new team,
        but is then uneditable when editing an existing team. This functionality is somewhat duplicated
        (but not completely, hence why I need this method) by the TeamPermissions class. TeamPermissions
        returns 403 Permission Denied if 'title' is in the request's update data. However, if I try to just rely
        on that and get the serializer where 'title' is editable and required, any PUT request fails with a
        400 Bad Request because 'title' is required.
        """
        if self.request.method in ['POST', 'GET']:
            serializer_class = serializers.TeamCreateRetrieveSerializer
        else:
            serializer_class = serializers.TeamUpdateSerializer
        return serializer_class

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(creator=user)

    @action(
        detail=True,
        methods=['get'],
        permission_classes=[IsAuthenticated, permissions.BeenInvitedToTeam]
    )
    def accept_invitation(self, request, **kwargs):
        try:
            invitation_id = self.request.GET.get('invitation')
            team_slug = kwargs.get('slug')
            team = Team.objects.get(slug=team_slug)
            invitation = TeamInvitation.objects.get(team=team, id=invitation_id, invitee_email=request.user.email)
            invitation.accept_invite(user=request.user)
            return Response({'status': 'Invitation accepted.'})
        except:
            return Response({'errors': 'Invitation not found.'}, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=['get'],
        permission_classes=[IsAuthenticated, permissions.BeenInvitedToTeam]
    )
    def decline_invitation(self, request, **kwargs):
        try:
            invitation_id = self.request.GET.get('invitation')
            team_slug = kwargs.get('slug')
            team = Team.objects.get(slug=team_slug)
            invitation = TeamInvitation.objects.get(team=team, id=invitation_id, invitee_email=request.user.email)
            invitation.decline_invite(user=request.user)
            return Response({'status': 'Invitation declined.'})
        except:
            return Response({'errors': 'Invitation not found.'}, status=status.HTTP_400_BAD_REQUEST)


class TeamMembershipViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.TeamMembershipSerializer
    # permission_classes = [IsAuthenticated]
    # TODO: adjust permission classes; or maybe doesn't matter; don't think I'll have this viewset publicly exposed; by default, it's admin only

    def get_queryset(self):
        user = self.request.user
        return TeamMembership.objects.filter(user=user)


class TeamInvitationViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.TeamInvitationSerializer
    permission_classes = [IsAuthenticated, permissions.TeamInvitePermissions]
    lookup_field = 'id'
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        team_slug = self.kwargs.get('team_slug')
        team = Team.objects.get(slug=team_slug)
        return TeamInvitation.objects.filter(team=team)

    def perform_create(self, serializer):
        invitee_email = self.request.data.get('invitee_email')
        if serializer.is_valid():
            inviter = self.request.user
            team_slug = self.kwargs.get('team_slug', None)
            team = Team.objects.get(slug=team_slug)
            already_a_member = team.members.filter(email=invitee_email)
            if already_a_member:
                raise SerializerValidationError({'errors': 'User is already a member of this team.'})
            serializer.save(inviter=inviter, team=team)
            return Response({'status': 'User invited.'})
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.ProjectSerializer
    permission_classes = [IsAuthenticated, permissions.ProjectPermissions]
    lookup_field = 'slug'

    def get_queryset(self):
        user = self.request.user
        team_slug = self.kwargs['team_slug']
        return Project.objects.filter_for_team_and_user(team_slug=team_slug, user=user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        team_slug = self.kwargs['team_slug']
        team = Team.objects.get(slug=team_slug)
        context['team'] = team
        # context['request'] = self.request
        return context

    def perform_create(self, serializer):
        team_slug = self.kwargs['team_slug']
        team = Team.objects.get(slug=team_slug)
        manager_username = self.kwargs.get('manager', None)
        if manager_username is not None:
            manager = User.objects.get(username=manager_username)
            serializer.save(team=team, manager=manager)
        serializer.save(team=team)


class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.TicketSerializer
    permission_classes = [IsAuthenticated, permissions.TicketPermissions]
    lookup_field = 'slug'

    def get_queryset(self):
        user = self.request.user
        team_slug = self.kwargs['team_slug']
        team = Team.objects.get(slug=team_slug)
        project_slug = self.kwargs['project_slug']
        project = Project.objects.get(slug=project_slug, team=team)
        return project.tickets.filter_for_team_and_user(user=user, team_slug=team_slug)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        team_slug = self.kwargs['team_slug']
        team = Team.objects.get(slug=team_slug)
        context['team'] = team
        project_slug = self.kwargs['project_slug']
        project = Project.objects.get(slug=project_slug, team=team)
        context['project'] = project
        context['user'] = self.request.user
        return context

    def perform_create(self, serializer):
        team_slug = self.kwargs['team_slug']
        team = Team.objects.get(slug=team_slug)
        project_slug = self.kwargs['project_slug']
        project = Project.objects.get(slug=project_slug, team=team)
        developer_username = self.kwargs.get('developer', None)
        if developer_username is not None:
            developer = User.objects.get(username=developer_username)
            serializer.save(project=project, user=self.request.user, developer=developer)
        serializer.save(project=project, user=self.request.user)
