# stdlib imports
import uuid

# core django imports
from django.db import models
from django.conf import settings
from django.core import mail
from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError, ObjectDoesNotExist, PermissionDenied
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

# third party imports
from django_extensions.db.models import TitleSlugDescriptionModel, TimeStampedModel
from django_extensions.db.fields import CreationDateTimeField

# my internal imports


User = settings.AUTH_USER_MODEL

# CUSTOM MANGERS

class TeamManager(models.Manager):
    def create_new(self, *args, **kwargs):
        if 'creator' in kwargs:
            creator = kwargs.pop('creator')
            if not isinstance(creator, get_user_model()):
                raise ValidationError(_('Creator argument must be a User object. If you wish to pass a username string, use the create_new_by_username() method instead.'))
            team = super().create(*args, **kwargs)
            membership = TeamMembership.objects.create(user=creator, team=team, role=TeamMembership.Roles.ADMIN)
            membership.save()
            return team
        else:
            raise ValidationError(_("The create_new() method must be passed a `creator`=User kwarg to assign an initial administrator."))

    def create_new_by_username(self, *args, **kwargs):
        if 'creator' in kwargs:
            creator = kwargs.pop('creator')
            if not isinstance(creator, str):
                raise ValidationError(_('Creator argument must be a string equal to a username. If you wish to pass a User object as the creator argument, use the create_new() model method instead.'))
            try:
                creator = get_user_model().objects.get(username=creator)
            except ObjectDoesNotExist:
                raise ObjectDoesNotExist(_("User by that username does not exist."))
            team = super().create(*args, **kwargs)
            membership = TeamMembership.objects.create(user=creator, team=team, role=TeamMembership.Roles.ADMIN)
            membership.save()
            return team
        else:
            raise ValidationError(_("The create_new_by_username() method must be passed a `creator`=User kwarg to assign an initial administrator."))


class TeamInvitationManager(models.Manager):
    def create_new(self, *args, **kwargs):
        if 'inviter' in kwargs and 'team' in kwargs:
            inviter = kwargs.get('inviter')
            team = kwargs.get('team')
            if not isinstance(inviter, get_user_model()):
                raise ValidationError(_('Inviter parameter must be a valid User object.'))
            if not isinstance(team, Team):
                raise ValidationError(_('Team parameter must be a valid Team object.'))
            message_text = 'Test'
            invitation = TeamInvitation.objects.create(inviter=inviter, team=team, invitee_email=kwargs.get('invitee_email'), message_text=message_text)
            return invitation
        else:
            raise ValidationError(_("You must pass in a team and inviter parameter."))


class ProjectManager(models.Manager):
    def create_new(self, *args, **kwargs):
        if 'manager' in kwargs and kwargs['manager'] is not None:
            manager = kwargs['manager']
            if not isinstance(manager, get_user_model()):
                raise ValidationError(_('Manager argument must be a User object.'))
            project = super().create(*args, **kwargs)
            membership = ProjectMembership.objects.create(user=manager, project=project, role=ProjectMembership.Roles.MANAGER)
            membership.save()
            return project
        return super().create(*args, **kwargs)


class TicketManager(models.Manager):
    def create_new(self, *args, **kwargs):
        if 'project' not in kwargs or not isinstance(kwargs['project'], Project):
            raise ValidationError(_('Project argument must be provided and must be a Project object.'))
        project = kwargs['project']
        if 'user' in kwargs and kwargs['user'] is not None:
            user = kwargs['user']
            if not isinstance(user, get_user_model()):
                raise ValidationError(_('User argument must be a User object.'))
            if not project.can_user_create_tickets(user):
                raise PermissionDenied(_('Only project members or team admins may create tickets.'))
        else:
            raise ValidationError(_('User argument must be provided.'))
        if 'developer' in kwargs and kwargs['developer'] is not None:
            developer = kwargs['developer']
            if not isinstance(developer, get_user_model()):
                raise ValidationError(_('Developer argument must be a User object.'))
            # only project managers or team admins may assign a developer
            if user not in project.team.get_admins() and user != project.manager:
                raise PermissionDenied(_('Only project managers or team admins may assign a developer.'))
            if developer not in project.members.all():
                raise ValidationError(_('Only project members may be assigned as a ticket\'s developer.'))
        return super().create(*args, **kwargs)



