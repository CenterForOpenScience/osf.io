import os
import json
from nose.tools import *

from api.citations.utils import render_citation


class Node:
    _id = '2nthu'
    csl = {'publisher': 'Open Science Framework', 'author': [{'given': u'Henrique', 'family': u'Harman'}], 'URL': 'localhost:5000/2nthu', 'issued': {'date-parts': [[2016, 12, 6]]}, 'title': u'The study of chocolate in its many forms', 'type': 'webpage', 'id': u'2nthu'}


class TestCiteprocpy:
    def test_failing_citations(self):
        node = Node()
        url_data_path = os.path.join(os.path.dirname(__file__), '../website/static/citeprocpy_test_data.json')
        with open(url_data_path) as url_test_data:
            data = json.load(url_test_data)['fails']
        matches = []
        for k, v in data.iteritems():
            try:
                citeprocpy = render_citation(node, k)
            except (TypeError, AttributeError):
                citeprocpy = ''
            if citeprocpy == v:
                matches.append(k)
                print k
        assert(len(matches) == 0)

    def test_passing_citations(self):
        node = Node()
        url_data_path = os.path.join(os.path.dirname(__file__), '../website/static/citeprocpy_test_data.json')
        with open(url_data_path) as url_test_data:
            data = json.load(url_test_data)['passes']
        not_matches = []
        for k, v in data.iteritems():
            try:
                citeprocpy = render_citation(node, k)
            except (TypeError, AttributeError):
                citeprocpy = ''
            if citeprocpy != v:
                not_matches.append(k)
                print k
        assert(len(not_matches) == 0)

