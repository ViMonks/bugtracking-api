# stdlib imports

# core django imports
from django.contrib.auth import get_user_model
from django.urls import reverse, reverse_lazy

# third party imports
from rest_framework import serializers
from rest_framework.fields import CurrentUserDefault

# my internal imports
from ..models import Team, TeamMembership, Project, ProjectMembership, Ticket, Comment, TeamInvitation
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
    user_is_admin = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ['title', 'slug', 'description', 'memberships', 'created', 'url', 'projects_list', 'user_is_admin', 'admins']
        read_only_fields = ['slug', 'created', 'memberships', 'url', 'projects_list', 'user_is_admin', 'admins']
        extra_kwargs = {
            "url": {"view_name": "api:teams-detail", "lookup_field": "slug"},
        }

    def get_projects_list(self, team):
        path = reverse('api:projects-list', kwargs={'team_slug': team.slug})
        request = self.context.get('request')
        return request.build_absolute_uri(path)

    def get_user_is_admin(self, team):
        user = self.context.get('request').user
        if team.is_user_admin(user):
            return True
        return False

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


class TeamInvitationSerializer(serializers.ModelSerializer):
    team = serializers.SlugRelatedField(read_only=True, slug_field='slug')
    url = serializers.SerializerMethodField()
    inviter = serializers.StringRelatedField(read_only=True)
    invitee = serializers.StringRelatedField(read_only=True)
    # invitee = serializers.SlugRelatedField(read_only=True)
    # inviter = serializers.SlugRelatedField(read_only=True)

    class Meta:
        model = TeamInvitation
        fields = ['id', 'status_name', 'team', 'invitee', 'invitee_email', 'inviter', 'message_text', 'created', 'modified', 'url']
        read_only_fields = ['id', 'status_name', 'team', 'invitee', 'inviter', 'message_text', 'created', 'modified', 'url']

    def get_url(self, invitation):
        request = self.context.get('request', None)
        path = reverse_lazy('api:invitations-detail', kwargs={'team_slug': invitation.team.slug, 'id': invitation.id})
        if request:
            url = request.build_absolute_uri(str(path)) # passing string path because reverse_lazy returns a proxy object
            return url
        return path

    def create(self, validated_data):
        invitation = TeamInvitation.objects.create_new(**validated_data)
        invitation.send_invitation_email()
        return invitation


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
    # manager = serializers.StringRelatedField(allow_null=True, required=False)
    url = serializers.SerializerMethodField()
    tickets_list = serializers.SerializerMethodField()
    user_permissions = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['title', 'slug', 'description', 'team', 'is_archived', 'manager', 'memberships', 'created', 'modified', 'url', 'tickets_list',  'open_tickets', 'user_permissions',]
        read_only_fields = ['slug', 'created', 'modified', 'team', 'memberships', 'url', 'tickets_list',  'open_tickets',]

    def get_url(self, project):
        request = self.context.get('request', None)
        path = reverse_lazy('api:projects-detail', kwargs={'team_slug': project.team.slug, 'slug': project.slug})
        if request:
            url = request.build_absolute_uri(str(path)) # passing string path because reverse_lazy returns a proxy object
            return url
        return path

    def get_user_permissions(self, project):
        user = self.context.get('request').user
        return project.get_user_project_permissions(user)

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


class DeveloperSlugField(serializers.SlugRelatedField):
    def get_queryset(self):
        if self.parent.instance: # meaning we're in detail view
            # return the project's members
            return self.parent.instance.project.members.all()
        elif (project := self.context['project']): # in list view
            # also return project members
            return project.members.all()
        else:
            # if there is no team in the context, then the serializer has been called in a weird way; return all users, validate in the model
            return User.objects.all()


class CommentSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(slug_field='username', read_only=True)
    ticket = serializers.SlugRelatedField(slug_field='slug', read_only=True)

    class Meta:
        model = Comment
        fields = ['user', 'ticket', 'text', 'created']
        read_only_fields = ['user', 'created',]

    def create(self, validated_data):
        return Comment.objects.create_new(**validated_data)


class TicketSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    developer = DeveloperSlugField(slug_field='username', required=False, allow_null=True)
    comments = CommentSerializer(read_only=True, many=True)
    user = serializers.StringRelatedField(read_only=True)
    user_permissions = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = ['title', 'slug', 'description', 'priority', 'user', 'project', 'resolution', 'developer', 'is_open', 'created', 'modified', 'url', 'comments', 'user_permissions']
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

    def get_user_permissions(self, ticket):
        user = self.context.get('request').user
        return ticket.get_user_ticket_permissions(user)

    def create(self, validated_data):
        return Ticket.objects.create_new(**validated_data)
