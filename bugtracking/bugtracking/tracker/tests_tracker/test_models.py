# stdlib imports

# django core imports
from django.test import TestCase
from django.contrib.auth import get_user_model

# third party imports
import pytest
from model_bakery import baker
from model_bakery.recipe import related

# my internal imports
from bugtracking.users.models import User
from bugtracking.tracker.models import Team, TeamMembership


# PYTEST FIXTURES
def user(username='admin'):
    return User.objects.create_user(username=username, password='password')

# TESTS

class BakeryTest(TestCase):
    def setUp(self):
        self.admin = user()
        self.team = baker.make(Team, members=[self.admin])
        self.team.make_admin(self.admin)

    def test_membership_object_exists(self):
        assert TeamMembership.objects.all().count() == 1

    def test_team_created(self):
        assert isinstance(self.team, Team)

    def test_member_exists(self):
        assert len(self.team.members.all()) == 1

    def test_admin_is_in_members(self):
        assert (self.admin in self.team.members.all())

    def test_admin_user_is_admin(self):
        assert (self.admin in self.team.get_admins())


# TODO: I think my old method of returning team owners and such returns all members who are MEMBERS of the team in question and OWNERS of ANY team; need to make sure new method doesn't do that

