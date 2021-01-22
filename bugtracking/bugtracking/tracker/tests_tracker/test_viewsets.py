# stdlib imports
import datetime as dt

# django core imports
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, ObjectDoesNotExist, PermissionDenied
from django.shortcuts import reverse
from django.core import mail

# third party imports
import pytest
from model_bakery import baker
from model_bakery.recipe import related
from rest_framework import status
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate

# my internal imports
from bugtracking.users.models import User
from bugtracking.tracker.models import (
    Team, TeamMembership, Project, ProjectMembership, Ticket, Comment, TeamInvitation
)
from bugtracking.tracker import views
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
        self.manager = base['manager']
        self.project = base['project']
        self.ticket = base['ticket']
        self.developer = base['developer']
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
        self.client.force_authenticate(self.admin)
        response = self.client.get(url)
        assert response.data[0]['title'] == 'team_title'
        assert len(response.data) == 1
        assert response.status_code == status.HTTP_200_OK

    def test_list_member(self):
        """Can view."""
        url = reverse('api:teams-list')
        self.client.force_authenticate(self.member)
        response = self.client.get(url)
        assert response.data[0]['title'] == 'team_title'
        assert len(response.data) == 1
        assert response.status_code == status.HTTP_200_OK

    def test_list_nonmember(self):
        """Cannot view."""
        url = reverse('api:teams-list')
        self.client.force_authenticate(self.nonmember)
        response = self.client.get(url)
        assert len(response.data) == 0
        assert response.status_code == status.HTTP_200_OK

    def test_list_anon(self):
        """Cannot view."""
        url = reverse('api:teams-list')
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN or response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_admin(self):
        """Can view."""
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_authenticate(self.admin)
        response = self.client.get(url)
        assert response.data['title'] == 'team_title'
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_member(self):
        """Can view."""
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_authenticate(self.member)
        response = self.client.get(url)
        assert response.data['title'] == 'team_title'
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_nonmember(self):
        """Cannot view."""
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_authenticate(self.nonmember)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_anon(self):
        """Cannot view."""
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN or response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_post_admin(self):
        """Can create."""
        url = reverse('api:teams-list')
        self.client.force_authenticate(self.admin)
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Team.objects.all().count() == 2
        new_team = Team.objects.get(slug='new-team')
        assert self.admin in new_team.get_admins()

    def test_post_nonmember(self):
        """Can create."""
        url = reverse('api:teams-list')
        self.client.force_authenticate(self.nonmember)
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Team.objects.all().count() == 2
        new_team = Team.objects.get(slug='new-team')
        assert self.nonmember in new_team.get_admins()

    def test_post_anon(self):
        """Cannot create."""
        url = reverse('api:teams-list')
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN or response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Team.objects.all().count() == 1

    def test_put_admin(self):
        """Can put."""
        old_title = self.team.title
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_authenticate(self.admin)
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
        self.client.force_authenticate(self.member)
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.team.refresh_from_db()
        # nothing should have updated
        assert not self.team.description == self.put_data['description']
        assert not self.team.title == "new updated title"

    def test_put_nonmember(self):
        """Cannot put."""
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_authenticate(self.nonmember)
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        self.team.refresh_from_db()
        # nothing should have updated
        assert not self.team.description == self.put_data['description']
        assert not self.team.title == "new updated title"

    def test_patch_admin(self):
        """Can patch."""
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_authenticate(self.admin)
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
        self.client.force_authenticate(self.member)
        response = self.client.patch(url, {'description': 'patch desc'})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.team.refresh_from_db()
        # nothing should have updated
        assert not self.team.description == 'patch desc'
        assert not self.team.title == "new updated title"

    def test_patch_nonmember(self):
        """Cannot patch."""
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_authenticate(self.nonmember)
        response = self.client.patch(url, {'description': 'patch desc'})
        assert response.status_code == status.HTTP_404_NOT_FOUND
        self.team.refresh_from_db()
        # nothing should have updated
        assert not self.team.description == 'patch desc'
        assert not self.team.title == "new updated title"

    def test_delete(self):
        """Teams cannot be deleted."""
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_authenticate(self.admin)
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Team.objects.all().count() == 1

    def test_title_cannot_be_updated(self):
        assert self.team.title == 'team_title'
        url = reverse('api:teams-detail', kwargs={'slug': self.team.slug})
        self.client.force_authenticate(self.admin)
        response = self.client.patch(url, {'title': 'updated title'})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.team.refresh_from_db()
        assert self.team.title == 'team_title'

    def test_removing_member(self):
        """Team admin can remove members from team."""
        self.team.add_member(self.nonmember)
        self.team.refresh_from_db()
        assert self.nonmember in self.team.members.all()
        url = reverse('api:teams-remove-member', kwargs={'slug': self.team.slug})
        self.client.force_authenticate(self.admin)
        response = self.client.put(url, {'member': 'nonmember'})
        assert response.status_code == status.HTTP_200_OK
        self.team.refresh_from_db()
        assert self.nonmember not in self.team.members.all()

    def test_removing_member_manager(self):
        """Team manager cannot remove members from team."""
        self.team.add_member(self.nonmember)
        self.team.refresh_from_db()
        assert self.nonmember in self.team.members.all()
        url = reverse('api:teams-remove-member', kwargs={'slug': self.team.slug})
        self.client.force_authenticate(self.manager)
        response = self.client.put(url, {'member': 'nonmember'})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.team.refresh_from_db()
        assert self.nonmember in self.team.members.all()

    def test_removing_member_also_removes_member_from_projects(self):
        """Removing a member from the team also removes him from all associated projects."""
        assert self.manager in self.team.members.all()
        assert self.manager in self.project.members.all()
        assert self.manager == self.project.manager
        url = reverse('api:teams-remove-member', kwargs={'slug': self.team.slug})
        self.client.force_authenticate(self.admin)
        response = self.client.put(url, {'member': 'manager'})
        assert response.status_code == status.HTTP_200_OK
        self.team.refresh_from_db()
        self.project.refresh_from_db()
        assert self.manager not in self.team.members.all()
        assert self.manager not in self.project.members.all()
        assert self.manager != self.project.manager

    def test_removing_member_also_removes_member_from_tickets(self):
        """Removing a member from the team also removes him from all associated tickets."""
        assert self.developer in self.team.members.all()
        assert self.developer in self.project.members.all()
        assert self.developer == self.ticket.developer
        url = reverse('api:teams-remove-member', kwargs={'slug': self.team.slug})
        self.client.force_authenticate(self.admin)
        response = self.client.put(url, {'member': 'developer'})
        assert response.status_code == status.HTTP_200_OK
        self.team.refresh_from_db()
        self.project.refresh_from_db()
        self.ticket.refresh_from_db()
        assert self.developer not in self.team.members.all()
        assert self.developer not in self.project.members.all()
        assert self.developer != self.ticket.developer

    def test_member_may_leave_team(self):
        assert self.member in self.team.members.all()
        url = reverse('api:teams-leave-team', kwargs={'slug': self.team.slug})
        self.client.force_authenticate(self.member)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        self.team.refresh_from_db()
        assert self.member not in self.team.members.all()

    def test_admin_may_not_leave_team(self):
        assert self.admin in self.team.members.all()
        url = reverse('api:teams-leave-team', kwargs={'slug': self.team.slug})
        self.client.force_authenticate(self.admin)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.team.refresh_from_db()
        assert self.admin in self.team.members.all()

    def test_user_may_not_force_other_user_to_leave_team(self):
        assert self.member in self.team.members.all()
        url = reverse('api:teams-leave-team', kwargs={'slug': self.team.slug})
        self.client.force_authenticate(self.admin)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.team.refresh_from_db()
        assert self.member in self.team.members.all()

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
        self.ticket = base['ticket']
        self.developer = base['developer']
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
        self.client.force_authenticate(self.admin)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]['title'] == self.project.title
        assert len(response.data) == 1

    def test_list_manager(self):
        """Can view."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        self.client.force_authenticate(self.manager)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]['title'] == self.project.title
        assert len(response.data) == 1

    def test_list_member(self):
        """Can view."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        self.client.force_authenticate(self.member)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]['title'] == self.project.title
        assert len(response.data) == 1

    def test_list_team_member(self):
        """Can view list, but project is not on it."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        self.client.force_authenticate(self.team_member)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0

    def test_list_nonmember(self):
        """Cannot view."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        self.client.force_authenticate(self.nonmember)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_anon(self):
        """Cannot view."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN or response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_admin(self):
        """Can view."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.admin)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == self.project.title

    def test_retrieve_manager(self):
        """Can view."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.manager)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == self.project.title

    def test_retrieve_member(self):
        """Can view."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.member)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == self.project.title

    def test_retrieve_team_member(self):
        """Cannot view."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.team_member)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_nonmember(self):
        """Cannot view."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.nonmember)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_anon(self):
        """Cannot view."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.nonmember)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_post_admin(self):
        """Can create."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        self.client.force_authenticate(self.admin)
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Project.objects.all().count() == 2
        new_project = Project.objects.get(slug='new-project')
        assert new_project.team == self.team

    def test_post_new_with_manager_assigned(self):
        """Can create."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        self.client.force_authenticate(self.admin)
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
        self.client.force_authenticate(self.manager)
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Project.objects.all().count() == 1

    def test_post_member(self):
        """Cannot create."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        self.client.force_authenticate(self.member)
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Project.objects.all().count() == 1

    def test_post_team_member(self):
        """Cannot create."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        self.client.force_authenticate(self.team_member)
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Project.objects.all().count() == 1

    def test_post_nonmember(self):
        """Cannot create."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        self.client.force_authenticate(self.nonmember)
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Project.objects.all().count() == 1

    def test_post_anon(self):
        """Cannot create."""
        url = reverse('api:projects-list', kwargs={'team_slug': self.team.slug})
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN or response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Project.objects.all().count() == 1

    def test_put_admin(self):
        """Can put."""
        assert self.project.is_archived == False
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.admin)
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
        self.client.force_authenticate(self.manager)
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_200_OK
        self.project.refresh_from_db()
        assert self.project.title == 'Updated Title'
        assert self.project.description == 'Updated description'
        assert self.project.is_archived == True

    def test_put_member(self):
        """Cannot put."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.member)
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Project.objects.all().count() == 1
        self.project.refresh_from_db()
        assert not self.project.title == self.put_data['title']
        assert not self.project.description == self.put_data['description']

    def test_put_team_member(self):
        """Cannot put."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.team_member)
        response = self.client.put(url, self.put_data)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Project.objects.all().count() == 1
        self.project.refresh_from_db()
        assert not self.project.title == self.put_data['title']
        assert not self.project.description == self.put_data['description']

    def test_put_nonmember(self):
        """Cannot put."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.nonmember)
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
        assert response.status_code == status.HTTP_403_FORBIDDEN or response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Project.objects.all().count() == 1
        self.project.refresh_from_db()
        assert not self.project.title == self.put_data['title']
        assert not self.project.description == self.put_data['description']

    def test_patch_admin(self):
        """Can patch."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.admin)
        response = self.client.patch(url, {'title': 'patch title', 'description': 'patch desc'})
        assert response.status_code == status.HTTP_200_OK
        self.project.refresh_from_db()
        assert self.project.title == 'patch title'
        assert self.project.description == 'patch desc'

    def test_patch_manager(self):
        """Can patch."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.manager)
        response = self.client.patch(url, {'title': 'patch title', 'description': 'patch desc'})
        assert response.status_code == status.HTTP_200_OK
        self.project.refresh_from_db()
        assert self.project.title == 'patch title'
        assert self.project.description == 'patch desc'

    def test_patch_member(self):
        """Cannot patch."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.member)
        response = self.client.patch(url, {'title': 'patch title', 'description': 'patch desc'})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.project.refresh_from_db()
        assert not self.project.title == 'patch title'
        assert not self.project.description == 'patch desc'

    def test_patch_team_member(self):
        """Cannot patch."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.team_member)
        response = self.client.patch(url, {'title': 'patch title', 'description': 'patch desc'})
        assert response.status_code == status.HTTP_404_NOT_FOUND
        self.project.refresh_from_db()
        assert not self.project.title == 'patch title'
        assert not self.project.description == 'patch desc'

    def test_patch_nonmember(self):
        """Cannot patch."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.nonmember)
        response = self.client.patch(url, {'title': 'patch title', 'description': 'patch desc'})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.project.refresh_from_db()
        assert not self.project.title == 'patch title'
        assert not self.project.description == 'patch desc'

    def test_admin_delete(self):
        """Can delete."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.admin)
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Project.objects.all().count() == 0

    def test_manager_delete(self):
        """Can delete."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.manager)
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Project.objects.all().count() == 0

    def test_member_delete(self):
        """Cannot delete."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.member)
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Project.objects.all().count() == 1

    def test_team_member_delete(self):
        """Cannot delete."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.team_member)
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Project.objects.all().count() == 1

    def test_nonmember_delete(self):
        """Cannot delete."""
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.nonmember)
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
        self.client.force_authenticate(self.admin)
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
        self.client.force_authenticate(self.admin)
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
        self.client.force_authenticate(self.manager)
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
        self.client.force_authenticate(self.manager)
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
        self.client.force_authenticate(self.admin)
        response = self.client.get(url)
        assert len(response.data) ==  2
        assert response.data[0]['title'] == 'project_title'
        assert response.data[1]['title'] == new_project.title

    def test_adding_new_member(self):
        """Team admin can add new members to project."""
        self.team.add_member(self.nonmember)
        self.team.refresh_from_db()
        assert self.nonmember in self.team.members.all()
        assert self.nonmember not in self.project.members.all()
        url = reverse('api:projects-add-member', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.admin)
        response = self.client.put(url, {'member': 'nonmember'})
        assert response.status_code == status.HTTP_200_OK
        self.project.refresh_from_db()
        assert self.nonmember in self.project.members.all()

    def test_adding_new_member_manager(self):
        """Project manager can add new members."""
        self.team.add_member(self.nonmember)
        self.team.refresh_from_db()
        assert self.nonmember in self.team.members.all()
        assert self.nonmember not in self.project.members.all()
        url = reverse('api:projects-add-member', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.manager)
        response = self.client.put(url, {'member': 'nonmember'})
        assert response.status_code == status.HTTP_200_OK
        self.project.refresh_from_db()
        assert self.nonmember in self.project.members.all()

    def test_adding_new_member_member(self):
        """Project member cannot add new members."""
        self.team.add_member(self.nonmember)
        self.team.refresh_from_db()
        assert self.nonmember in self.team.members.all()
        assert self.nonmember not in self.project.members.all()
        url = reverse('api:projects-add-member', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.member)
        response = self.client.put(url, {'member': 'nonmember'})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.project.refresh_from_db()
        assert self.nonmember not in self.project.members.all()

    def test_removing_member(self):
        """Team admin can remove members from project."""
        self.team.add_member(self.nonmember)
        self.project.add_member(self.nonmember)
        assert self.nonmember in self.project.members.all()
        url = reverse('api:projects-remove-member', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.admin)
        response = self.client.put(url, {'member': 'nonmember'})
        assert response.status_code == status.HTTP_200_OK
        self.project.refresh_from_db()
        assert self.nonmember not in self.project.members.all()

    def test_removing_member_manager(self):
        """Project manager can remove members from project."""
        self.team.add_member(self.nonmember)
        self.project.add_member(self.nonmember)
        assert self.nonmember in self.project.members.all()
        url = reverse('api:projects-remove-member', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.admin)
        response = self.client.put(url, {'member': 'nonmember'})
        assert response.status_code == status.HTTP_200_OK
        self.project.refresh_from_db()
        assert self.nonmember not in self.project.members.all()

    def test_removing_member_member(self):
        """Project member cannot remove members from project."""
        self.team.add_member(self.nonmember)
        self.project.add_member(self.nonmember)
        assert self.nonmember in self.project.members.all()
        url = reverse('api:projects-remove-member', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.member)
        response = self.client.put(url, {'member': 'nonmember'})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.project.refresh_from_db()
        assert self.nonmember in self.project.members.all()

    def test_removing_developer_removes_from_ticket_developer_field(self):
        """Removing a member who is a developer of a ticket clears that ticket's developer field."""
        assert self.developer in self.project.members.all()
        assert self.ticket in self.project.tickets.all()
        assert self.ticket.developer == self.developer
        url = reverse('api:projects-remove-member', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.admin)
        response = self.client.put(url, {'member': 'developer'})
        assert response.status_code == status.HTTP_200_OK
        self.project.refresh_from_db()
        self.ticket.refresh_from_db()
        assert self.developer not in self.project.members.all()
        assert self.ticket in self.project.tickets.all()
        assert self.ticket.developer != self.developer

    def test_archive_project(self):
        """Can archive."""
        assert self.project.is_archived == False
        url = reverse('api:projects-detail', kwargs={'team_slug': self.team.slug, 'slug': self.project.slug})
        self.client.force_authenticate(self.admin)
        response = self.client.put(url, {'is_archived': 'true', 'title': self.project.title})
        assert response.status_code == status.HTTP_200_OK
        self.project.refresh_from_db()
        assert self.project.is_archived == True


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
        self.client.force_authenticate(self.admin)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]['title'] == self.ticket.title
        assert len(response.data) == 1

    def test_list_manager(self):
        """Can view."""
        url = reverse('api:tickets-list', kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug})
        self.client.force_authenticate(self.manager)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]['title'] == self.ticket.title
        assert len(response.data) == 1

    def test_list_team_member(self):
        """Cannot view."""
        url = reverse('api:tickets-list', kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug})
        self.client.force_authenticate(self.team_member)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert len(response.data) == 1

    def test_list_nonmember(self):
        """Cannot view."""
        url = reverse('api:tickets-list', kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug})
        self.client.force_authenticate(self.nonmember)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert len(response.data) == 1

    def test_retrieve_admin(self):
        """Can view."""
        url = reverse('api:tickets-detail',
                      kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug, 'slug': self.ticket.slug})
        self.client.force_authenticate(self.admin)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == self.ticket.title

    def test_retrieve_manager(self):
        """Can view."""
        url = reverse('api:tickets-detail',
                      kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug, 'slug': self.ticket.slug})
        self.client.force_authenticate(self.manager)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == self.ticket.title

    def test_retrieve_team_member(self):
        """Cannot view."""
        url = reverse('api:tickets-detail',
                      kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug, 'slug': self.ticket.slug})
        self.client.force_authenticate(self.team_member)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_nonmember(self):
        """Cannot view."""
        url = reverse('api:tickets-detail',
                      kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug, 'slug': self.ticket.slug})
        self.client.force_authenticate(self.nonmember)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_post_admin(self):
        """Can post."""
        url = reverse('api:tickets-list', kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug})
        user = self.admin
        self.client.force_authenticate(user)
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
        self.client.force_authenticate(user)
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
        self.client.force_authenticate(user)
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
        self.client.force_authenticate(user)
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Ticket.objects.all().count() == 1

    def test_post_nonmember(self):
        """Cannot post."""
        url = reverse('api:tickets-list',
                      kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug})
        user = self.nonmember
        self.client.force_authenticate(user)
        response = self.client.post(url, self.post_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Ticket.objects.all().count() == 1

    def test_post_new_with_developer_assigned(self):
        url = reverse('api:tickets-list',
                      kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug})
        user = self.admin
        self.client.force_authenticate(user)
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
        self.client.force_authenticate(user)
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
        self.client.force_authenticate(user)
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
        self.client.force_authenticate(user)
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
        self.client.force_authenticate(user)
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
        self.client.force_authenticate(user)
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
        self.client.force_authenticate(user)
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
        self.client.force_authenticate(user)
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
        self.client.force_authenticate(user)
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
        self.client.force_authenticate(user)
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
        self.client.force_authenticate(user)
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
        self.client.force_authenticate(user)
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
        self.client.force_authenticate(user)
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
        self.client.force_authenticate(user)
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
        self.client.force_authenticate(user)
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
        self.client.force_authenticate(user)
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
        self.client.force_authenticate(user)
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
        self.client.force_authenticate(user)
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
        self.client.force_authenticate(user)
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
        self.client.force_authenticate(self.admin)
        response = self.client.get(url)
        assert len(response.data) == 1
        assert response.data[0]['title'] != other_team_ticket.title
        assert response.data[0]['title'] != other_project_ticket


