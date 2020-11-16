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
from bugtracking.tracker.api.serializers import TeamSerializer
from .factories import model_setup as fac


