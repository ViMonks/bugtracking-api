# stdlib imports

# core django imports
from django.conf import settings

# third party imports
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

# my internal imports
from ..models import Team, TeamMembership
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
    permission_classes = [IsAuthenticated]
    # TODO: adjust permission classes

    def get_queryset(self):
        user = self.request.user
        return TeamMembership.objects.filter(user=user)