class TestTeamInvitationViewSet(APITestCase):
    def setUp(self):
        base = fac()
        self.team = base['team']
        self.admin = base['admin']
        self.member = base['member']

    def test_admin_list(self):
        """Can view list."""
        user = self.admin
        invite = baker.make(TeamInvitation, team=self.team)
        second_invite = baker.make(TeamInvitation, team=self.team)
        other_team_invite = baker.make(TeamInvitation)
        url = reverse('api:invitations-list', kwargs={'team_slug': self.team.slug})
        self.client.force_authenticate(user)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        assert response.data[0]['id'] == str(invite.id)
        assert response.data[1]['id'] == str(second_invite.id)

    def test_member_list(self):
        """Cannot view list."""
        user = self.member
        invite = baker.make(TeamInvitation, team=self.team)
        second_invite = baker.make(TeamInvitation, team=self.team)
        other_team_invite = baker.make(TeamInvitation)
        url = reverse('api:invitations-list', kwargs={'team_slug': self.team.slug})
        self.client.force_authenticate(user)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert len(response.data) == 1
        assert response.data['errors'] == "Only a team administrator may view or manage team invitations."

    def test_admin_detail(self):
        """Can view details."""
        user = self.admin
        invite = baker.make(TeamInvitation, team=self.team)
        url = reverse('api:invitations-detail', kwargs={'team_slug': self.team.slug, 'id': str(invite.id)})
        self.client.force_authenticate(user)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(invite.id)

    def test_member_detail(self):
        """Cannot view details."""
        user = self.member
        invite = baker.make(TeamInvitation, team=self.team)
        url = reverse('api:invitations-detail', kwargs={'team_slug': self.team.slug, 'id': str(invite.id)})
        self.client.force_authenticate(user)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert str(response.data['errors']) == "Only a team administrator may view or manage team invitations."

    def test_admin_post(self):
        """Can post. Creates new invitation tied to the team identified in the url."""
        user = self.admin
        url = reverse('api:invitations-list', kwargs={'team_slug': self.team.slug})
        self.client.force_authenticate(user)
        response = self.client.post(url, {'invitee_email': 'test@email.com'})
        assert response.status_code == status.HTTP_201_CREATED
        invitation = TeamInvitation.objects.last()
        assert invitation.team == self.team
        assert invitation.inviter == user
        assert invitation.invitee_email == 'test@email.com'

    def test_member_post(self):
        """Cannot post."""
        user = self.member
        url = reverse('api:invitations-list', kwargs={'team_slug': self.team.slug})
        self.client.force_authenticate(user)
        response = self.client.post(url, {'invitee_email': 'test@email.com'})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert TeamInvitation.objects.count() == 0
        assert response.data['errors'] == "Only a team administrator may view or manage team invitations."

    def test_admin_delete(self):
        """Can delete."""
        user = self.admin
        invite = baker.make(TeamInvitation, team=self.team)
        url = reverse('api:invitations-detail', kwargs={'team_slug': self.team.slug, 'id': str(invite.id)})
        self.client.force_authenticate(user)
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert TeamInvitation.objects.count() == 0

    def test_member_delete(self):
        """Cannot delete."""
        user = self.member
        invite = baker.make(TeamInvitation, team=self.team)
        url = reverse('api:invitations-detail', kwargs={'team_slug': self.team.slug, 'id': str(invite.id)})
        self.client.force_authenticate(user)
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert TeamInvitation.objects.count() == 1

    def test_put(self):
        """Method is invalid."""
        user = self.admin
        invite = baker.make(TeamInvitation, team=self.team)
        url = reverse('api:invitations-detail', kwargs={'team_slug': self.team.slug, 'id': str(invite.id)})
        self.client.force_authenticate(user)
        response = self.client.put(url, {'invitee_email': 'updated@email.com'})
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert invite.invitee_email != 'updated@email.com'

    def test_patch(self):
        """Method is invalid."""
        user = self.admin
        invite = baker.make(TeamInvitation, team=self.team)
        url = reverse('api:invitations-detail', kwargs={'team_slug': self.team.slug, 'id': str(invite.id)})
        self.client.force_authenticate(user)
        response = self.client.patch(url, {'invitee_email': 'updated@email.com'})
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert invite.invitee_email != 'updated@email.com'

    def test_inviting_user_who_is_already_a_member(self):
        """Post returns an error message saying the user is already a member. Does not create a new invitation."""
        number_of_invitations = TeamInvitation.objects.count()
        self.member.email = 'already_member@email.com'
        self.member.save()
        user = self.admin
        url = reverse('api:invitations-list', kwargs={'team_slug': self.team.slug})
        self.client.force_authenticate(user)
        response = self.client.post(url, {'invitee_email': self.member.email})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert TeamInvitation.objects.count() == number_of_invitations
        assert response.data['errors'] == 'User is already a member of this team.'

    def test_inviting_user_who_was_invited_days_ago(self):
        """Should create a new invitation object since enough time has passed."""
        user = self.admin
        invite = baker.make(TeamInvitation, team=self.team)
        invite.created = dt.datetime.now() - dt.timedelta(days=5)
        invite.save()
        invite.refresh_from_db()
        assert TeamInvitation.objects.count() == 1
        email = invite.invitee_email
        url = reverse('api:invitations-list', kwargs={'team_slug': self.team.slug})
        self.client.force_authenticate(user)
        response = self.client.post(url, {'invitee_email': email})
        assert response.status_code == status.HTTP_201_CREATED
        assert TeamInvitation.objects.count() == 2

    def test_inviting_user_who_was_invited_just_now(self):
        """Should not create a new invitation object as user was just invited recently."""
        user = self.admin
        invite = baker.make(TeamInvitation, team=self.team)
        assert TeamInvitation.objects.count() == 1
        email = invite.invitee_email
        url = reverse('api:invitations-list', kwargs={'team_slug': self.team.slug})
        self.client.force_authenticate(user)
        response = self.client.post(url, {'invitee_email': email})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert TeamInvitation.objects.count() == 1



