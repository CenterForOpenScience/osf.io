import os
import pytest
from mock import call, Mock
import unittest
import responses
import json
HERE = os.path.dirname(os.path.abspath(__file__))
from nose.tools import assert_equal
from IA.consume_logs import create_logs


def log_files():
	with open(os.path.join(HERE, 'fixtures/njs82-1.json')) as json_file:
		return json.loads(json_file.read())

def log_files_two_pages():
	with open(os.path.join(HERE, 'fixtures/8jpzs-1.json')) as json_file:
		page1 = json.loads(json_file.read())
	with open(os.path.join(HERE, 'fixtures/8jpzs-2.json')) as json_file:
		page2 = json.loads(json_file.read())

	return page1, page2


class TestIALogs(unittest.TestCase):

	@responses.activate
	def test_log_dump(self):
		responses.add(
			responses.Response(
				responses.GET,
				'http://localhost:8000/v2/registrations/njs82/logs/?page[size]=100',
				json=log_files(),
			)
		)

		create_logs(registration_with_logs._logs, '.', 100, user_token, 'http://localhost:8000/')

		with open(os.path.join(HERE, 'fixtures/8jpzs-1.json')) as json_file:
			source_json = json.loads(json_file.read())
		with open(os.path.join(HERE, 'njs82/logs/njs82-1.json')) as json_file:
			target_json = json.loads(json_file.read())

		assert source_json['data'] == target_json




	###IGNORE PAST THIS LINE###
"""
	@pytest.fixture()
	def user(self):
		return UserFactory()

	@pytest.fixture()
	def user_token(self, user):
		return ApiOAuth2PersonalTokenFactory(owner=user).token_id

	@pytest.fixture()
	def registration_with_logs(self):
		test_reg = RegistrationFactory()
		NodeLogFactory(node=test_reg)
		NodeLogFactory(node=test_reg)
		return test_reg

	@pytest.fixture()
	def base_url(self):
		return API_BASE

	@pytest.fixture()
	def logs_url(self):
		return 'http://localhost:8000/v2/registrations/{}/logs/?page[size]={}'

	def test_get_registration_json(self, user_token, registration_with_logs, base_url, logs_url):
		create_logs(registration_with_logs._id, '.', 100, user_token, base_url, logs_url)
		json_file_path = os.path.join(registration_with_logs._id, 'logs', registration_with_logs._id+'-1.json')
		with open(json_file_path) as json_file:
			json_data = json.load(json_file)

		assert len(json_data) == registration_with_logs.logs.count()
		for log in json_data:
			assert registration_with_logs.logs.filter(_id = log['id']).exists()
			"""



