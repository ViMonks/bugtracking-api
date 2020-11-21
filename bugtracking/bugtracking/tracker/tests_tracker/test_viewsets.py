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
            #"title": "new updated title",
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
        old_title = self.team.title
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_login(self.admin)
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_200_OK
        self.team.refresh_from_db()
        # only description should have updated
        assert self.team.title == old_title
        assert self.team.description == self.put_data['description']
        assert not self.team.title == "new updated title"
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
        assert not self.team.title == "new updated title"

    def test_put_nonmember(self):
        """Cannot put."""
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_login(self.nonmember)
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        self.team.refresh_from_db()
        # nothing should have updated
        assert not self.team.description == self.put_data['description']
        assert not self.team.title == "new updated title"

    def test_patch_admin(self):
        """Can patch."""
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_login(self.admin)
        response = self.client.patch(url, {'description': 'patch desc'})
        assert response.status_code == status.HTTP_200_OK
        self.team.refresh_from_db()
        # only description should have updated
        assert self.team.description == 'patch desc'
        assert not self.team.title == "new updated title"
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
        assert not self.team.title == "new updated title"

    def test_patch_nonmember(self):
        """Cannot patch."""
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_login(self.nonmember)
        response = self.client.patch(url, {'description': 'patch desc'})
        assert response.status_code == status.HTTP_404_NOT_FOUND
        self.team.refresh_from_db()
        # nothing should have updated
        assert not self.team.description == 'patch desc'
        assert not self.team.title == "new updated title"

    def test_delete(self):
        """Teams cannot be deleted."""
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_login(self.admin)
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Team.objects.all().count() == 1


