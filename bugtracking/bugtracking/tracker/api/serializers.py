# stdlib imports

# core django imports
from django.contrib.auth import get_user_model
from django.urls import reverse, reverse_lazy

# third party imports
from rest_framework import serializers

# my internal imports
from ..models import Team, TeamMembership, Project, ProjectMembership, Ticket, Comment
from bugtracking.users.api.serializers import UserSerializer

User = get_user_model()


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
    projects_list = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ['title', 'slug', 'description', 'memberships', 'created', 'url', 'projects_list', ]
        read_only_fields = ['slug', 'created', 'memberships', 'url', 'projects_list', ]
        extra_kwargs = {
            "url": {"view_name": "api:teams-detail", "lookup_field": "slug"},
        }

    def get_projects_list(self, team):
        path = reverse('api:projects-list', kwargs={'team_slug': team.slug})
        request = self.context.get('request')
        return request.build_absolute_uri(path)

    def create(self, validated_data):
        return Team.objects.create_new(**validated_data)


class TeamUpdateSerializer(TeamCreateRetrieveSerializer):
    """Adds title to the read_only_fields Meta attribute."""
    class Meta(TeamCreateRetrieveSerializer.Meta):
        read_only_fields = ['slug', 'created', 'memberships', 'title', 'url', 'projects_list', ]

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
        fields = ['user', 'role', 'role_name']
        read_only_fields = ['user', 'role']

class ManagerSlugField(serializers.SlugRelatedField):
    def get_queryset(self):
        if self.parent.instance: # meaning we're in detail view
            # return the project's members
            return self.parent.instance.members.all().prefetch_related('project_memberships')
        elif (team := self.context['team']):
            # if in list view, return all team members
            return team.members.all().prefetch_related('project_memberships')
        else:
            # if there is no team in the context, then the serializer has been called in a weird way; return all users, validate in the model
            return User.objects.all().prefetch_related('project_memberships')


class ProjectSerializer(serializers.ModelSerializer):
    """The ForAdmins serializer allows editing of the manager field. Other users' serializers do not.
    Serializer class is determined in the viewset."""
    memberships = ProjectMembershipSerializer(read_only=True, many=True)
    team = serializers.SlugRelatedField(slug_field='slug', read_only=True)
    manager = ManagerSlugField(slug_field='username', required=False, allow_null=True)
    url = serializers.SerializerMethodField()
    tickets_list = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['title', 'slug', 'description', 'team', 'is_archived', 'manager', 'memberships', 'created', 'modified', 'url', 'tickets_list']
        read_only_fields = ['slug', 'created', 'modified', 'team', 'memberships', 'url', 'tickets_list']

    def get_url(self, project):
        request = self.context.get('request', None)
        path = reverse_lazy('api:projects-detail', kwargs={'team_slug': project.team.slug, 'slug': project.slug})
        if request:
            url = request.build_absolute_uri(str(path)) # passing string path because reverse_lazy returns a proxy object
            return url
        return path

    def get_tickets_list(self, project):
        path = reverse('api:tickets-list', kwargs={'team_slug': project.team.slug, 'project_slug': project.slug})
        request = self.context.get('request')
        return request.build_absolute_uri(path)

    def create(self, validated_data):
        return Project.objects.create_new(**validated_data)

    def update(self, instance, validated_data):
        if 'manager' in validated_data:
            manager = validated_data.pop('manager')
            instance.make_manager(manager)
        return super().update(instance, validated_data)


class TicketSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = ['title', 'slug', 'description', 'priority', 'user', 'project', 'resolution', 'developer', 'is_open', 'created', 'modified', 'url',]
        read_only_fields = ['slug', 'user', 'project', 'created', 'modified', 'url',]

    def get_url(self, ticket): # speculative so far; don't know how the nested routers will work
        request = self.context.get('request', None)
        path = reverse_lazy('api:tickets-detail', kwargs={
            'team_slug': ticket.project.team.slug, 'project_slug': ticket.project.slug, 'slug': ticket.slug
        })
        if request:
            url = request.build_absolute_uri(str(path))
            return url
        return path