# CUSTOM QUERYSETS

class TeamQueryset(models.QuerySet):
    def users_admin_teams(self, user):
        return self.filter(memberships__role=TeamMembership.Roles.ADMIN, memberships__user=user).distinct()

    def users_member_teams(self, user):
        return self.filter(memberships__role=TeamMembership.Roles.MEMBER, memberships__user=user).distinct()

    def all_users_teams(self, user):
        return self.filter(memberships__user=user).distinct()


class ProjectQueryset(models.QuerySet):
    def filter_for_team_and_user(self, team_slug, user):
        team = Team.objects.get(slug=team_slug)
        if user in team.get_admins():
            return self.filter(team__slug=team_slug).distinct()
        return self.filter(members=user, team__slug=team_slug).distinct()


class TicketQueryset(models.QuerySet):
    def filter_for_team_and_user(self, team_slug, user):
        team = Team.objects.get(slug=team_slug)
        if user in team.get_admins():
            return self.filter(project__team__slug=team_slug).distinct()
        return self.filter(project__members=user, project__team__slug=team_slug).distinct()


# TEAM AND RELATED THROUGH MODELS

class Team(TitleSlugDescriptionModel, models.Model):
    """
    The top level organizational unit for the app. A team is a collection of members and projects (which are a collection of tickets) that define a single organization
    working together on different projects. Teams have members of two classes: administrators and members.
    An example of a team might be a company, which has employees (members) with different roles and different projects that they are working on at any given time.
    """
    members = models.ManyToManyField(User, related_name='teams', through='TeamMembership')
    created = CreationDateTimeField() # implements a creation timestamp
    # the `TitleSlugDescriptionModel` implements title, slug, and description fields, with the slug based on the team's title

    objects = TeamManager.from_queryset(TeamQueryset)()

    def __str__(self):
        return f'<Title: {self.title}, Slug: {self.slug}>'

    def get_admins(self):
        return self.members.filter(team_memberships__role=TeamMembership.Roles.ADMIN, team_memberships__team=self)

    @property
    def admins(self):
        admins_names = []
        for name in self.get_admins():
            admins_names.append(name.username)
        return admins_names

    def get_non_admins(self):
        return self.members.filter(team_memberships__role=TeamMembership.Roles.MEMBER, team_memberships__team=self)

    @property
    def non_admins(self):
        non_admins_names = []
        for name in self.get_non_admins():
            non_admins_names.append(name.username)
        return non_admins_names

    @property # currently unused
    def projects_url(self):
        from django.contrib.sites.models import Site
        domain = Site.objects.get_current().domain
        path = reverse('api:projects-list', kwargs={'team_slug': self.slug})
        return f'https://{domain}{path}'

    def make_admin(self, user):
        if user in self.get_admins():
            return
        try:
            membership = self.memberships.get(user=user)
            membership.role = membership.Roles.ADMIN
            membership.save()
        except ObjectDoesNotExist:
            raise ValidationError(_('Cannot make user an admin. User is not a member of your team.'))

    def add_member(self, user):
        if user in self.members.all():
            return
        membership = TeamMembership.objects.create(team=self, user=user, role=TeamMembership.Roles.MEMBER)
        membership.save()

    def is_user_member(self, user):
        return user in self.members.all()


