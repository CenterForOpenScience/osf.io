import uuid
import pytest

from django.core.urlresolvers import reverse

from tests.base import test_app
from webtest_plus import TestApp
from website.app import init_app
from tests.json_api_test_app import JSONAPITestApp
from osf.models import QuickFilesNode, QuickFolder, OSFUser
from osf_tests.factories import AuthUserFactory
from api_tests.utils import create_test_file, create_test_quickfile

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@pytest.fixture()
def flask_app():
    return TestApp(test_app)

@pytest.fixture()
def django_app():
    return JSONAPITestApp()


class V1ViewsCase:

    @pytest.fixture(autouse=True)
    def app(self):
        return TestApp(test_app)

    @pytest.fixture(autouse=True)
    def app_init(self):
        try:
            test_app = init_app(routes=True, set_backends=False)
        except AssertionError:  # Routes have already been set up
            test_app = init_app(routes=False, set_backends=False)

        test_app.testing = True
        return test_app

    @pytest.yield_fixture(autouse=True)
    def request_context(self, app_init):
        context = app_init.test_request_context(headers={
            'Remote-Addr': '146.9.219.56',
            'User-Agent': 'Mozilla/5.0 (X11; U; SunOS sun4u; en-US; rv:0.9.4.1) Gecko/20020518 Netscape6/6.2.3'
        })
        context.push()
        yield context
        context.pop()


class V2ViewsCase:

    @pytest.fixture(autouse=True)
    def app(self):
        return JSONAPITestApp()

    def get_url(self, view_name, **kwargs):
        kwargs.update({'version': 'v2'})
        return reverse(view_name, kwargs=kwargs)


@pytest.mark.django_db
class MigrationTestCase:

    logger = logging.getLogger(__name__)

    def sprinkle_quickfiles(self, model, num_of_files):
        """
        Randomly adds files to QuickfilesNodes or Quickfolders to test the divorce migration
        :param model:
        :param num_of_files:
        :return:
        """
        random_queryset = list(OSFUser.objects.order_by('?'))
        import random
        for _ in range(0, num_of_files):
            random.shuffle(random_queryset)
            instance = random_queryset[0]
            if model == QuickFilesNode:
                file_node = create_test_file(QuickFilesNode.objects.get_for_user(instance), instance, filename=str(uuid.uuid4()))
            if model == QuickFolder:
                file_node = create_test_quickfile(instance, filename=str(uuid.uuid4()))

            file_node.save()

    def add_users(self, num, **kwargs):
        """
        Adds a large number of users for tests.
        :param num:
        :param kwargs:
        :return:
        """
        with_quickfiles_node = kwargs.pop('with_quickfiles_node', False)

        for _ in range(0, num):
            user = AuthUserFactory()
            user.save()

        from website import settings
        from osf.models.legacy_quickfiles import QuickFilesNode

        users = OSFUser.objects.all()
        if with_quickfiles_node:
            for user in users:
                for addon in settings.ADDONS_AVAILABLE:
                    if 'user' in addon.added_default:
                        user.add_addon(addon.short_name)
                user.save()
                QuickFilesNode.objects.create_for_user(user)

    def assert_joined(self, model, field_name, model2, field_name2):
        values_set1 = set(list((model.objects.all().values_list(field_name, flat=True))))
        values_set2 = set(list((model2.objects.all().values_list(field_name2, flat=True))))
        assert values_set1 == values_set2, '{model}.{field_name}, didn\'t join with {model2}.{field_name2}'.format(model=model.__name__,
                                                                                                                   field_name=field_name,
                                                                                                                   model2=model2.__name__,
                                                                                                                   field_name2=field_name2)
    def assert_subset(self, model, field_name, model2, field_name2):
        values_set1 = set(list((model.objects.all().values_list(field_name, flat=True))))
        values_set2 = set(list((model2.objects.all().values_list(field_name2, flat=True))))
        assert values_set1.issubset(values_set2), '{model}.{field_name}, didn\'t join with {model2}.{field_name2}'.format(model=model.__name__,
                                                                                                                   field_name=field_name,
                                                                                                                   model2=model2.__name__,
                                                                                                                   field_name2=field_name2)
