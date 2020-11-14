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


# TODO: I think my old method of returning team owners and such returns all members who are MEMBERS of the team in question and OWNERS of ANY team; need to make sure new method doesn't do that

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


class TestProject(TestCase):
    def setUp(self) -> None:
        base = fac()
        self.admin = base['admin']
        self.manager = base['manager']
        self.member = base['member']
        self.nonmember = base['nonmember']
        self.team = base['team']
        self.project = base['project']

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