class TestInvitationEmailSending(APITestCase):
    def setUp(self) -> None:
        base = fac()
        self.team = base['team']
        self.admin = base['admin']
        self.member = base['member']

    def test_email_is_sent(self):
        """Tests that email is sent, as well as email's details."""
        user = self.admin
        url = reverse('api:invitations-list', kwargs={'team_slug': self.team.slug})
        self.client.force_authenticate(user)
        response = self.client.post(url, {'invitee_email': 'test@email.com'})
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.subject == 'Team Invitation'
        assert str(self.team.title) in email.body
        assert 'test@email.com' in email.to

    def test_resending_invitation_email(self):
        user = self.admin
        invitation = baker.make(TeamInvitation, team=self.team, inviter=self.admin)
        url = reverse('api:invitations-resend-email', kwargs={'team_slug': self.team.slug, 'id': str(invitation.id)})
        self.client.force_authenticate(user)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'Invitation email sent successfully.'
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.subject == 'Team Invitation'
        assert 'You are receiving this invitation again' in email.body
        assert invitation.invitee_email in email.to

    def test_non_admins_cant_resend_email(self):
        user = self.member
        invitation = baker.make(TeamInvitation, team=self.team, inviter=self.admin)
        url = reverse('api:invitations-resend-email', kwargs={'team_slug': self.team.slug, 'id': str(invitation.id)})
        self.client.force_authenticate(user)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert len(mail.outbox) == 0


