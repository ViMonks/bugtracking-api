from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from rest_framework.authtoken.views import obtain_auth_token

from rest_auth import views as rest_auth_views
from rest_framework_social_oauth2.views import TokenView as token_login_view

# Frontend

urlpatterns = [
    path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
    path(
        "about/", TemplateView.as_view(template_name="pages/about.html"), name="about"
    ),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("bugtracking.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    # Your stuff: custom urls includes go here
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# API URLS
urlpatterns += [
    # API base url
    path("api/", include("config.api_router")),
    # DRF auth token
    path("auth-token/", obtain_auth_token),
    # OAuth https://github.com/RealmTeam/django-rest-framework-social-oauth2
    path("api/oauth/", include('rest_framework_social_oauth2.urls')),
    # Rest Auth https://django-rest-auth.readthedocs.io/
    path("api/auth/login/", token_login_view.as_view()),
    path("api/auth/", include(("rest_auth.urls", 'rest_auth'), namespace='rest_auth')),
    path("api/auth/registration/", include("rest_auth.registration.urls")),
    # this url is used to generate email content
    path('password-reset/confirm/<uidb64>/<token>/',
        TemplateView.as_view(template_name="password_reset_confirm.html"),
        name='password_reset_confirm'),
]

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
