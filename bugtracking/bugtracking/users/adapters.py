from typing import Any

from django.urls import reverse

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.utils import build_absolute_uri
from django.conf import settings
from django.http import HttpRequest


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest):
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def get_email_confirmation_url(self, request, emailconfirmation):
        url = settings.CUSTOM_ACCOUNT_CONFIRMATION_EMAIL_URL.format(emailconfirmation.key)
        full_url = settings.FRONTEND_HOST + url
        return full_url


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest, sociallogin: Any):
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)
