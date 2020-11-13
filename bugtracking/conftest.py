import pytest
from model_bakery import baker

@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    pass

@pytest.fixture
def admin():
    return baker.make_recipe('bugtracking.tracker.admin')

@pytest.fixture
def team():
    return baker.make_recipe('bugtracking.tracker.team')

@pytest.fixture
def owner():
    return baker.make('users.user')
