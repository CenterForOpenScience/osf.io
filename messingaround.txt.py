# coding: utf-8
get_ipython().magic(u'cat messing*')
from website.addons.zotero.model import Zotero
zot = Zotero()
print zot.client
print zot.account
print zot.account.oauthkey
from website.models import ExternalAccount
ExternalAccount.find()
all_accounts =   _client = None
all_accounts = ExternalAccount.find()
print all_accounts
all_accounts = list(all_accounts)
print all_accounts
print all_accounts[1]
print all_accounts[1]
print zot
zot.account = all_accounts[1]
get_ipython().magic(u'save messingarround.txt 7-37')
print zot.account
zot.items()
zot.Items()
zot.top()
print zot
type(zot)
zot
print zot.client
client = zot.client
client.items()
client.citations()
client.collections()
list = client.collections()
list[1]
list[0].name
list[0]['name']
list[0][u'name']
list[0]
list[0][1]
list[0][0]
list[0]
list[0][name]
list[0]['name']
list[0]['data']['name']