class TestAcceptInvitation(APITestCase):
    def setUp(self):
        base = fac()
        self.team = base['team']
        self.invitee = user(username='invitee')
        self.invitee.email = 'test@email.com'
        self.invitee.save()
        self.invitation = baker.make(TeamInvitation, invitee_email=self.invitee.email, team=self.team)

    def test_invitee_can_accept(self):
        """Tests that user can accept the invitation and that the user is successfully added to the team's members."""
        user = self.invitee
        assert user not in self.team.members.all()
        url = f"{reverse('api:teams-accept-invitation', kwargs={'slug': self.team.slug})}?invitation={str(self.invitation.id)}"
        self.client.force_authenticate(user)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'Invitation accepted.'
        self.team.refresh_from_db()
        self.invitation.refresh_from_db()
        assert self.invitation.status == TeamInvitation.Status.ACCEPTED
        assert user in self.team.members.all()

    def test_invalid_team(self):
        """Fails with a 400 bad request."""
        user = self.invitee
        assert user not in self.team.members.all()
        url = f"{reverse('api:teams-accept-invitation', kwargs={'slug': 'invalid'})}?invitation={str(self.invitation.id)}"
        self.client.force_authenticate(user)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['errors'] == 'Invitation not found.'
        self.team.refresh_from_db()
        self.invitation.refresh_from_db()
        assert self.invitation.status == TeamInvitation.Status.PENDING
        assert user not in self.team.members.all()

    def test_invalid_invitation_id(self):
        """Fails with a 400 bad request."""
        user = self.invitee
        assert user not in self.team.members.all()
        url = f"{reverse('api:teams-accept-invitation', kwargs={'slug': self.team.slug})}?invitation=invalid"
        self.client.force_authenticate(user)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['errors'] == 'Invitation not found.'
        self.team.refresh_from_db()
        self.invitation.refresh_from_db()
        assert self.invitation.status == TeamInvitation.Status.PENDING
        assert user not in self.team.members.all()

    def test_uninvited_user_accesses_valid_invitation_url(self):
        """Fails with a 403 forbidden."""
        user = User.objects.create_user(username='not_invited', password='password')
        user.email = 'invalid@email.com'
        user.save()
        assert user not in self.team.members.all()
        url = f"{reverse('api:teams-accept-invitation', kwargs={'slug': self.team.slug})}?invitation={str(self.invitation.id)}"
        self.client.force_authenticate(user)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['errors'] == 'Invitation not found.'
        self.team.refresh_from_db()
        self.invitation.refresh_from_db()
        assert self.invitation.status == TeamInvitation.Status.PENDING
        assert user not in self.team.members.all()

    def test_invited_user_accesses_wrong_invitation_uuid(self):
        """An invited user accessing an invalid invitation UUID receives the 400 bad request error in response."""
        other_invitation = baker.make(TeamInvitation, team=self.team)
        user = self.invitee
        assert user not in self.team.members.all()
        url = f"{reverse('api:teams-accept-invitation', kwargs={'slug': self.team.slug})}?invitation={str(other_invitation.id)}"
        self.client.force_authenticate(user)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['errors'] == 'Invitation not found.'
        self.team.refresh_from_db()
        self.invitation.refresh_from_db()
        assert self.invitation.status == TeamInvitation.Status.PENDING
        assert user not in self.team.members.all()

    def test_anonymous_user(self):
        """Fails with a 401 or 403 forbidden."""
        url = f"{reverse('api:teams-accept-invitation', kwargs={'slug': self.team.slug})}?invitation={str(self.invitation.id)}"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN or response.status_code == status.HTTP_401_UNAUTHORIZED
        self.team.refresh_from_db()
        self.invitation.refresh_from_db()
        assert self.invitation.status == TeamInvitation.Status.PENDING