class TeamMembership(TimeStampedModel, models.Model):
    """
    The through model representing the relationship between User and Team. Stores role information: whether the user is an admin of the team or a regular member.
    """
    class Roles(models.IntegerChoices):
        MEMBER = 1, 'Member'
        ADMIN = 2, 'Administrator'

    role = models.IntegerField(choices=Roles.choices, default=Roles.MEMBER)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_memberships')

    class Meta:
        unique_together = ('user', 'team',)

    def __str__(self):
        return f'<Team Membership: {self.user}, {self.team.slug}>'

    @property
    def role_name(self):
        return self.get_role_display()


class TeamInvitation(TimeStampedModel, models.Model):
    """
    Represents all invitations to a given team and handles sending the invite email.
    """
    class Status(models.IntegerChoices):
        PENDING = 1, 'Pending'
        ACCEPTED = 2, 'Accepted'
        DECLINED = 3, 'Declined'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.IntegerField(choices=Status.choices, default=Status.PENDING)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    invitee = models.ForeignKey(User, on_delete=models.CASCADE, default=None, null=True, blank=True, related_name='received_team_invites')
    invitee_email = models.EmailField()
    inviter = models.ForeignKey(User, on_delete=models.SET_NULL, default=None, null=True, blank=True, related_name='sent_team_invites')
    message_text = models.TextField()
    # TimeStampedModel implemented created and modified fields

    objects = TeamInvitationManager()

    @property
    def status_name(self):
        return self.get_status_display()

    def send_email(self):
        domain = get_current_site(request=None).domain
        mail.send_mail(
            subject='Team Invitation',
            message=self.message_text,
            from_email='noreply@bugtracking.io',
            recipient_list=[self.invitee_email]
        )


# PROJECT AND RELATED THROUGH MODELS

class Project(TitleSlugDescriptionModel, TimeStampedModel, models.Model):
    """
    The second level organizational unit for the app. A project (subsumed under a team) is a collection of members and tickets.
    An example of a project might be a website that a company is developing.
    """
    members = models.ManyToManyField(User, related_name='projects', through='ProjectMembership')
    team = models.ForeignKey(Team, related_name='projects', on_delete=models.CASCADE)
    subscribers = models.ManyToManyField(User, related_name='project_subscriptions', through='ProjectSubscription')
    is_archived = models.BooleanField(default=False)
    manager = models.ForeignKey(User, related_name='assigned_projects', on_delete=models.SET_NULL, null=True, blank=True)
    # the `TitleSlugDescriptionModel` implements title, slug, and description fields, with the slug based on the project's title
    # the `TimeStampedModel` implements created and modified fields

    objects = ProjectManager.from_queryset(ProjectQueryset)()

    def __str__(self):
        return f'<Title: {self.title}, Slug: {self.slug}>'

    def add_member(self, user):
        if user in self.members.all():
            return
        if user in self.team.members.all():
            membership = ProjectMembership.objects.create(project=self, user=user, role=ProjectMembership.Roles.DEVELOPER)
            membership.save()
        else:
            raise ValidationError(_('Cannot add user. User is not a member of this project\'s team.'))

    def make_manager(self, user):
        if user == self.manager:
            return
        if user in self.members.all():
            if self.manager:
                old_manager_membership = self.get_membership(self.manager)
                old_manager_membership.role = old_manager_membership.Roles.DEVELOPER
                old_manager_membership.save()
            new_manager_membership = self.get_membership(user)
            new_manager_membership.role = new_manager_membership.Roles.MANAGER
            new_manager_membership.save()
            self.manager = new_manager_membership.user
            self.save()
        else:
            raise ValidationError(_('Cannot make manager. User is not a member of this project.'))

    def get_membership(self, user):
        return ProjectMembership.objects.get(user=user, project=self)

    def can_user_view(self, user):
        return user in self.members.all() or user in self.team.get_admins()

    def can_user_edit(self, user):
        return user == self.manager or user in self.team.get_admins()

    def can_user_update_manager(self, user):
        return user in self.team.get_admins()

    def can_user_create_tickets(self, user):
        return user in self.members.all() or user in self.team.get_admins()


