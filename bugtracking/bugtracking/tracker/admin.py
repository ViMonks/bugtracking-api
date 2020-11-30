from django.contrib import admin
from . import models

# Register your models here.
admin.site.register(
    [models.Team, models.TeamMembership, models.Project, models.ProjectMembership, models.Ticket, models.Comment,
     models.TeamInvitation]
)
