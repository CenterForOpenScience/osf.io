"""
Enable the wiki and files add-ons for all existing nodes.
"""

from website.app import init_app
from website import models

app = init_app('website.settings', set_backends=True, routes=True)


def impute_addons():
    for node in models.Node.find():
        node.addons_enabled = ['wiki', 'files']
        node._ensure_addons()
        node.save()

if __name__ == '__main__':
    impute_addons()
