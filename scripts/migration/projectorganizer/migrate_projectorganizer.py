"""Fixes nodes without is_folder set.

This script must be run from the OSF root directory for the imports to work.
"""

from pymongo import MongoClient
from website.app import init_app

app = init_app()

from website.settings import DB_USER, DB_PASS, DB_PORT

client = MongoClient('localhost', DB_PORT)
client.osf20130903.authenticate(DB_USER, DB_PASS)

db = client.osf20130903
node = db['node']
node.update({"is_folder": {'$exists': False}}, {'$set': {'is_folder': False}}, multi=True)

print('-----\nDone.')