class TestDeclineInvitation(APITestCase):
    def setUp(self):
        base = fac()
        self.team = base['team']
        self.invitee = user(username='invitee')
        self.invitee.email = 'test@email.com'
        self.invitee.save()
        self.invitation = baker.make(TeamInvitation, invitee_email=self.invitee.email, team=self.team)

    def test_invitee_can_decline(self):
        """Tests that user can decline the invitation."""
        user = self.invitee
        assert user not in self.team.members.all()
        url = f"{reverse('api:teams-decline-invitation', kwargs={'slug': self.team.slug})}?invitation={str(self.invitation.id)}"
        self.client.force_authenticate(user)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'Invitation declined.'
        self.team.refresh_from_db()
        self.invitation.refresh_from_db()
        assert self.invitation.status == TeamInvitation.Status.DECLINED
        assert user not in self.team.members.all()

    def test_invalid_team(self):
        """Fails with a 400 bad request."""
        user = self.invitee
        assert user not in self.team.members.all()
        url = f"{reverse('api:teams-decline-invitation', kwargs={'slug': 'invalid'})}?invitation={str(self.invitation.id)}"
        self.client.force_authenticate(user)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['errors'] == 'Invitation not found.'
        self.team.refresh_from_db()
        self.invitation.refresh_from_db()
        assert self.invitation.status == TeamInvitation.Status.PENDING
        assert user not in self.team.members.all()

    def test_invalid_invitation_id(self):
        """Fails with a 400 bad request."""
        user = self.invitee
        assert user not in self.team.members.all()
        url = f"{reverse('api:teams-decline-invitation', kwargs={'slug': self.team.slug})}?invitation=invalid"
        self.client.force_authenticate(user)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['errors'] == 'Invitation not found.'
        self.team.refresh_from_db()
        self.invitation.refresh_from_db()
        assert self.invitation.status == TeamInvitation.Status.PENDING
        assert user not in self.team.members.all()

    def test_uninvited_user_accesses_valid_invitation_url(self):
        """Fails with a 403 forbidden."""
        user = User.objects.create_user(username='not_invited', password='password')
        user.email = 'invalid@email.com'
        user.save()
        assert user not in self.team.members.all()
        url = f"{reverse('api:teams-decline-invitation', kwargs={'slug': self.team.slug})}?invitation={str(self.invitation.id)}"
        self.client.force_authenticate(user)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['errors'] == 'Invitation not found.'
        self.team.refresh_from_db()
        self.invitation.refresh_from_db()
        assert self.invitation.status == TeamInvitation.Status.PENDING
        assert user not in self.team.members.all()

    def test_invited_user_accesses_wrong_invitation_uuid(self):
        """An invited user accessing an invalid invitation UUID receives the 400 bad request error in response."""
        other_invitation = baker.make(TeamInvitation, team=self.team)
        user = self.invitee
        assert user not in self.team.members.all()
        url = f"{reverse('api:teams-decline-invitation', kwargs={'slug': self.team.slug})}?invitation={str(other_invitation.id)}"
        self.client.force_authenticate(user)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['errors'] == 'Invitation not found.'
        self.team.refresh_from_db()
        self.invitation.refresh_from_db()
        assert self.invitation.status == TeamInvitation.Status.PENDING
        assert user not in self.team.members.all()

    def test_anonymous_user(self):
        """Fails with a 403 forbidden."""
        url = f"{reverse('api:teams-decline-invitation', kwargs={'slug': self.team.slug})}?invitation={str(self.invitation.id)}"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN or response.status_code == status.HTTP_401_UNAUTHORIZED
        self.team.refresh_from_db()
        self.invitation.refresh_from_db()
        assert self.invitation.status == TeamInvitation.Status.PENDING


