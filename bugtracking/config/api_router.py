from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter

from bugtracking.users.api.views import UserViewSet
from bugtracking.tracker.api.viewsets import TeamViewSet, TeamMembershipViewSet

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("users", UserViewSet)
router.register(r'teams', TeamViewSet, basename='teams')
# don't want the memberships viewset registered by default; only using it to debug stuff
# router.register(r'memberships', TeamMembershipViewSet, basename='memberships')


app_name = "api"
urlpatterns = router.urls
