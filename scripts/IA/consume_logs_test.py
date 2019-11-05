import os
import shutil
import pytest
from mock import call, Mock
import unittest
import responses
import json
HERE = os.path.dirname(os.path.abspath(__file__))
from nose.tools import assert_equal

from consume_logs import create_logs


def log_files():
	with open(os.path.join(HERE, 'tests/fixtures/njs82.json')) as json_file:
		return json.loads(json_file.read())

def log_files_two_pages():
	with open(os.path.join(HERE, 'tests/fixtures/8jpzs-1.json')) as json_file:
		page1 = json.loads(json_file.read())
	with open(os.path.join(HERE, 'tests/fixtures/8jpzs-2.json')) as json_file:
		page2 = json.loads(json_file.read())

	return page1, page2


class TestIALogs(unittest.TestCase):

	def tearDown(self):
		if os.path.isdir(os.path.join(HERE, 'njs82')):
			shutil.rmtree(os.path.join(HERE, 'njs82'))
		if os.path.isdir(os.path.join(HERE, '8jpzs')):
			shutil.rmtree(os.path.join(HERE, '8jpzs'))


	@responses.activate
	def test_log_dump(self):
		responses.add(
			responses.Response(
				responses.GET,
				'http://localhost:8000/v2/registrations/njs82/logs/?page[size]=100',
				json=log_files(),
			)
		)


		create_logs('njs82', '.', 100, 'asdfasdfasdgfasg', 'http://localhost:8000/')

		with open(os.path.join(HERE, 'tests/fixtures/njs82.json')) as json_file:
			source_json = json.loads(json_file.read())
		with open(os.path.join(HERE, 'njs82/logs/njs82-1.json')) as json_file:
			target_json = json.loads(json_file.read())

		assert source_json['data'] == target_json


	@responses.activate
	def test_log_dump_two_pages(self):
		responses.add(
			responses.Response(
				responses.GET,
				'http://localhost:8000/v2/registrations/8jpzs/logs/?page[size]=3',
				json=log_files_two_pages()[0],
			)
		)

		responses.add(
			responses.Response(
				responses.GET,
				'https://api.test.osf.io/v2/registrations/8jpzs/logs/?format=json&page=2&page%5Bsize%5D=3',
				json=log_files_two_pages()[1],
			)
		)

		create_logs('8jpzs', '.', 3, 'asdfasdfasdgfasg', 'http://localhost:8000/')

		with open(os.path.join(HERE, 'tests/fixtures/8jpzs-1.json')) as json_file:
			source_json_1 = json.loads(json_file.read())
		with open(os.path.join(HERE, 'tests/fixtures/8jpzs-2.json')) as json_file:
			source_json_2 = json.loads(json_file.read())
		with open(os.path.join(HERE, '8jpzs/logs/8jpzs-1.json')) as json_file:
			target_json_1 = json.loads(json_file.read())
		with open(os.path.join(HERE, '8jpzs/logs/8jpzs-2.json')) as json_file:
			target_json_2 = json.loads(json_file.read())

		source_json = source_json_1['data']+ source_json_2['data']
		target_json = target_json_1 + target_json_2

		assert source_json == target_json
