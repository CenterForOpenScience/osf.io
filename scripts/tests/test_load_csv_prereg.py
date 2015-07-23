# -*- coding: utf-8 -*-
import os
import json

from nose.tools import *  # noqa

from tests.base import OsfTestCase

from scripts.prereg import load_csv_prereg

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

class TestLoadCsvPrereg(OsfTestCase):

    def setUp(self):
        super(TestLoadCsvPrereg, self).setUp()
        self.page1_expected_data = {
            'q01': {
                'nav': 'Title',
                'type': 'string',
                'format': 'text',
                'title': 'Title',
                'description': 'What is the working title of your study? It is helpful if this is the same title that you submit for publication of your final manuscript, but it is not a requirement.',
                'help': 'Effect of sugar on brownie tastiness.'
            },
            'q02': {
                'nav': 'Authors',
                'type': 'string',
                'format': 'text',
                'title': 'Authorship',
                'description': 'The award goes to the first author of the pre-registered study is the recipient of the award money and must also be the first author of the published manuscript.',
                'help': 'Jimmy Stewart, Ava Gardner, Bob Hope, Greta Garbo'
            },
            'q03': {
                'nav': 'COI',
                'type': 'string',
                'format': 'textarea',
                'title': 'Conflict of Interest',
                'description': 'Could the results of this project benefit the financial interests of any of its authors, or be reasonably perceived to do so?',
                'help': 'The authors of this study own a majority share of Tastee Sugar Company.'
            },
            'q04': {
                'nav': 'Questions and Hypotheses',
                'type': 'object',
                'title': 'Research questions and hypotheses',
                'description': 'What are your research questions and hypotheses? Both directional and non-directional hypotheses are acceptable.',
                'help': 'There is strong evidence to suggest that sugar affects taste preferences, but the effect has never been demonstrated in brownies. Therefore, we will measure taste preference for four different levels of sugar concentration in a standard brownie recipe. If taste effects preferences, then mean preference indices will be higher with higher concentrations of sugar.',
            }
        }


    def test_load_correct_data(self):
        load_csv_prereg.main(dry_run=True)
        schema_directory = os.path.realpath(os.path.join(os.getcwd(), 'website/project/metadata'))
        output_file = os.path.join(schema_directory, 'prereg-prize-test.test.json')

        with open(output_file) as json_output:
            output_data = json.load(json_output)
            assert_in('pages', output_data)

            pages = output_data['pages']
            assert_equal(len(pages), 5)

            p1 = pages[0]
            assert_in('id', p1)
            assert_equal('page1', p1['id'])
            assert_in('questions', p1)
            questions = p1['questions']

            for qid, question_data in questions.items():
                assert_in('nav', question_data)
                assert_equal(self.page1_expected_data[qid]['nav'], question_data['nav'])
                assert_in('type', question_data)
                assert_equal(self.page1_expected_data[qid]['type'], question_data['type'])
                # not all questions have a format so there are omitted for now
                # assert_in('format', question_data)
                # assert_equal(self.page1_expected_data[qid]['format'], question_data['format'])
                assert_in('title', question_data)
                assert_equal(self.page1_expected_data[qid]['title'], question_data['title'])
                assert_in('description', question_data)
                assert_equal(self.page1_expected_data[qid]['description'], question_data['description'])
                assert_in('help', question_data)
                assert_equal(self.page1_expected_data[qid]['help'], question_data['help'])
