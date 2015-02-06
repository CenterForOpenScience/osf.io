# coding: utf-8
from website.zotero import model
from website import zotero
from website.addons import zotero
zot = Zotero()
get_ipython().magic(u'pinfo Zotero')
from website.settings.zotero import model
from website.addons.zotero import model
get_ipython().magic(u'pinfo Zotero')
from website.models import ExternalAccount
from website.addons.zotero.model import Zotero
zot = Zotero()
all_accounts = ExternalAccount.find()
all_accounts = list(all_accounts)
print all_accounts
zot.account = all_accounts[1]
print zot.account
zot.items()
client = zot.client
client.items()
client.citations()
client.collections()
len(client.collection())
len(client.collections())
client.collections()[0]
client.collections()[1]
cola = client.collections()[1]
cola
cola['data']['name]
cola['data']['name']
zot.account
zot.account.provider_id
acol['data']['key']
acoll['data']['key']
acoll['data']['key']
cola['data']['key']
for document in client.collections() print document
for document in client.collections(): print document
for document in client.collections(): print hey
for document in client.collections(): print "hey"
client.items()
len(client.items())
client.items()[0]
document = client.items()[0]
document
document.json.get('id')
document['id']
document['key']
document['itemtype']
document['itemType']
document['itemType']
document
document('ISSN')
document['ISSN']
document['key']
document['itemType']
document['data']['itemType']
document['data']['title']
if document['data']['title']: print "yes"
