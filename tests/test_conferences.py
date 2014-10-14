# -*- coding: utf-8 -*-

from nose.tools import *  # noqa (PEP8 asserts)
from modularodm.exceptions import ValidationError

from website.conferences.views import _parse_email_name, _render_conference_node
from website.conferences.model import Conference
from website.util import api_url_for, web_url_for
from framework.auth.core import Auth

from tests.base import OsfTestCase, fake
from tests.factories import ModularOdmFactory, FakerAttribute, ProjectFactory

class ConferenceFactory(ModularOdmFactory):
    FACTORY_FOR = Conference

    endpoint = FakerAttribute('slug')
    name = FakerAttribute('catch_phrase')
    active = True

def test_parse_email_name():
    assert_equal(_parse_email_name(' Fred'), 'Fred')
    assert_equal(_parse_email_name(u'Me‰¨ü'), u'Me‰¨ü')
    assert_equal(_parse_email_name(u'Fred <fred@queen.com>'), u'Fred')
    assert_equal(_parse_email_name(u'"Fred" <fred@queen.com>'), u'Fred')


def create_fake_conference_nodes(n, endpoint):
    nodes = []
    for i in range(n):
        node = ProjectFactory(is_public=True)
        node.add_tag(endpoint, Auth(node.creator))
        node.save()
        nodes.append(node)
    return nodes


class TestConferenceEmailViews(OsfTestCase):

    def test_conference_data(self):
        conference = ConferenceFactory()

        # Create conference nodes
        n_conference_nodes = 3
        conf_nodes = create_fake_conference_nodes(n_conference_nodes,
            conference.endpoint)
        # Create a non-conference node
        ProjectFactory()

        url = api_url_for('conference_data', meeting=conference.endpoint)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        json = res.json
        assert_equal(len(json), n_conference_nodes)

    def test_conference_results(self):
        conference = ConferenceFactory()

        url = web_url_for('conference_results', meeting=conference.endpoint)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)


class TestConferenceModel(OsfTestCase):

    def test_endpoint_and_name_are_required(self):
        with assert_raises(ValidationError):
            ConferenceFactory(endpoint=None, name=fake.company()).save()
        with assert_raises(ValidationError):
            ConferenceFactory(endpoint='spsp2014', name=None).save()