class TestChangingTeamAdmins(APITestCase):
    def setUp(self) -> None:
        base = fac()
        self.team = base['team']
        self.admin = base['admin']
        self.member = base['member']
        self.nonmember = base['nonmember']

    def test_admin_can_step_down_when_second_admin_exists(self):
        self.team.make_admin(self.member)
        user = self.admin
        url = reverse('api:teams-step-down-as-admin', kwargs={'slug': self.team.slug})
        self.client.force_authenticate(user)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'You have successfully stepped down as team admin.'
        self.team.refresh_from_db()
        assert self.admin not in self.team.get_admins()

    def test_member_gets_permission_denied(self):
        user = self.member
        url = reverse('api:teams-step-down-as-admin', kwargs={'slug': self.team.slug})
        self.client.force_authenticate(user)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data['errors'] == 'Only team administrators may perform that action.'
        self.team.refresh_from_db()
        assert self.admin in self.team.get_admins()

    def test_admin_cannot_step_down_if_only_one_admin(self):
        user = self.admin
        url = reverse('api:teams-step-down-as-admin', kwargs={'slug': self.team.slug})
        self.client.force_authenticate(user)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['errors'] == 'You cannot step down as team administrator if you are the only administration. Pleasea promote another member to administrator first.'
        self.team.refresh_from_db()
        assert self.admin in self.team.get_admins()

    def test_promoting_new_admin(self):
        assert self.member not in self.team.get_admins()
        user = self.admin
        url = reverse('api:teams-promote-admin', kwargs={'slug': self.team.slug})
        self.client.force_authenticate(user)
        response = self.client.post(url, {'user': self.member.username})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'Member successfully promoted to administrator.'
        self.team.refresh_from_db()
        assert self.admin in self.team.get_admins()
        assert self.member in self.team.get_admins()

    def test_non_admin_cant_promote_admin(self):
        user = self.member
        url = reverse('api:teams-promote-admin', kwargs={'slug': self.team.slug})
        self.client.force_authenticate(user)
        response = self.client.post(url, {'user': self.member.username})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data['errors'] == 'Only team administrators may perform that action.'
        self.team.refresh_from_db()
        assert self.admin in self.team.get_admins()
        assert self.member not in self.team.get_admins()

    def test_promoting_nonexistent_user_fails(self):
        user = self.admin
        url = reverse('api:teams-promote-admin', kwargs={'slug': self.team.slug})
        self.client.force_authenticate(user)
        response = self.client.post(url, {'user': 'user_does_not_exist'})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['errors'] == 'User does not exist.'
        self.team.refresh_from_db()
        assert self.admin in self.team.get_admins()
        assert self.member not in self.team.get_admins()

    def test_promoting_user_who_is_not_team_member_fails(self):
        user = self.admin
        url = reverse('api:teams-promote-admin', kwargs={'slug': self.team.slug})
        self.client.force_authenticate(user)
        response = self.client.post(url, {'user': self.nonmember.username})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['errors'] == 'Cannot make user an admin. User is not a member of your team.'
        self.team.refresh_from_db()
        assert self.admin in self.team.get_admins()
        assert self.nonmember not in self.team.get_admins()


