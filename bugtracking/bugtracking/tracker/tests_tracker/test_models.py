# stdlib imports

# django core imports
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, ObjectDoesNotExist

# third party imports
import pytest
from model_bakery import baker
from model_bakery.recipe import related

# my internal imports
from bugtracking.users.models import User
from bugtracking.tracker.models import (
    Team, TeamMembership, Project, ProjectMembership, Ticket, Comment
)
from .factories import model_setup as fac


# PYTEST FIXTURES
def user(username='admin'):
    return User.objects.create_user(username=username, password='password')

def create_team(user, title, description):
    return Team.objects.create(title=title, description=description, creator=user)

# TESTS

class FactoryTest(TestCase):
    """
    This tests the factory itself, as well as the following model methods:
    Team.make_admin()
    Team.add_member()
    Project.make_manager()
    Project.add_member()
    However, it only tests that the basic functionality of these methods work, i.e., members are added to the respective roles.
    It does not test any of the validation, e.g., that non-team-members can't be added as admin.
    """
    def setUp(self):
        base = fac()
        self.admin = base['admin']
        self.manager = base['manager']
        self.developer = base['developer']
        self.member = base['member']
        self.nonmember = base['nonmember']
        self.team = base['team']
        self.project = base['project']
        self.ticket = base['ticket']

    def test_four_membership_objects(self):
        assert TeamMembership.objects.all().count() == 4

    def test_team_created(self):
        assert isinstance(self.team, Team)

    def test_four_members(self):
        assert len(self.team.members.all()) == 4

    def test_admin_is_in_members(self):
        assert (self.admin in self.team.members.all())

    def test_admin_user_is_admin(self):
        assert (self.admin in self.team.get_admins())

    def test_five_users_total(self):
        assert User.objects.all().count() == 5

    def test_project_manager_assigned(self):
        assert ProjectMembership.objects.get(user=self.manager, project=self.project).role == ProjectMembership.Roles.MANGER
        assert self.manager == self.project.manager

    def test_project_has_four_members(self):
        assert self.project.members.all().count() == 4

    def test_developer_assigned_to_ticket(self):
        assert self.ticket.developer == self.developer

    def test_member_is_team_member(self):
        assert self.member in self.team.members.all()

    def test_nonmember_not_team_member(self):
        assert self.nonmember not in self.team.members.all()
        assert self.team.is_user_member(self.nonmember) == False




