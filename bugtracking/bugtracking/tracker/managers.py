# stdlib imports

# core django imports
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _

# third party imports

# my internal imports
from . import models

User = get_user_model()


