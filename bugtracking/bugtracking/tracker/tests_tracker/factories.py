from bugtracking.tracker import models
from django.contrib.auth import get_user_model

User = get_user_model()

def fac():
    """
    A factory function for returning a standard setup for testing.
    Creates the following users: admin, manager, developer, member, nonmember
    Admin is team admin. Manager is project manager. Developer is ticket developer.
    All except nonmember are team members.
    :return: (admin, manager, developer, member, nonmember, team, project, ticket)
    """
    admin = User.objects.create_user(username='admin', password='password')
    manager = User.objects.create_user(username='manager', password='password')
    developer = User.objects.create_user(username='developer', password='password')
    member = User.objects.create_user(username='member', password='password')
    nonmember = User.objects.create_user(username='nonmember', password='password')
    team = models.Team.objects.create(title='team_title', description='team_desc')
    all_members = [admin, manager, developer, member]
    team.make_admin(admin)
    project = models.Project.objects.create(team=team, title='project_title', description='project_desc')
    ticket = models.Ticket.objects.create(
        user=admin, project=project, developer=developer, title='ticket_title', description='desc',
    )
    for member in all_members:
        team.add_member(member)
        project.add_member(member)
    project.make_manager(manager)
    return admin, manager, developer, member, nonmember, team, project, ticket
