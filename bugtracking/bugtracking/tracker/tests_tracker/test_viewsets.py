# stdlib imports

# django core imports
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.shortcuts import reverse

# third party imports
import pytest
from model_bakery import baker
from model_bakery.recipe import related
from rest_framework import status
from rest_framework.test import APITestCase

# my internal imports
from bugtracking.users.models import User
from bugtracking.tracker.models import (
    Team, TeamMembership, Project, ProjectMembership, Ticket, Comment
)
from .factories import model_setup as fac


# PYTEST FIXTURES
def user(username='admin'):
    return User.objects.create_user(username=username, password='password')

# Team ViewSet
class TestTeamViewSet(APITestCase):
    def setUp(self) -> None:
        base = fac()
        self.admin = base['admin']
        self.member = base['member']
        self.nonmember = base['nonmember']
        self.team = base['team']
        self.post_data = {'title': 'new team', 'description': 'description'}
        # put_data includes all fields, but only description should be editable
        self.put_data = {
            "title": "new updated title",
            "slug": "new-updated-title",
            "description": "updated desc",
            "memberships": [
                {
                    "user": "monks",
                    "role": 2,
                    "role_name": "Administrator"
                }
            ],
            "created": "2020-11-17T15:16:20.403738-05:00",
            "url": "http://localhost:8000/api/teams/new-updated-title/"
        }

    def test_list_admin(self):
        """Can view."""
        url = reverse('api:teams-list')
        self.client.force_login(self.admin)
        response = self.client.get(url)
        assert response.data[0]['title'] == 'team_title'
        assert len(response.data) == 1
        assert response.status_code == status.HTTP_200_OK

    def test_list_member(self):
        """Can view."""
        url = reverse('api:teams-list')
        self.client.force_login(self.member)
        response = self.client.get(url)
        assert response.data[0]['title'] == 'team_title'
        assert len(response.data) == 1
        assert response.status_code == status.HTTP_200_OK

    def test_list_nonmember(self):
        """Cannot view."""
        url = reverse('api:teams-list')
        self.client.force_login(self.nonmember)
        response = self.client.get(url)
        assert len(response.data) == 0
        assert response.status_code == status.HTTP_200_OK

    def test_list_anon(self):
        """Cannot view."""
        url = reverse('api:teams-list')
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_admin(self):
        """Can view."""
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_login(self.admin)
        response = self.client.get(url)
        assert response.data['title'] == 'team_title'
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_member(self):
        """Can view."""
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_login(self.member)
        response = self.client.get(url)
        assert response.data['title'] == 'team_title'
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_nonmember(self):
        """Cannot view."""
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_login(self.nonmember)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_anon(self):
        """Cannot view."""
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_post_admin(self):
        """Can create."""
        url = reverse('api:teams-list')
        self.client.force_login(self.admin)
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Team.objects.all().count() == 2
        new_team = Team.objects.get(slug='new-team')
        assert self.admin in new_team.get_admins()

    def test_post_nonmember(self):
        """Can create."""
        url = reverse('api:teams-list')
        self.client.force_login(self.nonmember)
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Team.objects.all().count() == 2
        new_team = Team.objects.get(slug='new-team')
        assert self.nonmember in new_team.get_admins()

    def test_post_anon(self):
        """Cannot create."""
        url = reverse('api:teams-list')
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Team.objects.all().count() == 1

    def test_put_admin(self):
        """Can put."""
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_login(self.admin)
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_200_OK
        self.team.refresh_from_db()
        # only description should have updated
        assert self.team.description == self.put_data['description']
        assert not self.team.title == self.put_data['title']
        assert Team.objects.all().count() == 1

    def test_put_member(self):
        """Cannot put."""
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_login(self.member)
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.team.refresh_from_db()
        # nothing should have updated
        assert not self.team.description == self.put_data['description']
        assert not self.team.title == self.put_data['title']

    def test_put_nonmember(self):
        """Cannot put."""
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_login(self.nonmember)
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        self.team.refresh_from_db()
        # nothing should have updated
        assert not self.team.description == self.put_data['description']
        assert not self.team.title == self.put_data['title']

    def test_patch_admin(self):
        """Can patch."""
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_login(self.admin)
        response = self.client.patch(url, {'description': 'patch desc'})
        assert response.status_code == status.HTTP_200_OK
        self.team.refresh_from_db()
        # only description should have updated
        assert self.team.description == 'patch desc'
        assert not self.team.title == self.put_data['title']
        assert Team.objects.all().count() == 1

    def test_patch_member(self):
        """Cannot patch."""
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_login(self.member)
        response = self.client.patch(url, {'description': 'patch desc'})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.team.refresh_from_db()
        # nothing should have updated
        assert not self.team.description == 'patch desc'
        assert not self.team.title == self.put_data['title']

    def test_patch_nonmember(self):
        """Cannot patch."""
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_login(self.nonmember)
        response = self.client.patch(url, {'description': 'patch desc'})
        assert response.status_code == status.HTTP_404_NOT_FOUND
        self.team.refresh_from_db()
        # nothing should have updated
        assert not self.team.description == 'patch desc'
        assert not self.team.title == self.put_data['title']

    def test_delete(self):
        """Teams cannot be deleted."""
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_login(self.admin)
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Team.objects.all().count() == 1