class TestTeam(TestCase):
    def setUp(self) -> None:
        base = fac()
        self.admin = base['admin']
        self.member = base['member']
        self.nonmember = base['nonmember']
        self.team = base['team']

    def test_get_admins(self):
        """Returns admins only."""
        assert self.team.get_admins().count() == 1
        assert self.team.get_admins()[0] == self.admin

    def test_make_admin_fails_on_nonmember(self):
        """Proper error is raised and admin is NOT added."""
        with pytest.raises(ValidationError) as error:
            self.team.make_admin(self.nonmember)
        assert "Cannot make user an admin." in str(error.value)
        assert self.team.get_admins().count() == 1

    def test_is_user_member(self):
        """Returns true for members, false for non-members."""
        assert self.team.is_user_member(self.member) == True
        assert self.team.is_user_member(self.nonmember) == False

    def test_get_admins_returns_only_this_teams_admins(self):
        other_team = Team.objects.create(title='other', description='desc')
        other_admin = User.objects.create_user(username='other', password='password')
        other_team.add_member(other_admin)
        other_team.make_admin(other_admin)
        assert other_admin in other_team.get_admins()
        assert self.admin not in other_team.get_admins()
        assert other_admin not in self.team.get_admins()

    def test_get_admins_returns_only_this_teams_admins_even_if_other_admins_are_members(self):
        other_team = Team.objects.create(title='other', description='desc')
        other_admin = User.objects.create_user(username='other', password='password')
        other_team.add_member(other_admin)
        other_team.make_admin(other_admin)
        self.team.add_member(other_admin)
        assert other_admin in other_team.get_admins()
        assert self.admin not in other_team.get_admins()
        assert other_admin not in self.team.get_admins()

    def test_get_non_admins(self):
        """Returns non-admins only."""
        assert self.team.get_non_admins().count() == 3
        assert self.admin not in self.team.get_non_admins()

    def test_users_admin_teams_queryset(self):
        other_team = Team.objects.create(title='other', description='desc')
        other_admin = User.objects.create_user(username='other', password='password')
        other_team.add_member(other_admin)
        other_team.make_admin(other_admin)
        assert self.team in Team.objects.users_admin_teams(self.admin)
        assert other_team not in Team.objects.users_admin_teams(self.admin)
        assert len(Team.objects.users_admin_teams(self.member)) == 0

    def test_users_member_teams_queryset(self):
        other_team = Team.objects.create(title='other', description='desc')
        other_admin = User.objects.create_user(username='other', password='password')
        other_team.add_member(other_admin)
        other_team.make_admin(other_admin)
        assert self.team in Team.objects.users_member_teams(self.member)
        assert other_team not in Team.objects.users_member_teams(self.admin)
        assert len(Team.objects.users_member_teams(self.member)) == 1
        assert len(Team.objects.users_member_teams(self.nonmember)) == 0

    def test_team_creation_with_string(self):
        new_team = Team.objects.create_new(title='New', description='desc', creator='admin')
        assert isinstance(new_team, Team)
        assert self.admin in new_team.get_admins()
        assert Team.objects.all().count() == 2

    def test_team_creation_with_user_object(self):
        new_team = Team.objects.create_new(title='New', description='desc', creator=self.admin)
        assert isinstance(new_team, Team)
        assert self.admin in new_team.get_admins()
        assert Team.objects.all().count() == 2

    def test_team_creation_with_invalid_username_raises_correct_error(self):
        assert Team.objects.all().count() == 1
        with pytest.raises(ObjectDoesNotExist) as error:
            new_team = Team.objects.create_new(title='New', description='desc', creator='does_not_exist')
        assert "does not exist" in str(error.value)
        assert Team.objects.all().count() == 1

    def test_team_creation_with_wrong_object_type_raises_correct_error(self):
        assert Team.objects.all().count() == 1
        with pytest.raises(ValidationError) as error:
            new_team = Team.objects.create_new(title='New', description='desc', creator=1)
        assert "<class 'int'>" in str(error.value)
        assert Team.objects.all().count() == 1

    def test_team_creation_with_no_creator_kwarg_raises_error(self):
        assert Team.objects.all().count() == 1
        with pytest.raises(ValidationError) as error:
            new_team = Team.objects.create_new(title='New', description='desc')
        assert "creator" in str(error.value)
        assert Team.objects.all().count() == 1

    def test_add_member_on_already_existing_member(self):
        assert self.team.members.all().count() == 4
        self.team.add_member(self.member)
        assert self.team.members.all().count() == 4


