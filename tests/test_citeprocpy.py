import os
import json

from api.citations.utils import render_citation
from osf_tests.factories import UserFactory
from tests.base import OsfTestCase
from osf.models import OSFUser

class Node:
    _id = '2nthu'
    csl = {'publisher': 'Open Science Framework', 'author': [{'given': 'Henrique', 'family': 'Harman'}],
           'URL': 'localhost:5000/2nthu', 'issued': {'date-parts': [[2016, 12, 6]]},
           'title': 'The study of chocolate in its many forms', 'type': 'webpage', 'id': '2nthu'}
    visible_contributors = ''


class TestCiteprocpy(OsfTestCase):

    def setUp(self):
        super(TestCiteprocpy, self).setUp()
        self.user = UserFactory(fullname='Henrique Harman')

    def test_failing_citations(self):
        node = Node()
        node.visible_contributors = OSFUser.objects.filter(fullname='Henrique Harman')
        url_data_path = os.path.join(os.path.dirname(__file__), '../website/static/citeprocpy_test_data.json')
        with open(url_data_path) as url_test_data:
            data = json.load(url_test_data)['fails']
        matches = []
        for k, v in data.items():
            try:
                citeprocpy = render_citation(node, k)
            except (TypeError, AttributeError):
                citeprocpy = ''
            if citeprocpy == v:
                matches.append(k)
                print(k)
        assert(len(matches) == 0)

    def test_passing_citations(self):
        node = Node()
        node.visible_contributors = OSFUser.objects.filter(fullname='Henrique Harman')
        url_data_path = os.path.join(os.path.dirname(__file__), '../website/static/citeprocpy_test_data.json')
        with open(url_data_path) as url_test_data:
            data = json.load(url_test_data)['passes']
        not_matches = []
        citation = []
        for k, v in data.items():
            try:
                citeprocpy = render_citation(node, k)
            except (TypeError, AttributeError):
                citeprocpy = ''
            if citeprocpy != v:
                not_matches.append(k)
                citation.append(citeprocpy)
                print(k)
        assert(len(not_matches) == 0)