class TestPostingComments(APITestCase):
    def setUp(self) -> None:
        base = fac()
        self.member = base['member']
        self.nonmember = base['nonmember']
        self.team = base['team']
        self.project = base['project']
        self.project.add_member(self.member)
        self.team_member = user('team_member')
        self.team.add_member(self.team_member)
        self.ticket = base['ticket']
        self.post_data = {
            'text': 'New comment'
        }

    def test_post_member(self):
        """Can post."""
        assert len(self.ticket.comments.all()) == 0
        user = self.member
        url = reverse('api:tickets-create-comment', kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug, 'slug': self.ticket.slug})
        self.client.force_authenticate(user)
        response = self.client.post(url, data=self.post_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data == {'status': 'Comment created.'}
        assert len(self.ticket.comments.all()) == 1

    def test_post_nonmember(self):
        """Cannot post."""
        assert len(self.ticket.comments.all()) == 0
        user = self.nonmember
        url = reverse('api:tickets-create-comment', kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug, 'slug': self.ticket.slug})
        self.client.force_authenticate(user)
        response = self.client.post(url, data=self.post_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert len(self.ticket.comments.all()) == 0

    def test_post_team_member(self):
        """Cannot post. User is a member of the team but not the project."""
        assert len(self.ticket.comments.all()) == 0
        user = self.team_member
        url = reverse('api:tickets-create-comment', kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug, 'slug': self.ticket.slug})
        self.client.force_authenticate(user)
        response = self.client.post(url, data=self.post_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert len(self.ticket.comments.all()) == 0

    def test_post_with_missing_text(self):
        """Cannot post. Text is required."""
        assert len(self.ticket.comments.all()) == 0
        user = self.member
        url = reverse('api:tickets-create-comment', kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug, 'slug': self.ticket.slug})
        self.client.force_authenticate(user)
        response = self.client.post(url, data={'text': ''})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert len(self.ticket.comments.all()) == 0