# Project ViewSet
class TestProjectViewSet(APITestCase):
    def setUp(self) -> None:
        base = fac()
        self.admin = base['admin']
        self.manager = base['manager']
        self.member = base['member']
        self.nonmember = base['nonmember']
        self.team = base['team']
        self.project = base['project']
        self.team_member = user(username='team_member')
        self.team.add_member(self.team_member)
        self.post_data = {'title': 'new project', 'description': 'description'}
        self.put_data = {
            "title": "Updated Title",
            "slug": "new-project",
            "is_archived": "true",
            "description": "Updated description",
            "created": "2020-11-20T15:50:50.730158-05:00",
            "modified": "2020-11-20T16:23:02.069394-05:00",
        }

    def test_list_admin(self):
        """Can view."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        self.client.force_login(self.admin)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]['title'] == self.project.title
        assert len(response.data) == 1

    def test_list_manager(self):
        """Can view."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        self.client.force_login(self.manager)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]['title'] == self.project.title
        assert len(response.data) == 1

    def test_list_member(self):
        """Can view."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        self.client.force_login(self.member)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]['title'] == self.project.title
        assert len(response.data) == 1

    def test_list_team_member(self):
        """Can view list, but project is not on it."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        self.client.force_login(self.team_member)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0

    def test_list_nonmember(self):
        """Cannot view."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        self.client.force_login(self.nonmember)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_anon(self):
        """Cannot view."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_admin(self):
        """Can view."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.admin)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == self.project.title

    def test_retrieve_manager(self):
        """Can view."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.manager)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == self.project.title

    def test_retrieve_member(self):
        """Can view."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.member)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == self.project.title

    def test_retrieve_team_member(self):
        """Cannot view."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.team_member)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_nonmember(self):
        """Cannot view."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.nonmember)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_anon(self):
        """Cannot view."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.nonmember)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_post_admin(self):
        """Can create."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        self.client.force_login(self.admin)
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Project.objects.all().count() == 2
        new_project = Project.objects.get(slug='new-project')
        assert new_project.team == self.team

    def test_post_manager(self):
        """Cannot create."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        self.client.force_login(self.manager)
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Project.objects.all().count() == 1

    def test_post_member(self):
        """Cannot create."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        self.client.force_login(self.member)
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Project.objects.all().count() == 1

    def test_post_team_member(self):
        """Cannot create."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        self.client.force_login(self.team_member)
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Project.objects.all().count() == 1

    def test_post_nonmember(self):
        """Cannot create."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        self.client.force_login(self.nonmember)
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Project.objects.all().count() == 1

    def test_post_anon(self):
        """Cannot create."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Project.objects.all().count() == 1

    def test_put_admin(self):
        """Can put."""
        assert self.project.is_archived == False
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.admin)
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_200_OK
        self.project.refresh_from_db()
        assert self.project.title == 'Updated Title'
        assert self.project.description == 'Updated description'
        assert self.project.is_archived == True

    def test_put_manager(self):
        """Can put."""
        assert self.project.is_archived == False
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.manager)
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_200_OK
        self.project.refresh_from_db()
        assert self.project.title == 'Updated Title'
        assert self.project.description == 'Updated description'
        assert self.project.is_archived == True

    def test_put_member(self):
        """Cannot put."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.member)
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Project.objects.all().count() == 1
        self.project.refresh_from_db()
        assert not self.project.title == self.put_data['title']
        assert not self.project.description == self.put_data['description']

    def test_put_team_member(self):
        """Cannot put."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.team_member)
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Project.objects.all().count() == 1
        self.project.refresh_from_db()
        assert not self.project.title == self.put_data['title']
        assert not self.project.description == self.put_data['description']

    def test_put_nonmember(self):
        """Cannot put."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.nonmember)
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Project.objects.all().count() == 1
        self.project.refresh_from_db()
        assert not self.project.title == self.put_data['title']
        assert not self.project.description == self.put_data['description']

    def test_put_anon(self):
        """Cannot put."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Project.objects.all().count() == 1
        self.project.refresh_from_db()
        assert not self.project.title == self.put_data['title']
        assert not self.project.description == self.put_data['description']

    def test_patch_admin(self):
        """Can patch."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.admin)
        response = self.client.patch(url, {'title': 'patch title', 'description': 'patch desc'})
        assert response.status_code == status.HTTP_200_OK
        self.project.refresh_from_db()
        assert self.project.title == 'patch title'
        assert self.project.description == 'patch desc'

    def test_patch_manager(self):
        """Can patch."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.manager)
        response = self.client.patch(url, {'title': 'patch title', 'description': 'patch desc'})
        assert response.status_code == status.HTTP_200_OK
        self.project.refresh_from_db()
        assert self.project.title == 'patch title'
        assert self.project.description == 'patch desc'

    def test_patch_member(self):
        """Cannot patch."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.member)
        response = self.client.patch(url, {'title': 'patch title', 'description': 'patch desc'})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.project.refresh_from_db()
        assert not self.project.title == 'patch title'
        assert not self.project.description == 'patch desc'

    def test_patch_team_member(self):
        """Cannot patch."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.team_member)
        response = self.client.patch(url, {'title': 'patch title', 'description': 'patch desc'})
        assert response.status_code == status.HTTP_404_NOT_FOUND
        self.project.refresh_from_db()
        assert not self.project.title == 'patch title'
        assert not self.project.description == 'patch desc'

    def test_patch_nonmember(self):
        """Cannot patch."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.nonmember)
        response = self.client.patch(url, {'title': 'patch title', 'description': 'patch desc'})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.project.refresh_from_db()
        assert not self.project.title == 'patch title'
        assert not self.project.description == 'patch desc'

    def test_admin_delete(self):
        """Can delete."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.admin)
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Project.objects.all().count() == 0

    def test_manager_delete(self):
        """Can delete."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.manager)
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Project.objects.all().count() == 0

    def test_member_delete(self):
        """Cannot delete."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.member)
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Project.objects.all().count() == 1

    def test_team_member_delete(self):
        """Cannot delete."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.team_member)
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Project.objects.all().count() == 1

    def test_nonmember_delete(self):
        """Cannot delete."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.nonmember)
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Project.objects.all().count() == 1

    def test_patching_new_manager_as_admin(self):
        """Can change manager. Only team admins can."""
        assert self.project.manager == self.manager
        old_manager_membership = ProjectMembership.objects.get(user=self.manager, project=self.project)
        assert old_manager_membership.role == ProjectMembership.Roles.MANAGER
        new_manager_membership = ProjectMembership.objects.get(user=self.member, project=self.project)
        assert new_manager_membership.role == ProjectMembership.Roles.DEVELOPER
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.admin)
        response = self.client.patch(url, {"manager": "member"})
        assert response.status_code == status.HTTP_200_OK
        self.project.refresh_from_db()
        assert self.project.manager == self.member
        old_manager_membership.refresh_from_db()
        assert old_manager_membership.role == ProjectMembership.Roles.DEVELOPER
        new_manager_membership.refresh_from_db()
        assert new_manager_membership.role == ProjectMembership.Roles.MANAGER

    def test_putting_new_manager_as_admin(self):
        """Can change manager. Only team admins can."""
        assert self.project.manager == self.manager
        old_manager_membership = ProjectMembership.objects.get(user=self.manager, project=self.project)
        assert old_manager_membership.role == ProjectMembership.Roles.MANAGER
        new_manager_membership = ProjectMembership.objects.get(user=self.member, project=self.project)
        assert new_manager_membership.role == ProjectMembership.Roles.DEVELOPER
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.admin)
        self.put_data['manager'] = "member"
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_200_OK
        self.project.refresh_from_db()
        assert self.project.manager == self.member
        old_manager_membership.refresh_from_db()
        assert old_manager_membership.role == ProjectMembership.Roles.DEVELOPER
        new_manager_membership.refresh_from_db()
        assert new_manager_membership.role == ProjectMembership.Roles.MANAGER

    def test_patching_new_manager_as_manager(self):
        """Cannot change manager. Only team admins can"""
        assert self.project.manager == self.manager
        old_manager_membership = ProjectMembership.objects.get(user=self.manager, project=self.project)
        assert old_manager_membership.role == ProjectMembership.Roles.MANAGER
        new_manager_membership = ProjectMembership.objects.get(user=self.member, project=self.project)
        assert new_manager_membership.role == ProjectMembership.Roles.DEVELOPER
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.manager)
        self.put_data['manager'] = "member"
        response = self.client.patch(url, {"manager": "member"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'Only a team admin' in response.data['errors']
        self.project.refresh_from_db()
        assert self.project.manager == self.manager
        old_manager_membership.refresh_from_db()
        assert old_manager_membership.role == ProjectMembership.Roles.MANAGER
        new_manager_membership.refresh_from_db()
        assert new_manager_membership.role == ProjectMembership.Roles.DEVELOPER

    def test_putting_new_manager_as_manager(self):
        """Cannot change manager. Only team admins can"""
        assert self.project.manager == self.manager
        old_manager_membership = ProjectMembership.objects.get(user=self.manager, project=self.project)
        assert old_manager_membership.role == ProjectMembership.Roles.MANAGER
        new_manager_membership = ProjectMembership.objects.get(user=self.member, project=self.project)
        assert new_manager_membership.role == ProjectMembership.Roles.DEVELOPER
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_login(self.manager)
        self.put_data['manager'] = "member"
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'Only a team admin' in response.data['errors']
        self.project.refresh_from_db()
        assert self.project.manager == self.manager
        old_manager_membership.refresh_from_db()
        assert old_manager_membership.role == ProjectMembership.Roles.MANAGER
        new_manager_membership.refresh_from_db()
        assert new_manager_membership.role == ProjectMembership.Roles.DEVELOPER
