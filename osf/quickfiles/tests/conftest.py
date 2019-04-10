import pytest
from tests.base import test_app
from webtest_plus import TestApp
from tests.json_api_test_app import JSONAPITestApp
from osf_tests.factories import AuthUserFactory, ProjectFactory

@pytest.fixture(scope='session')
def flask_app():
    return TestApp(test_app)


@pytest.fixture(scope='session')
def django_app():
    return JSONAPITestApp()


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.fixture()
def user2():
    return AuthUserFactory()


@pytest.fixture()
def user3():
    return AuthUserFactory()


@pytest.fixture()
def quickfolder(user):
    return user.quickfolder


@pytest.fixture()
def project():
    return ProjectFactory()


def pytest_generate_tests(metafunc):
    # This is a helper for making parameterized test more readable by using a `cases` dict
    # called once per each test function
    if not metafunc.cls:
        return
    if not hasattr(metafunc.cls, 'cases'):
        return
    funcarglist = metafunc.cls.cases.get(metafunc.function.__name__)
    if not funcarglist:
        return
    argnames = sorted(funcarglist[0])
    metafunc.parametrize(argnames, [[funcargs[name] for name in argnames] for funcargs in funcarglist])
