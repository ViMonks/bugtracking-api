from django.conf import settings
from django.urls import include, path
from rest_framework.routers import DefaultRouter, SimpleRouter
from rest_framework_nested.routers import NestedSimpleRouter

from bugtracking.users.api.views import UserViewSet
from bugtracking.tracker.api.viewsets import TeamViewSet, TeamMembershipViewSet, ProjectViewSet, TicketViewSet, TeamInvitationViewSet

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("users", UserViewSet)
router.register(r'teams', TeamViewSet, basename='teams')
# don't want the memberships viewset registered by default; only using it to debug stuff
# router.register(r'memberships', TeamMembershipViewSet, basename='memberships')

team_router = NestedSimpleRouter(router, r'teams', lookup='team')
team_router.register(r'projects', ProjectViewSet, basename='projects')
team_router.register(r'invitations', TeamInvitationViewSet, basename='invitations')
project_router = NestedSimpleRouter(team_router, r'projects', lookup='project')
project_router.register(r'tickets', TicketViewSet, basename='tickets')


app_name = "api"
# urlpatterns = router.urls

urlpatterns = [

    path(r'', include(router.urls)),
    path(r'', include(team_router.urls)),
    path(r'', include(project_router.urls))
]