class TestProject(TestCase):
    def setUp(self) -> None:
        base = fac()
        self.admin = base['admin']
        self.manager = base['manager']
        self.member = base['member']
        self.nonmember = base['nonmember']
        self.team = base['team']
        self.project = base['project']

    def test_add_member_on_already_existing_member(self):
        assert self.project.members.all().count() == 4
        self.project.add_member(self.member)
        assert self.project.members.all().count() == 4

    def test_adding_manager_on_current_manager(self):
        assert self.project.manager == self.manager
        self.project.make_manager(self.manager)
        assert self.project.manager == self.manager

    def test_add_member_fails_on_non_team_member(self):
        with pytest.raises(ValidationError) as error:
            self.project.add_member(self.nonmember)
        assert "Cannot add" in str(error.value)
        assert self.nonmember not in self.project.members.all()

    def test_make_manager_fails_on_non_team_member(self):
        with pytest.raises(ValidationError) as error:
            self.project.make_manager(self.nonmember)
        assert "Cannot make manager" in str(error.value)
        assert self.nonmember != self.project.manager
        assert self.manager == self.project.manager

    def test_get_membership(self):
        assert isinstance(self.project.get_membership(self.member), ProjectMembership)

    def test_assigning_new_manager_changes_project_membership_roles(self):
        """
        Assigning a new manager should change the old manager's ProjectMembership.role back to developer
        and switch the new manager's role to manager.
        """
        assert self.project.get_membership(self.manager).role == ProjectMembership.Roles.MANGER
        self.project.make_manager(self.member)
        assert self.project.get_membership(self.manager).role == ProjectMembership.Roles.DEVELOPER
        assert self.project.get_membership(self.member).role == ProjectMembership.Roles.MANGER

    def test_can_user_view_method(self):
        assert self.project.can_user_view(self.member)
        assert not self.project.can_user_view(self.nonmember)

    def test_can_user_edit_method(self):
        assert self.project.can_user_edit(self.manager)
        assert self.project.can_user_edit(self.admin)
        assert not self.project.can_user_edit(self.nonmember)
        assert not self.project.can_user_edit(self.member)

    def test_filter_for_team_and_user_queryset(self):
        other_project = Project.objects.create(title='title', description='desc', team=self.team)
        other_team = Team.objects.create(title='other', description='desc')
        other_team_project = Project.objects.create(title='title', description='desc', team=other_team)
        # member sees the one project he is a member on
        assert len(Project.objects.filter_for_team_and_user(user=self.member, team_slug=self.team.slug)) == 1
        assert self.project in Project.objects.filter_for_team_and_user(user=self.member, team_slug=self.team.slug)
        # admin sees all projects on his team but not the other_team_project
        assert len(Project.objects.filter_for_team_and_user(user=self.admin, team_slug=self.team.slug)) == 2
        assert self.project in Project.objects.filter_for_team_and_user(user=self.admin, team_slug=self.team.slug)
        assert other_project in Project.objects.filter_for_team_and_user(user=self.admin, team_slug=self.team.slug)
        # nonmember sees no projects
        assert len(Project.objects.filter_for_team_and_user(user=self.nonmember, team_slug=self.team.slug)) == 0


class TestTicket(TestCase):
    def setUp(self):
        base = fac()
        self.member = base['member']
        self.nonmember = base['nonmember']
        self.ticket = base['ticket']
        self.team = base['team']
        self.developer = base['developer']
        self.admin = base['admin']
        self.manager = base['manager']

    def test_user_can_view_method(self):
        assert self.ticket.can_user_view(self.member)
        assert not self.ticket.can_user_view(self.nonmember)

    def test_user_can_edit_method(self):
        assert self.ticket.can_user_edit(self.developer)
        assert self.ticket.can_user_edit(self.manager)
        assert self.ticket.can_user_edit(self.admin)
        assert not self.ticket.can_user_edit(self.member)

    def test_filter_for_team_and_user_queryset(self):
        other_project = Project.objects.create(title='title', description='desc', team=self.team)
        # other_team = Team.objects.create(title='other', description='desc')
        other_ticket = Ticket.objects.create(title='title', description='desc', project=other_project)
        other_team_ticket = baker.make(Ticket)
        # other_team_project = Project.objects.create(title='title', description='desc', team=other_team)
        # member sees the one ticket on the project where he is a member
        assert len(Ticket.objects.filter_for_team_and_user(user=self.member, team_slug=self.team.slug)) == 1
        assert self.ticket in Ticket.objects.filter_for_team_and_user(user=self.member, team_slug=self.team.slug)
        # admin sees all tickets on his team but not the other_team_ticket
        assert len(Ticket.objects.filter_for_team_and_user(user=self.admin, team_slug=self.team.slug)) == 2
        assert self.ticket in Ticket.objects.filter_for_team_and_user(user=self.admin, team_slug=self.team.slug)
        assert other_ticket in Ticket.objects.filter_for_team_and_user(user=self.admin, team_slug=self.team.slug)
        assert other_team_ticket not in Ticket.objects.filter_for_team_and_user(user=self.admin, team_slug=self.team.slug)
        assert isinstance(other_team_ticket, Ticket) # just making sure model_bakery worked
        # nonmember sees no tickets
        assert len(Ticket.objects.filter_for_team_and_user(user=self.nonmember, team_slug=self.team.slug)) == 0
