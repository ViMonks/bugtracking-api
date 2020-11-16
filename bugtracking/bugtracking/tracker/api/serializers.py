# stdlib imports

# core django imports

# third party imports
from rest_framework import serializers

# my internal imports
from ..models import Team, TeamMembership, Project, Ticket, Comment
from bugtracking.users.api.serializers import UserSerializer


class TeamMembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = TeamMembership
        fields = ['user', 'role']
        read_only_fields = ['user', 'role']


class TeamSerializer(serializers.ModelSerializer):
    memberships = TeamMembershipSerializer(read_only=True)

    class Meta:
        model = Team
        fields = ['title', 'slug', 'description', 'members', 'memberships', 'created']
        read_only_fields = ['slug', 'created', 'members', 'memberships']

    def create(self, validated_data):
        return Team.objects.create(**validated_data)
