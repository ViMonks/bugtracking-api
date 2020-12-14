# std lib imports
import uuid

# django imports
from django.contrib.auth import get_user_model
from django.utils import timezone

# third party imports
from rest_framework import exceptions
from firebase_admin import auth as firebase_auth
from drf_firebase_auth.authentication import FirebaseAuthentication
from drf_firebase_auth.settings import api_settings

User = get_user_model()

class CustomFirebaseAuthentication(FirebaseAuthentication):
    def authenticate_token(self, decoded_token):
        """
        Returns firebase user if token is authenticated.
        Customized to fix a bug: original code was calling firebase_auth.AuthError, which doesn't exist. Perhaps deprecated. Updated to call firebase_auth.UserNotFoundError.
        """
        try:
            uid = decoded_token.get('uid')
            firebase_user = firebase_auth.get_user(uid)
            if api_settings.FIREBASE_AUTH_EMAIL_VERIFICATION:
                if not firebase_user.email_verified:
                    raise exceptions.AuthenticationFailed(
                        'Email address of this user has not been verified.'
                    )
            return firebase_user
        except ValueError:
            raise exceptions.AuthenticationFailed(
                'User ID is None, empty or malformed'
            )
        except firebase_auth.UserNotFoundError:
            raise exceptions.AuthenticationFailed(
                'Error retrieving the user, or the specified user ID does not '
                'exist'
            )

    def get_or_create_local_user(self, firebase_user):
        """
        Attempts to return or create a local User from Firebase user data.
        Customized to use the firebase_user's email as the Django username instead of uuid as username.
        Also customized to allow username lengths up to 50 characters instead of 30.
        """
        email = firebase_user.email if firebase_user.email \
            else firebase_user.provider_data[0].email
        try:
            user = User.objects.get(email=email)
            if not user.is_active:
                raise exceptions.AuthenticationFailed(
                    'User account is not currently active.'
                )
            user.last_login = timezone.now()
            user.save()
            return user
        except User.DoesNotExist:
            if not api_settings.FIREBASE_CREATE_LOCAL_USER:
                raise exceptions.AuthenticationFailed(
                    'User is not registered to the application.'
                )
            if firebase_user.display_name:
                username = '_'.join(
                    firebase_user.display_name.split(' ')
                )
            else:
                username = str(email)
            username = username if len(username) <= 50 else username[:50]
            new_user = User.objects.create_user(
                username=username,
                email=email
            )
            new_user.last_login = timezone.now()
            if api_settings.FIREBASE_ATTEMPT_CREATE_WITH_DISPLAY_NAME:
                display_name = firebase_user.display_name.split()
                if len(display_name) == 2:
                    new_user.first_name = display_name[0]
                    new_user.last_name = display_name[1]
            new_user.save()
            # self.create_local_firebase_user(new_user, firebase_user)
            return new_user
