# stdlib imports

# core django imports
from django.conf import settings

# third party imports
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

# my internal imports
from ..models import Team, TeamMembership, Project, Ticket
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


class TeamMembershipViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.TeamMembershipSerializer
    # permission_classes = [IsAuthenticated]
    # TODO: adjust permission classes; or maybe doesn't matter; don't think I'll have this viewset publicly exposed; by default, it's admin only

    def get_queryset(self):
        user = self.request.user
        return TeamMembership.objects.filter(user=user)


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
    permission_classes = [IsAuthenticated] # TODO: update
    lookup_field = 'slug'

    def get_queryset(self):
        user = self.request.user
        team_slug = self.kwargs['team_slug']
        return Ticket.objects.filter_for_team_and_user(user=user, team_slug=team_slug)
