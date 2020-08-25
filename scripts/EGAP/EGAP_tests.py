import unittest
from jsonschema.exceptions import ValidationError
from create_EGAP_json import (schema_to_spreadsheet_mapping,
	make_project_dict,
	make_registration_dict,
	other_mapping,
)

HEADER_ROW = ['POST DATE',
	'ID',
	'STATUS',
	'TITLE',
	'B2 AUTHORS',
	'EMAIL',
	'B3 ACKNOWLEDGEMENTS',
	'B4 FACULTY MEMBER?',
	'B5 PROSPECTIVE OR RETROSPECTIVE?',
	'B6 EXPERIMENTAL STUDY?',
	'B7 DATE OF START OF STUDY',
	'B8 GATE DATE',
	'B8 FORMERLY GATED UNTIL',
	'B9 PRESENTED AT EGAP MEETING?',
	'B10 PRE-ANALYSIS PLAN WITH REGISTRATION?',
	'C1 BACKGROUND',
	'C2 HYPOTHESES',
	'C3 TESTING PLAN',
	'C4 COUNTRY',
	'C5 SAMPLE SIZE',
	'C6 POWER ANALYSIS?',
	'C7 IRB APPROVAL?',
	'C8 IRB NUMBER',
	'C9 DATE OF IRB APPROVAL',
	'C10 INTERVENTION IMPLEMENTER',
	'C11 REMUNERATION?',
	'C12 PUBLICATION AGREEMENT?',
	'C13 JEL CODES',
	'METHODOLOGY',
	'POLICY']

TEST_ROW_WITH_OTHER = ['03/05/2017 - 17:00',
	'20170305AA',
	'Status is not saved, so this field doesnt matter',
	'The members of Nsync',
	'Justin Timberlake | Joey Fatone | Lance Bass',
	'doesnt@matter.com',
	'We acknolowledge Chris Kirkpatrick',
	'Justin Timberlake is a faculty Member',
	'This is my other response for prospective',
	'Yes',
	'05/01/2017',
	'05/01/2020',
	'',
	'No',
	'No',
	'Test background',
	'test hypothesis',
	'This is my testing plan',
	'Switzerland',
	'3242',
	'This is a power analysis other response',
	'This is an other irb response',
	'343434',
	'03/06/2017',
	'This is an other intervention response',
	'This is an other renumeration response',
	'This is an other publication agreement response',
	'Jel Code',
	'Survey Methodology',
	'Gender']

# Testing row with missing required fields. i.e. Hypothesis, Background, testing plan.
TEST_ROW_WITH_MISSING = ['03/05/2017 - 17:00',
	'20170305AA',
	'Status is not saved, so this field doesnt matter',
	'The members of Nsync',
	'Justin Timberlake | Joey Fatone | Lance Bass',
	'doesnt@matter.com',
	'We acknolowledge Chris Kirkpatrick',
	'Justin Timberlake is a faculty Member',
	'This is my other response for prospective',
	'Yes',
	'05/01/2017',
	'05/01/2020',
	'',
	'No',
	'No',
	'',
	'',
	'',
	'Switzerland',
	'3242',
	'This is a power analysis other response',
	'This is an other irb response',
	'343434',
	'03/06/2017',
	'This is an other intervention response',
	'This is an other renumeration response',
	'This is an other publication agreement response',
	'Jel Code',
	'Survey Methodology',
	'Gender']

TEST_ROW_WITH_OTHER_AUTHORS = [
 	{'name': 'Justin Timberlake', 'email': 'jt@gmail.com'},
 	{'name': 'Joey Fatone'},
 	{'name': 'Lance Bass', 'email': 'lBass@gmail.com'}]

TEST_ROW = ['05/05/2018 - 17:00',
	'20180505AA',
	'Status is not saved, so this field doesnt matter',
	'The members of Backstreet boys',
	'Nick Carter | Brian Littrell, Ph.D. | AJ McLean | U.S. Agency Bureau, Department of Agency affairs (DOAA)',
	'doesnt@matter.com',
	'We acknolowledge Chris Kirkpatrick',
	'Yes',
	'Registration prior to any research activities',
	'Yes',
	'05/01/2017',
	'05/01/2020',
	'',
	'No',
	'No',
	'Test background',
	'test hypothesis',
	'This is my testing plan',
	'Switzerland',
	'3242',
	'Yes',
	'Yes',
	'343434',
	'03/06/2017',
	'Researchers',
	'Yes',
	'Yes',
	'Jel Code',
	'Survey Methodology',
	'Gender']

TEST_ROW_AUTHORS = [
 	{'name': 'Nick Carter', 'email': 'nickc@gmail.com'},
 	{'name': 'Brian Littrell, Ph.D.'},
 	{'name': 'AJ McLean', 'email': 'AJML@gmail.com'},
 	{'name': 'U.S. Agency Bureau, Department of Agency affairs (DOAA)', 'email': 'DOAA@UAB.gov'}]

class TestProjectDict(unittest.TestCase):

	def test_row_with_other(self):
		project_dict = make_project_dict(TEST_ROW_WITH_OTHER, TEST_ROW_WITH_OTHER_AUTHORS, HEADER_ROW)
		self.assertEqual(project_dict['title'], TEST_ROW_WITH_OTHER[3])
		self.assertEqual(project_dict['contributors'], TEST_ROW_WITH_OTHER_AUTHORS)
		self.assertEqual(project_dict['post-date'], TEST_ROW_WITH_OTHER[0])
		self.assertEqual(project_dict['id'], TEST_ROW_WITH_OTHER[1])

	def test_row(self):
		project_dict = make_project_dict(TEST_ROW, TEST_ROW_AUTHORS, HEADER_ROW)
		self.assertEqual(project_dict['title'], TEST_ROW[3])
		self.assertEqual(project_dict['contributors'], TEST_ROW_AUTHORS)
		self.assertEqual(project_dict['post-date'], TEST_ROW[0])
		self.assertEqual(project_dict['id'], TEST_ROW[1])

class TestRegistrationDict(unittest.TestCase):

	def run_registration_test(self, row, header_row):
		project_dict = make_registration_dict(row, header_row, row[1])
		for question_dict in schema_to_spreadsheet_mapping:
			question_key = question_dict.keys()[0]
			spreadsheet_column = question_dict[question_key]
			column_index = header_row.index(spreadsheet_column)
			if type(project_dict[question_key]['value']) == list:
				field_val = project_dict[question_key]['value'][0]
			else:
				field_val = project_dict[question_key]['value']
			if row[column_index] != field_val and question_key in other_mapping:
				self.assertEqual(project_dict[question_key]['value'], 'Other (describe in text box below)')
				field_val = project_dict[other_mapping[question_key]]['value']
				self.assertEqual(row[column_index], field_val)
			else:
				self.assertEqual(row[column_index], field_val)

	def test_row_with_other(self):
		self.run_registration_test(TEST_ROW_WITH_OTHER, HEADER_ROW)

	def test_row(self):
		self.run_registration_test(TEST_ROW, HEADER_ROW)

	def test_row_with_errors(self):
		self.assertRaises(Exception, make_registration_dict, TEST_ROW_WITH_MISSING, HEADER_ROW, TEST_ROW_WITH_MISSING[1])