class ProjectMembership(TimeStampedModel, models.Model):
    """
    The through model representing the relationship between User and Project. Stores role information (manager or developer) and timestamp information (when the user joined the project, when user's role is changed.
    """
    class Roles(models.IntegerChoices):
        DEVELOPER = 1, 'Developer'
        MANAGER = 2, 'Manager'

    role = models.IntegerField(choices=Roles.choices, default=Roles.DEVELOPER)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='project_memberships')

    class Meta:
        unique_together = ('user', 'project',)

    def __str__(self):
        return f'<Project Membership: {self.user}, {self.project.slug}>'

    @property
    def role_name(self):
        return self.get_role_display()


class ProjectSubscription(TimeStampedModel, models.Model):
    """
    The through model representing the email subscription relationship between Projects and Users.
    Stores timestamp information and subscription preferences for the individual project object (not global project notification preferences).
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='subscriptions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='project_subscription_objects')

    class Meta:
        unique_together = ('user', 'project',)

    def __str__(self):
        return f'<ProjectSubscription: {self.user}, {self.project.slug}>'


# TICKET, COMMENT AND RELATED THROUGH MODELS

class Ticket(TitleSlugDescriptionModel, TimeStampedModel, models.Model):
    """
    The lowest organizational unit of the app. A ticket (subsumed under a project) represents an individual task related to that project.
    An example of a ticket might be a task (implementing an API endpoint on a website, for instance) or a bug report that has been submitted (a particular webpage doesn't load).
    """
    class Priorities(models.IntegerChoices):
        LOW = 1, 'Low'
        HIGH = 2, 'High'
        URGENT = 3, 'Urgent'

    priority = models.IntegerField(choices=Priorities.choices, default=Priorities.LOW)
    user = models.ForeignKey(User, related_name='submitted_tickets', on_delete=models.SET_NULL, null=True)
    project = models.ForeignKey(Project, related_name='tickets', on_delete=models.CASCADE)
    resolution = models.TextField(null=True, default=None, blank=True)
    developer = models.ForeignKey(User, related_name='assigned_tickets', on_delete=models.SET_NULL, null=True, blank=True)
    is_open = models.BooleanField(default=True)
    subscribers = models.ManyToManyField(User, related_name='ticket_subscriptions', through='TicketSubscription')
    # the `TitleSlugDescriptionModel` implements title, slug, and description fields, with the slug based on the ticket's title
    # the `TimeStampedModel` implements created and modified fields

    objects = TicketManager.from_queryset(TicketQueryset)()

    def __str__(self):
        return f'<Ticket: {self.title}, Slug: {self.slug}>'

    def can_user_view(self, user):
        return user in self.project.members.all() or user in self.project.team.get_admins() or user == self.user

    def can_user_edit(self, user):
        return user == self.developer or user == self.project.manager or user in self.project.team.get_admins() or user == self.user

    def can_user_change_developer(self, user):
        return user in self.project.team.get_admins() or user == self.project.manager

    def can_user_delete(self, user):
        return user in self.project.team.get_admins() or user == self.project.manager


class TicketSubscription(TimeStampedModel, models.Model):
    """
    The through model representing the email subscription relationship between Projects and Users.
    Stores timestamp information and subscription preferences for the individual ticket object (not global ticket notification preferences).
    """
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='subscriptions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ticket_subscription_objects')

    class Meta:
        unique_together = ('user', 'ticket',)

    def __str__(self):
        return f'<TicketSubscription: {self.user}, {self.ticket.slug}>'


class Comment(TimeStampedModel, models.Model):
    """
    A comment which can be posted to an individual ticket.
    """
    user = models.ForeignKey(User, related_name='comments', on_delete=models.SET_NULL, null=True)
    text = models.TextField()
    ticket = models.ForeignKey(Ticket, related_name='comments', on_delete=models.CASCADE)
    # the `TimeStampedModel` implements created and modified fields

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f'<Comment on {self.ticket.slug} by {self.user}>'
