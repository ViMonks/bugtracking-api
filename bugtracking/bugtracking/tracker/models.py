# stdlib imports

# core django imports
from django.db import models
from django.conf import settings

# third party imports
from django_extensions.db.models import TitleSlugDescriptionModel, TimeStampedModel
from django_extensions.db.fields import CreationDateTimeField

# my internal imports


User = settings.AUTH_USER_MODEL

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

    def __str__(self):
        return f'<Title: {self.title}, Slug: {self.slug}>'

    def can_be_viewed_by_user(self, user):
        return user in self.members

    def get_admins(self):
        return self.members.filter(team_memberships__role=2, team_memberships__team=self)

    def make_admin(self, user):
        membership = self.memberships.get(user=user)
        membership.role = 2
        membership.save()


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


# TODO: implement a TeamInvitation model to handle team invites


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
    # the `TitleSlugDescriptionModel` implements title, slug, and description fields, with the slug based on the project's title
    # the `TimeStampedModel` implements created and modified fields

    def __str__(self):
        return f'<Title: {self.title}, Slug: {self.slug}>'


class ProjectMembership(TimeStampedModel, models.Model):
    """
    The through model representing the relationship between User and Project. Stores role information (manager or developer) and timestamp information (when the user joined the project, when user's role is changed.
    """
    class Roles(models.IntegerChoices):
        DEVELOPER = 1, 'Developer'
        MANGER = 2, 'Manager'

    role = models.IntegerField(choices=Roles.choices, default=Roles.DEVELOPER)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='project_memberships')

    class Meta:
        unique_together = ('user', 'project',)

    def __str__(self):
        return f'<Project Membership: {self.user}, {self.project.slug}>'


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

    def __str__(self):
        return f'<Ticket: {self.title}, Slug: {self.slug}>'


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
