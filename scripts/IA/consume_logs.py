import requests
import os
import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument(
	'-g',
	'--guid',
	help='This is the GUID of the target node on the OSF'
)
parser.add_argument(
	'-d',
	'--directory',
	help='This is the target Directory for the project and its files'
)

parser.add_argument(
	'-p',
	'--pagesize',
	help='How many logs should appear per file? Default is 100'
)

LOGS_URL = 'https://api.test.osf.io/v2/registrations/{}/logs/?page[size]={}'

def json_with_pagination(path, guid, page, url):
	# Get JSON of registration logs
	response = requests.get(url)

	if response.status_code == 404:
		raise ValueError('Project not found. Check GUID and try again.')

	# Craft filename based on page number
	json_filename = guid + '-' + str(page) + '.json'
	file_location = os.path.join(path, json_filename)
	json_data = json.loads(response.content)['data']
	with open(file_location, 'w') as file:
		json.dump(json_data, file)
	return json.loads(response.content)

def main(default_args=True):
	# Arg Parsing
	if (default_args):
		args = parser.parse_args(['--guid', 'default', '--directory', 'default'])
	else:
		args = parser.parse_args()
	args = parser.parse_args()
	guid = args.guid
	directory = args.directory
	pagesize = args.pagesize

	# Args handling
	if not guid:
		raise ValueError('Project GUID must be specified! Use -g')
	if not directory:
		# Setting default to current directory
		directory = '.'
	if not pagesize:
		pagesize = 100

	# Creating directories
	path = os.path.join(directory,guid)
	if not os.path.exists(path):
		os.mkdir(path)
	path = os.path.join(path,'logs')
	os.mkdir(path)

	# Retrieving page 1
	response = json_with_pagination(path, guid, 1, LOGS_URL.format(guid, pagesize))
	page_num = 2

	# Retrieve the rest of the pages (if applicable)
	while response['links']['next']:
		next_link = response['links']['next']
		response = json_with_pagination(path, guid, page_num, next_link)
		page_num = page_num + 1

	print('Log data successfully transferred!')



if __name__ == '__main__':

    main(default_args=False)