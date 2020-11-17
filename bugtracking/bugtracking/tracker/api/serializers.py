# stdlib imports

# core django imports

# third party imports
from rest_framework import serializers

# my internal imports
from ..models import Team, TeamMembership, Project, ProjectMembership, Ticket, Comment
from bugtracking.users.api.serializers import UserSerializer


# TEAMS-RELATED SERIALIZERS
class TeamMembershipSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = TeamMembership
        fields = ['user', 'role', 'role_name']
        read_only_fields = ['user', 'role', ]


class TeamCreateRetrieveSerializer(serializers.ModelSerializer):
    memberships = TeamMembershipSerializer(read_only=True, many=True)
    # members = UserSerializer(many=True)

    class Meta:
        model = Team
        fields = ['title', 'slug', 'description', 'memberships', 'created', 'url']
        read_only_fields = ['slug', 'created', 'memberships',]
        extra_kwargs = {
            "url": {"view_name": "api:teams-detail", "lookup_field": "slug"}
        }

    def create(self, validated_data):
        return Team.objects.create_new(**validated_data)

class TeamUpdateSerializer(TeamCreateRetrieveSerializer):

    class Meta(TeamCreateRetrieveSerializer.Meta):
        read_only_fields = ['slug', 'created', 'memberships', 'title',]

    def update(self, instance, validated_data):
        if 'title' in validated_data:
            raise serializers.ValidationError({
                'title': 'A team\'s title field cannot be updated after team creation.'
            })
        return super().update(instance, validated_data)


# PROJECT-RELATED SERIALIZERS
class ProjectMembershipSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = ProjectMembership
        fields = ['user', 'role']
        read_only_fields = ['role']


class ProjectSerializer(serializers.ModelSerializer):
    pass
