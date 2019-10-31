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
	print ('start')
	if (default_args):
		args = parser.parse_args(['--guid', 'default', '--directory', 'default'])
	else:
		args = parser.parse_args()
	args = parser.parse_args()
	guid = args.guid
	directory = args.directory

	zip_url = 'https://files.osf.io/v1/resources/{}/providers/osfstorage/?zip='
	path = os.path.join(directory,guid)
	os.mkdir(path)
	path = os.path.join(path,'files')
	os.mkdir(path)
	response = requests.get(zip_url.format(guid))
	print ('getting...')
	zipfile_location = os.path.join(path, (guid+'.zip'))
	with open(zipfile_location, 'wb') as file:
		file.write(response.content)

	with ZipFile(zipfile_location, 'r') as zipObj:
		zipObj.extractall(path)

	os.remove(zipfile_location)
	print('DONE!')



if __name__ == '__main__':

    main(default_args=False)