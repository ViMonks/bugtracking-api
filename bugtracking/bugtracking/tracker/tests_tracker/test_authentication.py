# stdlib imports

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
from rest_framework.test import APITestCase, APIClient
from rest_framework.authtoken.models import Token
from allauth.account.models import EmailAddress


# my internal imports
from bugtracking.users.models import User
from bugtracking.tracker.models import (
    Team, TeamMembership, Project, ProjectMembership, Ticket, Comment, TeamInvitation
)
from .factories import model_setup as fac


# PYTEST FIXTURES
def user(username='admin'):
    return User.objects.create_user(username=username, password='password')


class TestDjangoUserAuthentication(APITestCase):
    def setUp(self) -> None:
        base = fac()
        self.admin = base['admin']
        self.admin.email = 'admin@email.com'
        self.admin.save()
        self.admin_email = EmailAddress.objects.create(user=self.admin, email=self.admin.email, primary=True, verified=True)
        self.url = reverse('api:teams-list')

    # all this is outdated
    # def test_auth_headers_token(self):
    #     client = APIClient()
    #     token_response = client.post(reverse('rest_auth:rest_login'), {'username': 'admin', 'password': 'password'})
    #     token_key = token_response.data['key']
    #     client.credentials(HTTP_AUTHORIZATION='Token '+token_key)
    #     response = client.get(self.url)
    #     assert response.status_code==status.HTTP_200_OK

    # def test_auth_headers_bearer(self):
    #     client = APIClient()
    #     token_response = client.post(reverse('rest_auth:rest_login'), {'username': 'admin', 'password': 'password'})
    #     token_key = token_response.data['key']
    #     client.credentials(HTTP_AUTHORIZATION='Bearer '+token_key)
    #     response = client.get(self.url)
    #     assert response.status_code==status.HTTP_200_OK
