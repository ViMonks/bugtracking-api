# stdlib imports

# core django imports
from django.contrib.auth import get_user_model

# third party imports
from model_bakery.recipe import Recipe, related

# my internal imports
from .models import (
    Team, TeamMembership, Project, ProjectMembership, ProjectSubscription, Ticket, TicketSubscription, Comment
)

User = get_user_model()

admin = Recipe(User, username='team_admin')
team = Recipe(Team, members=related('admin'))