class TestTicketPermissionsEndpoint(APITestCase):
    def setUp(self) -> None:
        base = fac()
        self.admin = base['admin']
        self.member = base['member']
        self.team = base['team']
        self.project = base['project']
        self.ticket = base['ticket']

    def test_response_status(self):
        """Tests the response status code."""
        user = self.member
        url = reverse('api:tickets-get-user-permissions', kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug, 'slug': self.ticket.slug})
        self.client.force_authenticate(user)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_response_content_exists(self):
        """Tests that the appropriate keys, representing the different permissions, exist in the response."""
        user = self.member
        url = reverse('api:tickets-get-user-permissions',
                      kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug,
                              'slug': self.ticket.slug})
        self.client.force_authenticate(user)
        response = self.client.get(url)
        keys = response.data.keys()
        assert 'view' in keys
        assert 'edit' in keys
        assert 'delete' in keys
        assert 'change_developer' in keys
        assert 'close' in keys

    def test_response_content_accurate_for_member(self):
        """
        Tests that the response content accurately reflects the user's permissions.
        User is a project member, so user should be able to view, but nothing else.
        """
        user = self.member
        url = reverse('api:tickets-get-user-permissions',
                      kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug,
                              'slug': self.ticket.slug})
        self.client.force_authenticate(user)
        response = self.client.get(url)
        data = response.data
        assert data['view'] == True
        assert data['edit'] == False
        assert data['delete'] == False
        assert data['change_developer'] == False
        assert data['close'] == False

    def test_response_content_accurate_for_admin(self):
        """
        Tests that the response content accurately reflects the user's permissions.
        User is a team admin, so all permissions should be true.
        """
        user = self.admin
        url = reverse('api:tickets-get-user-permissions',
                      kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug,
                              'slug': self.ticket.slug})
        self.client.force_authenticate(user)
        response = self.client.get(url)
        data = response.data
        assert data['view'] == True
        assert data['edit'] == True
        assert data['delete'] == True
        assert data['change_developer'] == True
        assert data['close'] == True

    def test_anon_user_gets_401(self):
        """Tests the response status code."""
        url = reverse('api:tickets-get-user-permissions',
                      kwargs={'team_slug': self.project.team.slug, 'project_slug': self.project.slug,
                              'slug': self.ticket.slug})
        response = self.client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

class TestProjectPermissionsEndpoint(APITestCase):
    def setUp(self) -> None:
        base = fac()
        self.admin = base['admin']
        self.member = base['member']
        self.nonmember = base['nonmember']
        self.team = base['team']
        self.project = base['project']
        self.project.add_member(self.member)
        self.team_member = user('team_member')
        self.team.add_member(self.team_member)
        self.ticket = base['ticket']
        self.url = reverse('api:projects-get-user-permissions', kwargs={'team_slug': self.project.team.slug, 'slug': self.project.slug})

    def test_response_status(self):
        """Tests the response status code."""
        user = self.member
        self.client.force_authenticate(user)
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_200_OK

    def test_response_content_exists(self):
        """Tests that the appropriate keys, representing the different permissions, exist in the response."""
        user = self.member
        self.client.force_authenticate(user)
        response = self.client.get(self.url)
        keys = response.data.keys()
        assert 'view' in keys
        assert 'edit' in keys
        assert 'update_manager' in keys
        assert 'create_tickets' in keys

    def test_response_content_accurate_for_member(self):
        """
        Tests that the response content accurately reflects the user's permissions.
        User is a project member, so user should be able to view project details and submit tickets.
        """
        user = self.member
        self.client.force_authenticate(user)
        response = self.client.get(self.url)
        data = response.data
        assert data['view'] == True
        assert data['edit'] == False
        assert data['update_manager'] == False
        assert data['create_tickets'] == True

    def test_response_content_accurate_for_admin(self):
        """
        Tests that the response content accurately reflects the user's permissions.
        User is a team admin, so all permissions should be true.
        """
        user = self.admin
        self.client.force_authenticate(user)
        response = self.client.get(self.url)
        data = response.data
        assert data['view'] == True
        assert data['edit'] == True
        assert data['update_manager'] == True
        assert data['create_tickets'] == True

    def test_anon_user_gets_401(self):
        """Tests the response status code."""
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
