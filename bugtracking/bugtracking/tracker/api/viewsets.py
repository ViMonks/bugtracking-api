# stdlib imports

# core django imports
from django.conf import settings

# third party imports
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

# my internal imports
from ..models import Team
from . import serializers
from . import permissions

User = settings.AUTH_USER_MODEL


class TeamViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.TeamSerializer
    permission_classes = [IsAuthenticated, permissions.TeamPermissions]
    lookup_field = 'slug'

    def get_queryset(self):
        user = self.request.user
        return Team.objects.all_users_teams(user)

    def perform_create(self, serializer):
        user = self.request.user
        
