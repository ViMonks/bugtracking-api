from rest_framework.authentication import TokenAuthentication

class BearerAuthentication(TokenAuthentication):
    """
    Simply changes the authorization header from 'Token' to 'Bearer' to be consistent with the social oauth header from DRF Social OAuth2.
    """
    keyword = 'Bearer'
