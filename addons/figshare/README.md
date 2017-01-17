## Setup figshare for development

**Note:** The figshare account you test with **cannot** be the same as the figshare account
associated with the API application. Attempting to use the same account will result in errors
akin to *{"error": "You cannot request an access token for yourself!"}* (This note may be outdated,
as figshare updated their original API.)

Two methods of local testing: 
* Using an OAuth App registered on figshare, which requires a callback url that uses https. This README 
has instructions for use with ngrok, but there are other methods.
* Manually generating an Auth token through figshare's UI and creating an ExternalAccount via shell.

### A) OAuth and ngrok (untested)

1. Download ngrok (partially free, but TLS requires [subscription](https://ngrok.com/product#pricing))
2. Run with `ngrok tls -subdomain=openscience 5000` 
  * `-subdomain` can be something other than `openscience`
  * this assumes you have the OSF running with https enabled
3. Copy website/addons/figshare/settings/defaults.py to website/addons/figshare/settings/local.py
4. Go to [figshare](http://figshare.com), create an account, and login 
5. Click the dropdown with your name and select **Applications** and click **Create application**
6. Add https://openscience.ngrok.io:5000/api/v1/oauth/callback/figshare/ as the **Callback URL**
7. Open website/addons/figshare/settings/local.py
  * Copy the *consumer_key* to **CLIENT_ID**
  * Copy the *consumer_secret* to **CLIENT_SECRET**
8. Open website/settings/local.py, add *figshare* to ADDONS_REQUESTED

### B) Manual generation of auth token and ExternalAccount

1. Go to [figshare](http://figshare.com), create an account, and login 
2. Click the dropdown with your name and select **Applications** and click **Create Personal Token**
3. `invoke shell`, then run:
```
from addons.figshare.client import FigshareClient
from website.oauth.models import ExternalAccount

me = User.find_one(Q('username', 'eq', '<your username>'))
token = '<personal token id from figshare>'
client = FigshareClient(token)

info = client.userinfo()
ea = ExternalAccount(
    provider='figshare',
    provider_id=info['id'],
    provider_name='figshare',
    oauth_key=token,
    display_name='{} {}'.format(info['first_name'], info['last_name'])
)
ea.save()
fu = me.get_or_add_addon('figshare')
me.external_accounts.append(ea)
me.save()

commit()
```
4. Done. At this point, you should be able to enable figshare on a node and import the account you just created.
