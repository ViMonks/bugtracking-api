from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter

from bugtracking.users.api.views import UserViewSet
from bugtracking.tracker.api.viewsets import TeamViewSet

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("users", UserViewSet)
router.register(r'teams', TeamViewSet, basename='team')


app_name = "api"
urlpatterns = router.urls
