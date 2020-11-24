# stdlib imports

# django core imports
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, ObjectDoesNotExist, PermissionDenied
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

    def test_title_cannot_be_updated(self):
        assert self.team.title == 'team_title'
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_login(self.admin)
        response = self.client.patch(url, {'title': 'updated title'})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.team.refresh_from_db()
        assert self.team.title == 'team_title'


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

    def test_post_new_with_manager_assigned(self):
        """Can create."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        self.client.force_login(self.admin)
        self.post_data['manager'] = 'manager'
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_201_CREATED
        new_project = Project.objects.get(slug='new-project')
        assert new_project.manager == self.manager
        membership_object = ProjectMembership.objects.get(user=self.manager, project=new_project)
        assert membership_object.role == ProjectMembership.Roles.MANAGER

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

    def test_list_view_returns_only_team_projects(self):
        new_project = baker.make(Project, team=self.team)
        other_team_project = baker.make(Project)
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        self.client.force_login(self.admin)
        response = self.client.get(url)
        assert len(response.data) ==  2
        assert response.data[0]['title'] == 'project_title'
        assert response.data[1]['title'] == new_project.title


# Ticket ViewSet
class TestTicketViewSet(APITestCase):
    def setUp(self) -> None:
        base = fac()
        self.admin = base['admin']
        self.manager = base['manager']
        self.developer = base['developer']
        self.member = base['member']
        self.team_member = user('team_member')
        self.nonmember = base['nonmember']
        self.team = base['team']
        self.team.add_member(self.team_member)
        self.project = base['project']
        self.ticket = base['ticket']
        self.post_data = {
            'title': 'new ticket',
            'description': 'description',
            'project': self.project.slug,
        }
        self.put_data = {
            'title': 'updated title',
            'description': 'updated description',
            'priority': 3,
            'resolution': 'updated resolution',
        }
        self.patch_data = {
            'priority': 3
        }

    def test_list_admin(self):
        """Can view."""
        url = reverse('api:tickets-list', kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug})
        self.client.force_login(self.admin)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]['title'] == self.ticket.title
        assert len(response.data) == 1

    def test_list_manager(self):
        """Can view."""
        url = reverse('api:tickets-list', kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug})
        self.client.force_login(self.manager)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]['title'] == self.ticket.title
        assert len(response.data) == 1

    def test_list_team_member(self):
        """Cannot view."""
        url = reverse('api:tickets-list', kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug})
        self.client.force_login(self.team_member)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert len(response.data) == 1

    def test_list_nonmember(self):
        """Cannot view."""
        url = reverse('api:tickets-list', kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug})
        self.client.force_login(self.nonmember)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert len(response.data) == 1

    def test_retrieve_admin(self):
        """Can view."""
        url = reverse('api:tickets-detail',
                      kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug, 'slug': self.ticket.slug})
        self.client.force_login(self.admin)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == self.ticket.title

    def test_retrieve_manager(self):
        """Can view."""
        url = reverse('api:tickets-detail',
                      kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug, 'slug': self.ticket.slug})
        self.client.force_login(self.manager)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == self.ticket.title

    def test_retrieve_team_member(self):
        """Cannot view."""
        url = reverse('api:tickets-detail',
                      kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug, 'slug': self.ticket.slug})
        self.client.force_login(self.team_member)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_nonmember(self):
        """Cannot view."""
        url = reverse('api:tickets-detail',
                      kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug, 'slug': self.ticket.slug})
        self.client.force_login(self.nonmember)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_post_admin(self):
        """Can post."""
        url = reverse('api:tickets-list', kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug})
        user = self.admin
        self.client.force_login(user)
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Ticket.objects.all().count() == 2
        ticket = Ticket.objects.last()
        assert ticket.user == user
        assert ticket.project == self.project

    def test_post_manager(self):
        """Can post."""
        url = reverse('api:tickets-list',
                      kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug})
        user = self.manager
        self.client.force_login(user)
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Ticket.objects.all().count() == 2
        ticket = Ticket.objects.last()
        assert ticket.user == user
        assert ticket.project == self.project

    def test_post_member(self):
        """Can post."""
        url = reverse('api:tickets-list',
                      kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug})
        user = self.member
        self.client.force_login(user)
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Ticket.objects.all().count() == 2
        ticket = Ticket.objects.last()
        assert ticket.user == user
        assert ticket.project == self.project

    def test_post_team_member(self):
        """Cannot post."""
        url = reverse('api:tickets-list',
                      kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug})
        user = self.team_member
        self.client.force_login(user)
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Ticket.objects.all().count() == 1

    def test_post_nonmember(self):
        """Cannot post."""
        url = reverse('api:tickets-list',
                      kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug})
        user = self.nonmember
        self.client.force_login(user)
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Ticket.objects.all().count() == 1

    def test_post_new_with_developer_assigned(self):
        url = reverse('api:tickets-list',
                      kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug})
        user = self.admin
        self.client.force_login(user)
        self.post_data['developer'] = 'developer'
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_201_CREATED
        ticket = Ticket.objects.last()
        assert ticket.developer == self.developer

    def test_put_admin(self):
        "Can put."
        url = reverse('api:tickets-detail', kwargs={
            'team_slug': self.project.team.slug,
            'project_slug': self.project.slug,
            'slug': self.ticket.slug
        })
        user = self.admin
        self.client.force_login(user)
        assert self.ticket.title == 'ticket_title'
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_200_OK
        self.ticket.refresh_from_db()
        assert self.ticket.title == 'updated title'

    def test_put_manager(self):
        "Can put."
        url = reverse('api:tickets-detail', kwargs={
            'team_slug': self.project.team.slug,
            'project_slug': self.project.slug,
            'slug': self.ticket.slug
        })
        user = self.manager
        self.client.force_login(user)
        assert self.ticket.title == 'ticket_title'
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_200_OK
        self.ticket.refresh_from_db()
        assert self.ticket.title == 'updated title'

    def test_put_developer(self):
        "Can put."
        url = reverse('api:tickets-detail', kwargs={
            'team_slug': self.project.team.slug,
            'project_slug': self.project.slug,
            'slug': self.ticket.slug
        })
        user = self.developer
        self.client.force_login(user)
        assert self.ticket.title == 'ticket_title'
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_200_OK
        self.ticket.refresh_from_db()
        assert self.ticket.title == 'updated title'

    def test_put_member(self):
        "Cannot put."
        url = reverse('api:tickets-detail', kwargs={
            'team_slug': self.project.team.slug,
            'project_slug': self.project.slug,
            'slug': self.ticket.slug
        })
        user = self.member
        self.client.force_login(user)
        assert self.ticket.title == 'ticket_title'
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.ticket.refresh_from_db()
        assert self.ticket.title == 'ticket_title'

    def test_put_team_member(self):
        "Cannot put."
        url = reverse('api:tickets-detail', kwargs={
            'team_slug': self.project.team.slug,
            'project_slug': self.project.slug,
            'slug': self.ticket.slug
        })
        user = self.team_member
        self.client.force_login(user)
        assert self.ticket.title == 'ticket_title'
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.ticket.refresh_from_db()
        assert self.ticket.title == 'ticket_title'

    def test_put_nonmember(self):
        "Cannot put."
        url = reverse('api:tickets-detail', kwargs={
            'team_slug': self.project.team.slug,
            'project_slug': self.project.slug,
            'slug': self.ticket.slug
        })
        user = self.nonmember
        self.client.force_login(user)
        assert self.ticket.title == 'ticket_title'
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.ticket.refresh_from_db()
        assert self.ticket.title == 'ticket_title'

    def test_patch_admin(self):
        "Can patch."
        url = reverse('api:tickets-detail', kwargs={
            'team_slug': self.project.team.slug,
            'project_slug': self.project.slug,
            'slug': self.ticket.slug
        })
        user = self.admin
        self.client.force_login(user)
        assert self.ticket.priority == 1
        response = self.client.patch(url, self.patch_data)
        assert response.status_code == status.HTTP_200_OK
        self.ticket.refresh_from_db()
        assert self.ticket.priority == 3

    def test_patch_manager(self):
        "Can patch."
        url = reverse('api:tickets-detail', kwargs={
            'team_slug': self.project.team.slug,
            'project_slug': self.project.slug,
            'slug': self.ticket.slug
        })
        user = self.manager
        self.client.force_login(user)
        assert self.ticket.priority == 1
        response = self.client.patch(url, self.patch_data)
        assert response.status_code == status.HTTP_200_OK
        self.ticket.refresh_from_db()
        assert self.ticket.priority == 3

    def test_patch_developer(self):
        "Can patch."
        url = reverse('api:tickets-detail', kwargs={
            'team_slug': self.project.team.slug,
            'project_slug': self.project.slug,
            'slug': self.ticket.slug
        })
        user = self.developer
        self.client.force_login(user)
        assert self.ticket.priority == 1
        response = self.client.patch(url, self.patch_data)
        assert response.status_code == status.HTTP_200_OK
        self.ticket.refresh_from_db()
        assert self.ticket.priority == 3

    def test_patch_member(self):
        "Cannot patch."
        url = reverse('api:tickets-detail', kwargs={
            'team_slug': self.project.team.slug,
            'project_slug': self.project.slug,
            'slug': self.ticket.slug
        })
        user = self.member
        self.client.force_login(user)
        assert self.ticket.priority == 1
        response = self.client.patch(url, self.patch_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.ticket.refresh_from_db()
        assert self.ticket.priority == 1

    def test_patch_team_member(self):
        "Cannot patch."
        url = reverse('api:tickets-detail', kwargs={
            'team_slug': self.project.team.slug,
            'project_slug': self.project.slug,
            'slug': self.ticket.slug
        })
        user = self.team_member
        self.client.force_login(user)
        assert self.ticket.priority == 1
        response = self.client.patch(url, self.patch_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.ticket.refresh_from_db()
        assert self.ticket.priority == 1

    def test_patch_nonmember(self):
        "Cannot patch."
        url = reverse('api:tickets-detail', kwargs={
            'team_slug': self.project.team.slug,
            'project_slug': self.project.slug,
            'slug': self.ticket.slug
        })
        user = self.nonmember
        self.client.force_login(user)
        assert self.ticket.priority == 1
        response = self.client.patch(url, self.patch_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.ticket.refresh_from_db()
        assert self.ticket.priority == 1

    def test_delete_admin(self):
        "Can delete."
        url = reverse('api:tickets-detail', kwargs={
            'team_slug': self.project.team.slug,
            'project_slug': self.project.slug,
            'slug': self.ticket.slug
        })
        user = self.admin
        self.client.force_login(user)
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Ticket.objects.count() == 0

    def test_delete_manager(self):
        "Can delete."
        url = reverse('api:tickets-detail', kwargs={
            'team_slug': self.project.team.slug,
            'project_slug': self.project.slug,
            'slug': self.ticket.slug
        })
        user = self.manager
        self.client.force_login(user)
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Ticket.objects.count() == 0

    def test_delete_developer(self):
        "Cannot delete."
        url = reverse('api:tickets-detail', kwargs={
            'team_slug': self.project.team.slug,
            'project_slug': self.project.slug,
            'slug': self.ticket.slug
        })
        user = self.developer
        self.client.force_login(user)
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Ticket.objects.count() == 1

    def test_updating_developer_admin(self):
        """Can update developer."""
        url = reverse('api:tickets-detail', kwargs={
            'team_slug': self.project.team.slug,
            'project_slug': self.project.slug,
            'slug': self.ticket.slug
        })
        user = self.admin
        self.client.force_login(user)
        assert self.ticket.developer == self.developer
        response = self.client.patch(url, {'developer': user.username})
        assert response.status_code == status.HTTP_200_OK
        self.ticket.refresh_from_db()
        assert self.ticket.developer == user

    def test_updating_developer_manager(self):
        """Can update developer."""
        url = reverse('api:tickets-detail', kwargs={
            'team_slug': self.project.team.slug,
            'project_slug': self.project.slug,
            'slug': self.ticket.slug
        })
        user = self.manager
        self.client.force_login(user)
        assert self.ticket.developer == self.developer
        response = self.client.patch(url, {'developer': user.username})
        assert response.status_code == status.HTTP_200_OK
        self.ticket.refresh_from_db()
        assert self.ticket.developer == user

    def test_updating_developer_developer(self):
        """Cannot update developer."""
        url = reverse('api:tickets-detail', kwargs={
            'team_slug': self.project.team.slug,
            'project_slug': self.project.slug,
            'slug': self.ticket.slug
        })
        user = self.developer
        self.client.force_login(user)
        assert self.ticket.developer == self.developer
        response = self.client.patch(url, {'developer': 'admin'})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.ticket.refresh_from_db()
        assert self.ticket.developer == self.developer

    def test_cannot_create_new_without_project(self):
        with pytest.raises(ValidationError) as error:
            Ticket.objects.create_new(title='title', description='description')
        assert "Project argument" in str(error.value)
        assert Ticket.objects.count() == 1

    def test_cannot_create_new_with_project_argument_as_wrong_type(self):
        with pytest.raises(ValidationError) as error:
            Ticket.objects.create_new(title='title', description='description', project='project')
        assert "Project argument" in str(error.value)
        assert Ticket.objects.count() == 1

    def test_cannot_create_new_without_user(self):
        with pytest.raises(ValidationError) as error:
            Ticket.objects.create_new(title='title', description='description', project=self.project)
        assert "User argument must be provided" in str(error.value)
        assert Ticket.objects.count() == 1

    def test_cannot_create_new_with_user_argument_wrong_type(self):
        with pytest.raises(ValidationError) as error:
            Ticket.objects.create_new(title='title', description='description', project=self.project, user='admin')
        assert "User argument must be a User object" in str(error.value)
        assert Ticket.objects.count() == 1

    def test_cannot_create_new_with_user_who_does_not_have_permission(self):
        with pytest.raises(PermissionDenied) as error:
            Ticket.objects.create_new(title='title', description='description', project=self.project, user=self.team_member)
        assert "Only project members" in str(error.value)
        assert Ticket.objects.count() == 1

    def test_ticket_list_only_includes_project_tickets(self):
        assert len(self.team.projects.all()) == 1
        other_project = baker.make(Project, team=self.team)
        other_project_ticket = baker.make(Ticket, project=other_project)
        other_team_ticket = baker.make(Ticket)
        self.team.refresh_from_db()
        assert len(self.team.projects.all()) == 2
        url = reverse('api:tickets-list', kwargs={'team_slug': self.team.slug, 'project_slug': self.project.slug})
        self.client.force_login(self.admin)
        response = self.client.get(url)
        assert len(response.data) == 1
        assert response.data[0]['title'] != other_team_ticket.title
        assert response.data[0]['title'] != other_project_ticket
