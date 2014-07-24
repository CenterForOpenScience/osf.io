"""Fixes nodes with two copies of the files and wiki addons attached.

This script must be run from the OSF root directory for the imports to work.
"""


from pymongo import MongoClient

from website.app import init_app
from website.project.model import Node

from website.addons.wiki.model import AddonWikiNodeSettings
from website.addons.osffiles.model import AddonFilesNodeSettings

app = init_app()

from website.settings import DB_USER, DB_PASS

client = MongoClient('localhost', 20771)
client.osf20130903.authenticate(DB_USER, DB_PASS)
db = client.osf20130903

for addon_class in (AddonWikiNodeSettings, AddonFilesNodeSettings):
    print('Processing ' + addon_class.__name__)
    query = db['node'].find({
        '.'.join(
            ('__backrefs',
                  'addons',
                  addon_class.__name__.lower(),
                 'owner'
            )
        ): {'$size': 2}
    })

    for node in (Node.load(node['_id']) for node in query):
        print('- ' + node._id)
        keep, discard = [x for x in node.addons if isinstance(x, addon_class)]
        addon_class.remove_one(discard)

    print('')

print('-----\nDone.')
