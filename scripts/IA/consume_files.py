import requests
import os
import argparse
from zipfile import ZipFile

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

def main(default_args=True):
	if (default_args):
		args = parser.parse_args(['--guid', 'default', '--directory', 'default'])
	else:
		args = parser.parse_args()
	args = parser.parse_args()
	guid = args.guid
	directory = args.directory

	if not guid:
		raise ValueError('Project GUID must be specified! Use -g')
	if not directory:
		# Setting default to current directory
		directory = '.'

	zip_url = 'https://files.osf.io/v1/resources/xxxxx/providers/osfstorage/?zip='
	path = os.path.join(directory,guid)
	os.mkdir(path)
	path = os.path.join(path,'files')
	os.mkdir(path)

	response = requests.get(zip_url.format(guid))
	if response.status_code == 404:
		raise ValueError('Project not found. Check GUID and try again.')

	zipfile_location = os.path.join(path, (guid+'.zip'))
	with open(zipfile_location, 'wb') as file:
		file.write(response.content)

	with ZipFile(zipfile_location, 'r') as zipObj:
		zipObj.extractall(path)

	os.remove(zipfile_location)
	print('File data successfully transferred!')



if __name__ == '__main__':

    main(default_args=False)