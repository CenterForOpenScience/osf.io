from website.app import init_app
from website.models import Node, User
from framework import Q
from framework.analytics import piwik

app = init_app('website.settings', set_backends=True)

# NOTE: This is a naive implementation for migration, requiring a POST request
# for every user and every node. It is possible to bundle these together in a
# single request, but it would require duplication of logic and strict error
# checking of the result. Doing it this way is idempotent, and allows any
# exceptions raised to halt the process with a usable error message.

for user in User.find():
    if user.piwik_token:
        continue

    piwik.create_user(user)

for node in Node.find(Q('is_public', 'eq', True) & Q('is_deleted', 'eq', False)):
    if node.piwik_site_id:
        continue

    piwik._provision_node(node._id)
