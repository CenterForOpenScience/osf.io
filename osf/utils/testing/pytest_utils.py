import uuid
import pytest

from website.search.util import build_query
from website.search import elastic_search
from website.search import search
from website import settings
from django.core.urlresolvers import reverse

from tests.base import test_app
from webtest_plus import TestApp
from website.app import init_app
from tests.json_api_test_app import JSONAPITestApp
from osf.quickfiles.legacy_quickfiles import QuickFilesNode
from api_tests.utils import create_test_file

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@pytest.fixture()
def flask_app():
    return TestApp(test_app)

@pytest.fixture()
def django_app():
    return JSONAPITestApp()


@pytest.mark.enable_search
class ElasticSearchTestCase:

    @pytest.fixture(autouse=True)
    def index(self):
        settings.ELASTIC_INDEX = uuid.uuid4().hex
        elastic_search.INDEX = settings.ELASTIC_INDEX

        search.create_index(elastic_search.INDEX)
        yield
        search.delete_index(elastic_search.INDEX)

    def query(self, term, raw=False):
        return search.search(build_query(term), index=elastic_search.INDEX, raw=raw)

    def query_file(self, name):
        term = 'category:file AND "{}"'.format(name)
        return self.query(term)


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

    def sprinkle_quickfiles(self, num_of_files):
        random_queryset = QuickFilesNode.objects.order_by('?')
        for num in range(0, num_of_files):
            node = random_queryset[num]
            create_test_file(node, node.creator, filename=str(uuid.uuid4()))

    def bulk_add(self, num, factory, **kwargs):
        with_quickfiles_node = kwargs.pop('with_quickfiles_node')
        objects = []
        Model = factory._meta.model

        for _ in range(0, num):
            objects.append(factory.build(**kwargs))

        users = Model.objects.bulk_create(objects)
        from website import settings
        if with_quickfiles_node:  # TODO this should be better
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
